"""
core.py – Spotify playlist downloader core logic.

Adapted from https://github.com/invzfnc/spotify-downloader
"""

__version__ = "1.0.0"
__author__ = "Cha @github.com/invzfnc"

import concurrent.futures
import os
import re
import threading

from typing import TypedDict, Callable
from time import sleep
from random import uniform
from itertools import chain

from spotapi import Public
from yt_dlp import YoutubeDL
from ytmusicapi import YTMusic

DOWNLOAD_PATH = "./downloads/"
AUDIO_FORMAT = "m4a"
CONCURRENT_LIMIT = 5
CONCURRENT_FRAGMENT_DOWNLOADS = 8

_thread_local = threading.local()


class PlaylistInfo(TypedDict):
    title: str
    artist: str


def _is_album_url(url: str) -> bool:
    """Return *True* if *url* points to a Spotify album."""
    return bool(re.search(r"open\.spotify\.com/album/", url))


def get_album_info(album_id: str) -> list[PlaylistInfo]:
    """Extracts track data from a Spotify album and returns a list of
    ``{"title": ..., "artist": ...}`` dicts."""

    result: list[PlaylistInfo] = []

    try:
        chunks = list(Public.album_info(album_id))
        items = list(chain.from_iterable(chunks))
    except (KeyError, Exception):
        return result

    for item in items:
        try:
            track = item["track"]
            song: PlaylistInfo = {
                "title": track["name"],
                "artist": track["artists"]["items"][0]["profile"]["name"],
            }
        except (KeyError, IndexError, TypeError):
            continue

        if song not in result:
            result.append(song)

    return result


def get_playlist_info(playlist_id: str) -> list[PlaylistInfo]:
    """Extracts track data from Spotify and returns a list of
    ``{"title": ..., "artist": ...}`` dicts.

    Accepts playlist **or** album URLs/IDs.  Album URLs are detected
    automatically and routed to :func:`get_album_info`."""

    if _is_album_url(playlist_id):
        return get_album_info(playlist_id)

    result: list[PlaylistInfo] = []

    try:
        chunks = list(Public.playlist_info(playlist_id))
        items = list(chain.from_iterable([chunk["items"] for chunk in chunks]))
    except (KeyError, Exception):
        return result

    for item in items:
        item = item["itemV2"]["data"]

        if item["__typename"] == "Track":
            song: PlaylistInfo = {
                "title": item["name"],
                "artist": item["artists"]["items"][0]["profile"]["name"],
            }
        elif item["__typename"] == "LocalTrack":
            song = {
                "title": item["name"],
                "artist": item["artistName"],
            }
        else:
            continue

        if song not in result:
            result.append(song)

    return result


def get_song_url(song_info: PlaylistInfo) -> tuple[str, str]:
    """Searches YouTube Music for the best match and returns its URL."""

    if not hasattr(_thread_local, "ytmusic_client"):
        _thread_local.ytmusic_client = YTMusic()

    data = _thread_local.ytmusic_client.search(f"{song_info['title']} {song_info['artist']}")

    url_part = "https://music.youtube.com/watch?v="

    songs = [entry for entry in data if entry["resultType"] == "song"]
    matches = [s for s in songs if song_info["title"] in s["title"]]

    if matches:
        match = matches[0]
        return url_part + match["videoId"], match["title"]

    streams = [e for e in data if e["resultType"] in ("song", "video")]
    if streams:
        return url_part + streams[0]["videoId"], streams[0]["title"]

    return "", ""


def get_song_urls(
    playlist_info: list[PlaylistInfo],
    concurrent_limit: int,
    progress_cb: Callable[[str, str], None] | None = None,
    cancel_flag: list[bool] | None = None,
) -> list[str]:
    """Matches each track to a YouTube Music URL.

    Args:
        playlist_info:   list of track dicts.
        concurrent_limit: number of concurrent searches.
        progress_cb:     optional ``(status, message)`` callback called from
                         worker threads.
        cancel_flag:     single-element list; set ``cancel_flag[0] = True``
                         from the main thread to abort.
    """

    def process_song(song_info: PlaylistInfo) -> str:
        if cancel_flag and cancel_flag[0]:
            return ""

        if progress_cb:
            progress_cb("matching", f"Matching: {song_info['title']}")

        try:
            url, title = get_song_url(song_info)
        except Exception as exc:
            if progress_cb:
                progress_cb("error", f"Search error for {song_info['title']}: {exc}")
            url, title = "", ""

        if url and progress_cb:
            progress_cb("found", f"Found: {title}")
        elif progress_cb:
            progress_cb("not_found", f"No match for: {song_info['title']}")

        sleep(uniform(0.1, 0.5))
        return url

    urls: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_limit) as executor:
        futures = [executor.submit(process_song, song) for song in playlist_info]
        for future in futures:
            if cancel_flag and cancel_flag[0]:
                for f in futures:
                    f.cancel()
                break
            urls.append(future.result())

    return urls


