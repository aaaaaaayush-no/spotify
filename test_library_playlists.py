"""Tests for library.py and playlists.py modules."""

import json
import os
import tempfile
import unittest

from library import scan_directory, _fmt_duration
from playlists import (
    load_playlists,
    save_playlists,
    create_playlist,
    delete_playlist,
    rename_playlist,
    add_track_to_playlist,
    remove_track_from_playlist,
    PlaylistEntry,
)


class TestFmtDuration(unittest.TestCase):
    def test_none(self):
        self.assertEqual(_fmt_duration(None), "—")

    def test_zero(self):
        self.assertEqual(_fmt_duration(0), "—")

    def test_negative(self):
        self.assertEqual(_fmt_duration(-5), "—")

    def test_seconds_only(self):
        self.assertEqual(_fmt_duration(45), "0:45")

    def test_minutes_and_seconds(self):
        self.assertEqual(_fmt_duration(185), "3:05")

    def test_exact_minute(self):
        self.assertEqual(_fmt_duration(120), "2:00")


class TestScanDirectory(unittest.TestCase):
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(scan_directory(d), [])

    def test_nonexistent_dir(self):
        self.assertEqual(scan_directory("/nonexistent_dir_xyz"), [])

    def test_ignores_non_audio(self):
        with tempfile.TemporaryDirectory() as d:
            open(os.path.join(d, "readme.txt"), "w").close()
            open(os.path.join(d, "image.png"), "w").close()
            self.assertEqual(scan_directory(d), [])

    def test_picks_up_mp3_file(self):
        with tempfile.TemporaryDirectory() as d:
            # Create a dummy mp3 (not valid audio, but tests fallback)
            fp = os.path.join(d, "test_song.mp3")
            with open(fp, "wb") as f:
                f.write(b"\x00" * 128)
            tracks = scan_directory(d)
            self.assertEqual(len(tracks), 1)
            self.assertEqual(tracks[0]["filename"], "test_song.mp3")
            self.assertEqual(tracks[0]["fmt"], "MP3")


class TestPlaylists(unittest.TestCase):
    def test_load_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_playlists(d), [])

    def test_create_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            pls = create_playlist(d, "My Mix")
            self.assertEqual(len(pls), 1)
            self.assertEqual(pls[0]["name"], "My Mix")
            self.assertEqual(pls[0]["tracks"], [])
            # reload
            loaded = load_playlists(d)
            self.assertEqual(loaded, pls)

    def test_delete_playlist(self):
        with tempfile.TemporaryDirectory() as d:
            create_playlist(d, "A")
            create_playlist(d, "B")
            pls = delete_playlist(d, 0)
            self.assertEqual(len(pls), 1)
            self.assertEqual(pls[0]["name"], "B")

    def test_rename_playlist(self):
        with tempfile.TemporaryDirectory() as d:
            create_playlist(d, "Old")
            pls = rename_playlist(d, 0, "New")
            self.assertEqual(pls[0]["name"], "New")

    def test_add_and_remove_track(self):
        with tempfile.TemporaryDirectory() as d:
            create_playlist(d, "Test")
            track = PlaylistEntry(path="/fake.mp3", title="Song", artist="Artist")
            pls = add_track_to_playlist(d, 0, track)
            self.assertEqual(len(pls[0]["tracks"]), 1)
            self.assertEqual(pls[0]["tracks"][0]["title"], "Song")

            pls = remove_track_from_playlist(d, 0, 0)
            self.assertEqual(len(pls[0]["tracks"]), 0)

    def test_load_corrupt_file(self):
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, "playlists.json")
            with open(fp, "w") as f:
                f.write("not valid json{{{")
            self.assertEqual(load_playlists(d), [])

    def test_delete_out_of_range(self):
        with tempfile.TemporaryDirectory() as d:
            create_playlist(d, "Only")
            pls = delete_playlist(d, 5)  # out of range
            self.assertEqual(len(pls), 1)  # unchanged

    def test_remove_track_out_of_range(self):
        with tempfile.TemporaryDirectory() as d:
            create_playlist(d, "PL")
            pls = remove_track_from_playlist(d, 0, 99)
            self.assertEqual(len(pls[0]["tracks"]), 0)


if __name__ == "__main__":
    unittest.main()
