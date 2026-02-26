"""Tests for core.py download functionality."""

import threading
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from core import (
    get_song_url, get_song_urls, download_from_urls, run_download,
    get_album_info, get_playlist_info, _is_album_url, _thread_local,
)


class TestIsAlbumUrl(unittest.TestCase):
    """Test _is_album_url URL detection."""

    def test_album_url(self):
        self.assertTrue(_is_album_url("https://open.spotify.com/album/2CUXo26JAWIbQx0EVMnjpA"))

    def test_album_url_with_query(self):
        self.assertTrue(_is_album_url(
            "https://open.spotify.com/album/2CUXo26JAWIbQx0EVMnjpA?si=qEvS5pSGSqKci_acBtzsiQ"
        ))

    def test_playlist_url(self):
        self.assertFalse(_is_album_url("https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"))

    def test_plain_id(self):
        self.assertFalse(_is_album_url("2CUXo26JAWIbQx0EVMnjpA"))


class TestGetAlbumInfo(unittest.TestCase):
    """Test get_album_info with mocked spotapi."""

    @patch("core.Public")
    def test_returns_tracks_from_album(self, mock_public):
        mock_public.album_info.return_value = iter([
            [
                {"track": {"name": "Song A", "artists": {"items": [{"profile": {"name": "Artist A"}}]}}},
                {"track": {"name": "Song B", "artists": {"items": [{"profile": {"name": "Artist B"}}]}}},
            ]
        ])
        result = get_album_info("https://open.spotify.com/album/abc123")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], {"title": "Song A", "artist": "Artist A"})
        self.assertEqual(result[1], {"title": "Song B", "artist": "Artist B"})

    @patch("core.Public")
    def test_returns_empty_on_api_error(self, mock_public):
        mock_public.album_info.side_effect = Exception("API error")
        result = get_album_info("https://open.spotify.com/album/abc123")
        self.assertEqual(result, [])

    @patch("core.Public")
    def test_skips_malformed_items(self, mock_public):
        mock_public.album_info.return_value = iter([
            [
                {"track": {"name": "Good", "artists": {"items": [{"profile": {"name": "Artist"}}]}}},
                {"bad_key": "no track data"},
            ]
        ])
        result = get_album_info("https://open.spotify.com/album/abc123")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Good")

    @patch("core.Public")
    def test_deduplicates_tracks(self, mock_public):
        track = {"track": {"name": "Same", "artists": {"items": [{"profile": {"name": "Artist"}}]}}}
        mock_public.album_info.return_value = iter([[track, track]])
        result = get_album_info("https://open.spotify.com/album/abc123")
        self.assertEqual(len(result), 1)


class TestGetPlaylistInfoAlbumDispatch(unittest.TestCase):
    """Test that get_playlist_info dispatches to get_album_info for album URLs."""

    @patch("core.get_album_info")
    def test_album_url_dispatches_to_album_handler(self, mock_album):
        mock_album.return_value = [{"title": "T", "artist": "A"}]
        url = "https://open.spotify.com/album/2CUXo26JAWIbQx0EVMnjpA?si=abc"
        result = get_playlist_info(url)
        mock_album.assert_called_once_with(url)
        self.assertEqual(result, [{"title": "T", "artist": "A"}])

    @patch("core.Public")
    def test_playlist_url_uses_playlist_api(self, mock_public):
        mock_public.playlist_info.return_value = iter([
            {"items": [{"itemV2": {"data": {"__typename": "Track", "name": "S",
             "artists": {"items": [{"profile": {"name": "A"}}]}}}}]}
        ])
        result = get_playlist_info("https://open.spotify.com/playlist/abc")
        mock_public.playlist_info.assert_called_once()
        self.assertEqual(len(result), 1)


