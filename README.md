# Spotify Playlist Downloader

A GUI application to browse and download Spotify playlists. It fetches track metadata from Spotify (no login required) and downloads each song in high quality via YouTube Music, with embedded metadata (title, artist, album art, etc.).

> **Educational purposes only.** Users are responsible for complying with Spotify's and YouTube Music's terms of service.

---

## Features

- 🎵 **No Spotify account required** – playlist metadata is fetched publicly
- 🖥 **GUI interface** – manage and monitor all downloads in one window
- 📋 **Track list** – see every song in the playlist before downloading
- ⬇ **One-click download** – match and download with a single button
- 🎚 **Configurable** – choose output folder, audio format, and concurrency
- 🔍 **Real-time log** – watch matching and download progress live
- ❌ **Cancel at any time** – stop an in-progress download gracefully

## Screenshot

![Spotify Playlist Downloader GUI](https://github.com/user-attachments/assets/1faea087-613d-459f-b5e2-66e911bbee37)

## Requirements

- Python 3.12+
- [ffmpeg](https://ffmpeg.org/download.html) installed and on your `PATH`

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/aaaaaaayush-no/spotify.git
cd spotify

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate.bat     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch the GUI
python main.py
```

## Usage

1. Paste a **public Spotify playlist URL** into the *Playlist URL* field.
2. *(Optional)* Click **Fetch Tracks** to preview the track list before downloading.
3. Choose an **Output Directory**, **Audio Format** (`m4a`, `mp3`, `opus`, …), and **Concurrent** search limit.
4. Click **⬇ Download** – the app will match each track on YouTube Music, then download and embed metadata automatically.
5. Monitor progress in the **Log** pane; click **✕ Cancel** to abort.

## Project Structure

| File | Description |
|------|-------------|
| `main.py` | Application entry point |
| `gui.py` | Tkinter GUI (dark-themed, responsive) |
| `core.py` | Spotify playlist fetching + yt-dlp download logic |
| `requirements.txt` | Python dependencies |

## Credits

Core download logic adapted from [invzfnc/spotify-downloader](https://github.com/invzfnc/spotify-downloader).