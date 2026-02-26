# Spotify Playlist Downloader

A GUI application to browse and download Spotify playlists. It fetches track metadata from Spotify (no login required) and downloads each song in high quality via YouTube Music, with embedded metadata (title, artist, album art, etc.).

> **Educational purposes only.** Users are responsible for complying with Spotify's and YouTube Music's terms of service.

---

## Features

- 🎵 **No Spotify account required** – playlist metadata is fetched publicly
- 🖥 **GUI interface** – manage and monitor all downloads in one window
- 📋 **Track list** – see every song in the playlist before downloading
- ☑ **Selective downloads** – check/uncheck individual tracks to download only what you want
- ⬇ **One-click download** – match and download with a single button
- 🎚 **Configurable** – choose output folder, audio format, and concurrency
- 🔍 **Real-time log** – watch matching and download progress live
- 📊 **Progress tracking** – determinate progress bar and per-track status
- ❌ **Cancel at any time** – stop an in-progress download gracefully
- 📦 **Build as .exe** – package into a standalone Windows executable

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
3. **Select tracks** – use the checkboxes (☑/☐) in the track list to choose which songs to download. Use **All** / **None** buttons to quickly select or deselect all.
4. Choose an **Output Directory**, **Audio Format** (`m4a`, `mp3`, `opus`, …), and **Concurrent** search limit.
5. Click **⬇ Download** – the app will match each selected track on YouTube Music, then download and embed metadata automatically.
6. Monitor progress in the **Log** pane and the progress bar; click **✕ Cancel** to abort.

## Building a Standalone Executable

You can package the application into a single `.exe` (Windows) or binary (macOS/Linux) using [PyInstaller](https://pyinstaller.org):

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
python build_exe.py
```

The output will be in the `dist/` directory as `SpotifyDownloader` (or `SpotifyDownloader.exe` on Windows).

## Project Structure

| File | Description |
|------|-------------|
| `main.py` | Application entry point |
| `gui.py` | Tkinter GUI (dark-themed, responsive) |
| `core.py` | Spotify playlist fetching + yt-dlp download logic |
| `build_exe.py` | PyInstaller build script for standalone executable |
| `requirements.txt` | Python dependencies |

## Credits

Core download logic adapted from [invzfnc/spotify-downloader](https://github.com/invzfnc/spotify-downloader).