class TestGetSongUrl(unittest.TestCase):
    """Test get_song_url with thread-local YTMusic client."""

    def tearDown(self):
        if hasattr(_thread_local, "ytmusic_client"):
            del _thread_local.ytmusic_client

    @patch("core.YTMusic")
    def test_returns_url_for_song_match(self, mock_yt_cls):
        mock_instance = MagicMock()
        mock_instance.search.return_value = [
            {"resultType": "song", "title": "My Song", "videoId": "abc123"},
        ]
        mock_yt_cls.return_value = mock_instance

        url, title = get_song_url({"title": "My Song", "artist": "Artist"})
        self.assertEqual(url, "https://music.youtube.com/watch?v=abc123")
        self.assertEqual(title, "My Song")

    @patch("core.YTMusic")
    def test_returns_empty_when_no_match(self, mock_yt_cls):
        mock_instance = MagicMock()
        mock_instance.search.return_value = []
        mock_yt_cls.return_value = mock_instance

        url, title = get_song_url({"title": "Unknown", "artist": "Nobody"})
        self.assertEqual(url, "")
        self.assertEqual(title, "")

    @patch("core.YTMusic")
    def test_thread_local_creates_separate_clients(self, mock_yt_cls):
        """Each thread should get its own YTMusic client."""
        mock_instance = MagicMock()
        mock_instance.search.return_value = [
            {"resultType": "song", "title": "Song", "videoId": "v1"},
        ]
        mock_yt_cls.return_value = mock_instance

        client_ids = []

        def worker():
            if hasattr(_thread_local, "ytmusic_client"):
                del _thread_local.ytmusic_client
            get_song_url({"title": "Song", "artist": "Artist"})
            client_ids.append(id(_thread_local.ytmusic_client))

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(client_ids), 3)
        # Each thread should have created a new YTMusic instance
        self.assertEqual(mock_yt_cls.call_count, 3)


class TestGetSongUrls(unittest.TestCase):
    """Test get_song_urls with error handling."""

    @patch("core.get_song_url")
    def test_collects_urls_in_order(self, mock_get_url):
        mock_get_url.side_effect = [
            ("https://music.youtube.com/watch?v=a", "Song A"),
            ("https://music.youtube.com/watch?v=b", "Song B"),
        ]
        urls = get_song_urls(
            [{"title": "A", "artist": "X"}, {"title": "B", "artist": "Y"}],
            concurrent_limit=2,
        )
        self.assertEqual(len(urls), 2)
        self.assertIn("v=a", urls[0])
        self.assertIn("v=b", urls[1])

    @patch("core.get_song_url")
    def test_handles_search_exception_gracefully(self, mock_get_url):
        """A failed search should return empty string, not crash."""
        mock_get_url.side_effect = ConnectionError("rate limited")
        urls = get_song_urls(
            [{"title": "A", "artist": "X"}],
            concurrent_limit=2,
        )
        self.assertEqual(urls, [""])

    @patch("core.get_song_url")
    def test_mixed_success_and_failure(self, mock_get_url):
        """Some searches succeed, some fail; download should continue."""
        mock_get_url.side_effect = [
            ("https://music.youtube.com/watch?v=a", "Song A"),
            ConnectionError("error"),
            ("https://music.youtube.com/watch?v=c", "Song C"),
        ]
        urls = get_song_urls(
            [
                {"title": "A", "artist": "X"},
                {"title": "B", "artist": "Y"},
                {"title": "C", "artist": "Z"},
            ],
            concurrent_limit=2,
        )
        self.assertEqual(len(urls), 3)
        self.assertIn("v=a", urls[0])
        self.assertEqual(urls[1], "")
        self.assertIn("v=c", urls[2])

    @patch("core.get_song_url")
    def test_cancel_flag_stops_processing(self, mock_get_url):
        mock_get_url.return_value = ("url", "title")
        cancel = [True]
        urls = get_song_urls(
            [{"title": "A", "artist": "X"}],
            concurrent_limit=1,
            cancel_flag=cancel,
        )
        # Should return empty or very few results due to cancellation
        self.assertTrue(all(u == "" or u == "url" for u in urls))


class TestRunDownload(unittest.TestCase):
    """Test run_download end-to-end with mocks."""

    @patch("core.download_from_urls")
    @patch("core.get_song_urls")
    @patch("core.get_playlist_info")
    def test_full_flow(self, mock_pi, mock_urls, mock_dl):
        mock_pi.return_value = [{"title": "S", "artist": "A"}]
        mock_urls.return_value = ["url1"]

        with tempfile.TemporaryDirectory() as d:
            msgs = []
            result = run_download(
                playlist_url="id",
                output_dir=d,
                audio_format="m4a",
                title_first=False,
                concurrent_limit=5,
                download_archive=None,
                progress_cb=lambda k, m: msgs.append((k, m)),
            )
        self.assertEqual(len(result), 1)
        self.assertTrue(any(k == "done" for k, _ in msgs))
        mock_dl.assert_called_once()


if __name__ == "__main__":
    unittest.main()
