"""
library.py – Scan download directories and read audio-file metadata.
"""

import os
from typing import TypedDict

from mutagen import File as MutagenFile

SUPPORTED_EXTENSIONS = {".m4a", ".mp3", ".opus", ".flac", ".wav", ".aac", ".ogg"}


class TrackMeta(TypedDict):
    path: str
    filename: str
    title: str
    artist: str
    album: str
    duration: str
    fmt: str


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return "—"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def scan_directory(directory: str) -> list[TrackMeta]:
    """Return metadata for every supported audio file in *directory*."""
    tracks: list[TrackMeta] = []
    if not os.path.isdir(directory):
        return tracks

    for entry in sorted(os.listdir(directory)):
        ext = os.path.splitext(entry)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        full = os.path.join(directory, entry)
        if not os.path.isfile(full):
            continue

        title, artist, album, duration = os.path.splitext(entry)[0], "Unknown", "", "—"
        try:
            mf = MutagenFile(full, easy=True)
            if mf is not None:
                title = (mf.get("title") or [os.path.splitext(entry)[0]])[0]
                artist = (mf.get("artist") or ["Unknown"])[0]
                album = (mf.get("album") or [""])[0]
                duration = _fmt_duration(mf.info.length if mf.info else None)
        except Exception:
            pass

        tracks.append(
            TrackMeta(
                path=full,
                filename=entry,
                title=title,
                artist=artist,
                album=album,
                duration=duration,
                fmt=ext.lstrip(".").upper(),
            )
        )
    return tracks
