"""
gui.py – Tkinter GUI for the Spotify Playlist Downloader.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core import (
    AUDIO_FORMAT,
    CONCURRENT_FRAGMENT_DOWNLOADS,
    CONCURRENT_LIMIT,
    DOWNLOAD_PATH,
    get_playlist_info,
    run_download,
)

AUDIO_FORMATS = ["m4a", "mp3", "opus", "flac", "wav", "aac"]

# ── color palette ─────────────────────────────────────────────────────────────
BG = "#121212"
SURFACE = "#1e1e1e"
SURFACE2 = "#2a2a2a"
ACCENT = "#1db954"          # Spotify green
ACCENT_HOVER = "#1ed760"
TEXT = "#ffffff"
TEXT_MUTED = "#b3b3b3"
ERROR = "#e74c3c"
WARN = "#f39c12"


class SpotifyDownloaderApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Spotify Playlist Downloader")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(720, 560)

        # state
        self._cancel_flag: list[bool] = [False]
        self._worker: threading.Thread | None = None
        self._progress_total: int = 0
        self._progress_done: int = 0

        self._build_ui()
        self.update_idletasks()
        self._center()

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_header()
        self._build_settings()
        self._build_panes()
        self._build_footer()

    def _build_header(self) -> None:
        hdr = tk.Frame(self, bg=BG, pady=14)
        hdr.grid(row=0, column=0, sticky="ew", padx=20)

        tk.Label(
            hdr, text="🎵  Spotify Playlist Downloader",
            bg=BG, fg=ACCENT,
            font=("Helvetica", 18, "bold"),
        ).pack(side="left")

        tk.Label(
            hdr, text="powered by YouTube Music",
            bg=BG, fg=TEXT_MUTED,
            font=("Helvetica", 10),
        ).pack(side="left", padx=(10, 0), anchor="s", pady=3)

    def _build_settings(self) -> None:
        frame = tk.LabelFrame(
            self, text=" Settings ", bg=SURFACE,
            fg=TEXT_MUTED, bd=0,
            font=("Helvetica", 9),
        )
        frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        # ── Playlist URL ──────────────────────────────────────────────────────
        self._add_label(frame, "Playlist URL:", 0)
        url_row = tk.Frame(frame, bg=SURFACE)
        url_row.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=5)
        url_row.columnconfigure(0, weight=1)

        self.url_var = tk.StringVar()
        url_entry = self._entry(url_row, self.url_var, placeholder="https://open.spotify.com/playlist/…")
        url_entry.grid(row=0, column=0, sticky="ew")

        self._btn(url_row, "Fetch Tracks", self._fetch_tracks, width=12).grid(
            row=0, column=1, padx=(6, 0)
        )

        # ── Output directory ─────────────────────────────────────────────────
        self._add_label(frame, "Output Dir:", 1)
        dir_row = tk.Frame(frame, bg=SURFACE)
        dir_row.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=5)
        dir_row.columnconfigure(0, weight=1)

        self.dir_var = tk.StringVar(value=os.path.abspath(DOWNLOAD_PATH))
        self._entry(dir_row, self.dir_var).grid(row=0, column=0, sticky="ew")
        self._btn(dir_row, "Browse…", self._browse_dir, secondary=True, width=8).grid(
            row=0, column=1, padx=(6, 0)
        )

        # ── Audio format ─────────────────────────────────────────────────────
        self._add_label(frame, "Audio Format:", 2)
        self.fmt_var = tk.StringVar(value=AUDIO_FORMAT)
        fmt_combo = ttk.Combobox(
            frame, textvariable=self.fmt_var,
            values=AUDIO_FORMATS, state="readonly", width=8,
        )
        fmt_combo.grid(row=2, column=1, sticky="w", padx=(0, 10), pady=5)
        self._style_combobox(fmt_combo)

        # ── Concurrent limit ─────────────────────────────────────────────────
        self._add_label(frame, "Concurrent:", 3)
        conc_row = tk.Frame(frame, bg=SURFACE)
        conc_row.grid(row=3, column=1, sticky="w", padx=(0, 10), pady=5)

        self.conc_var = tk.IntVar(value=CONCURRENT_LIMIT)
        self._spinbox(conc_row, self.conc_var, 1, 20).pack(side="left")

        tk.Label(
            conc_row, text="simultaneous searches",
            bg=SURFACE, fg=TEXT_MUTED, font=("Helvetica", 9),
        ).pack(side="left", padx=(6, 0))

        # ── Concurrent fragment downloads ────────────────────────────────────
        self._add_label(frame, "Fragments:", 4)
        frag_row = tk.Frame(frame, bg=SURFACE)
        frag_row.grid(row=4, column=1, sticky="w", padx=(0, 10), pady=5)

        self.frag_var = tk.IntVar(value=CONCURRENT_FRAGMENT_DOWNLOADS)
        self._spinbox(frag_row, self.frag_var, 1, 32).pack(side="left")

        tk.Label(
            frag_row, text="concurrent fragment downloads",
            bg=SURFACE, fg=TEXT_MUTED, font=("Helvetica", 9),
        ).pack(side="left", padx=(6, 0))

        # ── Title-first option ────────────────────────────────────────────────
        self.title_first_var = tk.BooleanVar(value=False)
        chk = tk.Checkbutton(
            frame,
            text='Save as "<title> – <artist>" (default: artist first)',
            variable=self.title_first_var,
            bg=SURFACE, fg=TEXT, selectcolor=SURFACE2,
            activebackground=SURFACE, activeforeground=TEXT,
            font=("Helvetica", 9),
        )
        chk.grid(row=5, column=1, sticky="w", padx=(0, 10), pady=(2, 6))

    def _build_panes(self) -> None:
        pane = tk.PanedWindow(
            self, orient=tk.HORIZONTAL,
            bg=BG, sashwidth=6, sashrelief="flat",
        )
        pane.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 6))

        # left – track list
        left = tk.Frame(pane, bg=SURFACE, bd=0)
        pane.add(left, minsize=200, stretch="always")
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        track_hdr = tk.Frame(left, bg=SURFACE)
        track_hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            track_hdr, text="Track List", bg=SURFACE, fg=TEXT_MUTED,
            font=("Helvetica", 9, "bold"), anchor="w", pady=4,
        ).pack(side="left", padx=8)

        self.track_count_var = tk.StringVar(value="")
        tk.Label(
            track_hdr, textvariable=self.track_count_var,
            bg=SURFACE, fg=TEXT_MUTED, font=("Helvetica", 8),
        ).pack(side="left", padx=(4, 0))

        self._btn(track_hdr, "All", self._select_all,
                  secondary=True, width=4, pady=0).pack(side="right", padx=(0, 6))
        self._btn(track_hdr, "None", self._deselect_all,
                  secondary=True, width=4, pady=0).pack(side="right", padx=(0, 4))

        cols = ("sel", "title", "artist", "status")
        self.track_tree = ttk.Treeview(
            left, columns=cols, show="headings",
            selectmode="browse",
        )
        self._style_tree()
        for col, heading, width in [
            ("sel", "✓", 30),
            ("title", "Title", 210),
            ("artist", "Artist", 130),
            ("status", "Status", 80),
        ]:
            self.track_tree.heading(col, text=heading, anchor="w")
            self.track_tree.column(col, width=width, anchor="w",
                                   stretch=(col != "sel"))
        self.track_tree.column("sel", minwidth=30, stretch=False)
        self.track_tree.bind("<ButtonRelease-1>", self._on_tree_click)

        sb_v = ttk.Scrollbar(left, orient="vertical",
                              command=self.track_tree.yview)
        self.track_tree.configure(yscrollcommand=sb_v.set)
        self.track_tree.grid(row=1, column=0, sticky="nsew")
        sb_v.grid(row=1, column=1, sticky="ns")

        # right – log
        right = tk.Frame(pane, bg=SURFACE, bd=0)
        pane.add(right, minsize=200, stretch="always")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        log_hdr = tk.Frame(right, bg=SURFACE)
        log_hdr.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            log_hdr, text="Log", bg=SURFACE, fg=TEXT_MUTED,
            font=("Helvetica", 9, "bold"), anchor="w", pady=4,
        ).pack(side="left", padx=8)
        self._btn(log_hdr, "Clear", self._clear_log,
                  secondary=True, width=6, pady=0).pack(side="right", padx=6)

        self.log_text = tk.Text(
            right, state="disabled", bg=SURFACE2, fg=TEXT,
            font=("Courier", 9), relief="flat", bd=0,
            wrap="word", insertbackground=TEXT,
        )
        sb_log = ttk.Scrollbar(right, orient="vertical",
                                command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb_log.set)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        sb_log.grid(row=1, column=1, sticky="ns")

        # tag colours for log
        self.log_text.tag_configure("status", foreground=ACCENT)
        self.log_text.tag_configure("found", foreground="#5dade2")
        self.log_text.tag_configure("matching", foreground=TEXT_MUTED)
        self.log_text.tag_configure("download", foreground=TEXT)
        self.log_text.tag_configure("done", foreground=ACCENT)
        self.log_text.tag_configure("error", foreground=ERROR)
        self.log_text.tag_configure("info", foreground=TEXT_MUTED)

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg=BG)
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 14))
        footer.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(
            footer, textvariable=self.status_var,
            bg=BG, fg=TEXT_MUTED, font=("Helvetica", 9), anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.progress = ttk.Progressbar(
            footer, mode="determinate", length=160, maximum=100,
        )
        self.progress.grid(row=0, column=1, padx=(0, 10))

        self.dl_btn = self._btn(footer, "⬇  Download", self._start_download, width=14)
        self.dl_btn.grid(row=0, column=2)

        self.cancel_btn = self._btn(
            footer, "✕  Cancel", self._cancel_download,
            secondary=True, width=10,
        )
        self.cancel_btn.grid(row=0, column=3, padx=(8, 0))
        self.cancel_btn.config(state="disabled")

    # ── widget helpers ────────────────────────────────────────────────────────

    def _add_label(self, parent: tk.Widget, text: str, row: int) -> None:
        tk.Label(
            parent, text=text, bg=SURFACE, fg=TEXT_MUTED,
            font=("Helvetica", 9), anchor="e", width=13,
        ).grid(row=row, column=0, sticky="e", padx=(10, 4), pady=5)

    def _entry(
        self, parent: tk.Widget, var: tk.Variable, placeholder: str = ""
    ) -> tk.Entry:
        e = tk.Entry(
            parent, textvariable=var,
            bg=SURFACE2, fg=TEXT, insertbackground=TEXT,
            relief="flat", bd=4, font=("Helvetica", 10),
        )
        if placeholder and not var.get():
            e.insert(0, placeholder)
            e.config(fg=TEXT_MUTED)

            def on_focus_in(event: tk.Event) -> None:
                if e.get() == placeholder:
                    e.delete(0, "end")
                    e.config(fg=TEXT)

            def on_focus_out(event: tk.Event) -> None:
                if not e.get():
                    e.insert(0, placeholder)
                    e.config(fg=TEXT_MUTED)

            e.bind("<FocusIn>", on_focus_in)
            e.bind("<FocusOut>", on_focus_out)
        return e

    def _btn(
        self, parent: tk.Widget, text: str,
        command: object, secondary: bool = False,
        width: int = 10, pady: int = 4,
    ) -> tk.Button:
        bg = SURFACE2 if secondary else ACCENT
        fg = TEXT_MUTED if secondary else "#000000"
        abg = SURFACE if secondary else ACCENT_HOVER

        btn = tk.Button(
            parent, text=text, command=command,  # type: ignore[arg-type]
            bg=bg, fg=fg,
            activebackground=abg, activeforeground=fg,
            font=("Helvetica", 9, "bold"),
            relief="flat", bd=0,
            width=width, pady=pady,
            cursor="hand2",
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=abg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    def _spinbox(
        self, parent: tk.Widget, var: tk.IntVar, from_: int, to: int
    ) -> tk.Spinbox:
        return tk.Spinbox(
            parent, from_=from_, to=to, textvariable=var,
            bg=SURFACE2, fg=TEXT, insertbackground=TEXT,
            buttonbackground=SURFACE2,
            relief="flat", bd=4, width=4,
            font=("Helvetica", 10),
        )

    def _style_combobox(self, combo: ttk.Combobox) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=SURFACE2,
            background=SURFACE2,
            foreground=TEXT,
            arrowcolor=TEXT_MUTED,
            bordercolor=SURFACE2,
        )

    def _style_tree(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Treeview",
            background=SURFACE2,
            foreground=TEXT,
            fieldbackground=SURFACE2,
            rowheight=24,
            font=("Helvetica", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=SURFACE,
            foreground=TEXT_MUTED,
            relief="flat",
            font=("Helvetica", 9, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#000000")],
        )

    # ── actions ───────────────────────────────────────────────────────────────

    def _center(self) -> None:
        w, h = 860, 620
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory(
            title="Select download folder",
            initialdir=self.dir_var.get(),
        )
        if path:
            self.dir_var.set(path)

    def _fetch_tracks(self) -> None:
        url = self._get_url()
        if not url:
            return

        self._clear_tracks()
        self._log("status", f"Fetching playlist: {url}")
        self.status_var.set("Fetching playlist…")
        self.progress.start(12)

        def worker() -> None:
            tracks = get_playlist_info(url)
            self.after(0, lambda: self._on_fetch_done(tracks))

        threading.Thread(target=worker, daemon=True).start()

    def _on_fetch_done(self, tracks: list) -> None:
        self.progress.stop()
        self.progress["value"] = 0
        if not tracks:
            self.status_var.set("No tracks found – check the URL.")
            self._log("error", "No tracks found. Make sure the playlist is public.")
            return

        for t in tracks:
            self.track_tree.insert(
                "", "end",
                values=("☑", t["title"], t["artist"], "—"),
            )

        self._update_track_count()
        self.status_var.set(f"{len(tracks)} tracks loaded.")
        self._log("status", f"Loaded {len(tracks)} tracks.")

    def _start_download(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "A download is already in progress.")
            return

        url = self._get_url()
        if not url:
            return

        output_dir = self.dir_var.get().strip()
        if not output_dir:
            messagebox.showwarning("Missing output dir", "Please select an output directory.")
            return

        # build selected track list from tree (if tracks have been fetched)
        selected_tracks: list[dict] | None = None
        children = self.track_tree.get_children()
        if children:
            selected_tracks = []
            for iid in children:
                vals = self.track_tree.item(iid, "values")
                if vals[0] == "☑":
                    selected_tracks.append({"title": vals[1], "artist": vals[2]})
            if not selected_tracks:
                messagebox.showwarning(
                    "No tracks selected",
                    "Please select at least one track to download.",
                )
                return

        self._cancel_flag[0] = False
        self._progress_total = len(selected_tracks) if selected_tracks else 0
        self._progress_done = 0
        self.dl_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress["value"] = 0
        self.progress.start(12)
        self.status_var.set("Starting…")

        audio_fmt = self.fmt_var.get()
        concurrent = self.conc_var.get()
        title_first = self.title_first_var.get()
        frag_dl = self.frag_var.get()

        # pre-populate track list if empty
        if not children:
            self._log("status", "No tracks pre-fetched; fetching now…")

        def worker() -> None:
            run_download(
                playlist_url=url,
                output_dir=output_dir,
                audio_format=audio_fmt,
                title_first=title_first,
                concurrent_limit=concurrent,
                download_archive=None,
                concurrent_fragment_downloads=frag_dl,
                progress_cb=self._on_progress,
                cancel_flag=self._cancel_flag,
                selected_tracks=selected_tracks,
            )
            self.after(0, self._on_download_done)

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _cancel_download(self) -> None:
        self._cancel_flag[0] = True
        self.status_var.set("Cancelling…")
        self._log("error", "Cancel requested – finishing current batch…")

    def _on_progress(self, kind: str, message: str) -> None:
        """Called from the worker thread; schedules GUI update on main thread."""
        self.after(0, lambda: self._handle_progress(kind, message))

    def _handle_progress(self, kind: str, message: str) -> None:
        self._log(kind, message)

        if kind == "status":
            self.status_var.set(message)
        elif kind == "done":
            self.status_var.set(message)
            self.progress.stop()
            self.progress["value"] = 100
            for iid in self.track_tree.get_children():
                vals = self.track_tree.item(iid, "values")
                if vals[0] == "☑":
                    self.track_tree.set(iid, "status", "✓")
        elif kind == "found":
            name = message.replace("Found: ", "").split(" (")[0]
            for iid in self.track_tree.get_children():
                title = self.track_tree.item(iid, "values")[1]
                if title in name or name in title:
                    self.track_tree.set(iid, "status", "matched")
                    break
            self._advance_progress()
        elif kind == "not_found":
            self._advance_progress()

    def _advance_progress(self) -> None:
        """Increment the determinate progress bar by one track."""
        self._progress_done += 1
        if self._progress_total > 0:
            if self._progress_done == 1:
                self.progress.stop()          # stop indeterminate animation once
            self.progress["value"] = int(
                self._progress_done / self._progress_total * 100
            )

    def _on_download_done(self) -> None:
        self.progress.stop()
        self.dl_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

    def _clear_tracks(self) -> None:
        for iid in self.track_tree.get_children():
            self.track_tree.delete(iid)

    def _get_url(self) -> str:
        raw = self.url_var.get().strip()
        placeholder = "https://open.spotify.com/playlist/…"
        if not raw or raw == placeholder:
            messagebox.showwarning("Missing URL", "Please enter a Spotify playlist URL.")
            return ""
        return raw

    def _log(self, tag: str, message: str) -> None:
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    # ── selection helpers ─────────────────────────────────────────────────────

    def _on_tree_click(self, event: tk.Event) -> None:
        """Toggle the checkbox when the '✓' column is clicked."""
        region = self.track_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col = self.track_tree.identify_column(event.x)
        if col != "#1":  # first column is the checkbox
            return
        iid = self.track_tree.identify_row(event.y)
        if not iid:
            return
        cur = self.track_tree.item(iid, "values")[0]
        new_val = "☐" if cur == "☑" else "☑"
        vals = list(self.track_tree.item(iid, "values"))
        vals[0] = new_val
        self.track_tree.item(iid, values=vals)
        self._update_track_count()

    def _select_all(self) -> None:
        for iid in self.track_tree.get_children():
            vals = list(self.track_tree.item(iid, "values"))
            vals[0] = "☑"
            self.track_tree.item(iid, values=vals)
        self._update_track_count()

    def _deselect_all(self) -> None:
        for iid in self.track_tree.get_children():
            vals = list(self.track_tree.item(iid, "values"))
            vals[0] = "☐"
            self.track_tree.item(iid, values=vals)
        self._update_track_count()

    def _update_track_count(self) -> None:
        children = self.track_tree.get_children()
        total = len(children)
        selected = sum(
            1 for iid in children
            if self.track_tree.item(iid, "values")[0] == "☑"
        )
        if total:
            self.track_count_var.set(f"{selected}/{total} selected")
        else:
            self.track_count_var.set("")


def launch() -> None:
    app = SpotifyDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    launch()
