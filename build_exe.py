"""
build_exe.py – Build a standalone executable with PyInstaller.

Usage:
    pip install pyinstaller
    python build_exe.py

The resulting executable will be in the ``dist/`` directory.
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    "main.py",
    "--onefile",
    "--windowed",
    "--name=SpotifyDownloader",
    "--clean",
])
