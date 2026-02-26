"""
playlists.py – JSON-backed local playlist manager.

Playlists are stored in a single JSON file inside the download directory.
"""

import json
import os
from typing import TypedDict


PLAYLISTS_FILE = "playlists.json"


class PlaylistEntry(TypedDict):
    path: str
    title: str
    artist: str


class Playlist(TypedDict):
    name: str
    tracks: list[PlaylistEntry]


def _playlists_path(directory: str) -> str:
    return os.path.join(directory, PLAYLISTS_FILE)


def load_playlists(directory: str) -> list[Playlist]:
    """Load all playlists from the JSON file in *directory*."""
    fp = _playlists_path(directory)
    if not os.path.isfile(fp):
        return []
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_playlists(directory: str, playlists: list[Playlist]) -> None:
    """Persist *playlists* to the JSON file in *directory*."""
    os.makedirs(directory, exist_ok=True)
    fp = _playlists_path(directory)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(playlists, f, indent=2, ensure_ascii=False)


def create_playlist(directory: str, name: str) -> list[Playlist]:
    """Create a new empty playlist and return all playlists."""
    pls = load_playlists(directory)
    pls.append(Playlist(name=name, tracks=[]))
    save_playlists(directory, pls)
    return pls


def delete_playlist(directory: str, index: int) -> list[Playlist]:
    """Delete a playlist by index and return remaining playlists."""
    pls = load_playlists(directory)
    if 0 <= index < len(pls):
        pls.pop(index)
        save_playlists(directory, pls)
    return pls


def rename_playlist(directory: str, index: int, new_name: str) -> list[Playlist]:
    """Rename a playlist by index and return all playlists."""
    pls = load_playlists(directory)
    if 0 <= index < len(pls):
        pls[index]["name"] = new_name
        save_playlists(directory, pls)
    return pls


def add_track_to_playlist(
    directory: str, playlist_index: int, track: PlaylistEntry
) -> list[Playlist]:
    """Append a track to a playlist and return all playlists."""
    pls = load_playlists(directory)
    if 0 <= playlist_index < len(pls):
        pls[playlist_index]["tracks"].append(track)
        save_playlists(directory, pls)
    return pls


def remove_track_from_playlist(
    directory: str, playlist_index: int, track_index: int
) -> list[Playlist]:
    """Remove a track from a playlist and return all playlists."""
    pls = load_playlists(directory)
    if 0 <= playlist_index < len(pls) and 0 <= track_index < len(pls[playlist_index]["tracks"]):
        pls[playlist_index]["tracks"].pop(track_index)
        save_playlists(directory, pls)
    return pls