def download_from_urls(
    urls: list[str],
    output_dir: str,
    audio_format: str,
    title_first: bool,
    download_archive: str | None,
    concurrent_fragment_downloads: int = CONCURRENT_FRAGMENT_DOWNLOADS,
    progress_cb: Callable[[str, str], None] | None = None,
) -> None:
    """Downloads audio for each URL via yt-dlp."""

    os.makedirs(output_dir, exist_ok=True)

    if not output_dir.endswith("/"):
        output_dir += "/"

    if title_first:
        filename = f"{output_dir}%(title)s - %(creator)s.%(ext)s"
    else:
        filename = f"{output_dir}%(creator)s - %(title)s.%(ext)s"

    class ProgressLogger:
        def debug(self, msg: str) -> None:
            if msg.startswith("[download]") and progress_cb:
                progress_cb("download", msg.strip())

        def info(self, msg: str) -> None:
            if progress_cb:
                progress_cb("info", msg.strip())

        def warning(self, msg: str) -> None:
            pass

        def error(self, msg: str) -> None:
            if progress_cb:
                progress_cb("error", msg.strip())

    options = {
        "concurrent_fragment_downloads": concurrent_fragment_downloads,
        "extract_flat": "discard_in_playlist",
        "final_ext": "m4a",
        "format": "bestaudio/best",
        "fragment_retries": 10,
        "ignoreerrors": "only_download",
        "outtmpl": {"default": filename, "pl_thumbnail": ""},
        "postprocessor_args": {
            "ffmpeg": [
                "-c:v", "mjpeg",
                "-vf", "crop='if(gt(ih,iw),iw,ih)':'if(gt(iw,ih),ih,iw)'",
            ]
        },
        "postprocessors": [
            {"format": "jpg", "key": "FFmpegThumbnailsConvertor", "when": "before_dl"},
            {
                "key": "FFmpegExtractAudio",
                "nopostoverwrites": False,
                "preferredcodec": audio_format,
                "preferredquality": "5",
            },
            {"add_chapters": True, "add_infojson": "if_exists",
             "add_metadata": True, "key": "FFmpegMetadata"},
            {"already_have_thumbnail": False, "key": "EmbedThumbnail"},
            {"key": "FFmpegConcat", "only_multi_video": True, "when": "playlist"},
        ],
        "retries": 10,
        "writethumbnail": True,
        "logger": ProgressLogger(),
    }

    if download_archive:
        options["download_archive"] = f"{output_dir}{download_archive}"

    with YoutubeDL(options) as ydl:
        ydl.download([u for u in urls if u])


def run_download(
    playlist_url: str,
    output_dir: str,
    audio_format: str,
    title_first: bool,
    concurrent_limit: int,
    download_archive: str | None,
    concurrent_fragment_downloads: int = CONCURRENT_FRAGMENT_DOWNLOADS,
    progress_cb: Callable[[str, str], None] | None = None,
    cancel_flag: list[bool] | None = None,
    selected_tracks: list[PlaylistInfo] | None = None,
) -> list[PlaylistInfo]:
    """High-level entry point used by the GUI.

    Returns the list of tracks found in the playlist (may be empty on error).

    If *selected_tracks* is provided the playlist fetch is skipped and only the
    given tracks are downloaded.
    """
    if selected_tracks:
        playlist_info = selected_tracks
    else:
        if progress_cb:
            progress_cb("status", "Fetching track info from Spotify…")

        playlist_info = get_playlist_info(playlist_url)

        if not playlist_info:
            if progress_cb:
                progress_cb("error", "Could not fetch tracks. Check the URL and try again.")
            return []

    if progress_cb:
        progress_cb("status", f"Found {len(playlist_info)} tracks. Matching to YouTube Music…")

    urls = get_song_urls(playlist_info, concurrent_limit, progress_cb, cancel_flag)

    if cancel_flag and cancel_flag[0]:
        if progress_cb:
            progress_cb("status", "Download cancelled.")
        return playlist_info

    if progress_cb:
        progress_cb("status", "Downloading audio files…")

    download_from_urls(urls, output_dir, audio_format, title_first,
                       download_archive, concurrent_fragment_downloads,
                       progress_cb)

    if progress_cb:
        progress_cb("done", "All downloads complete!")

    return playlist_info
