"""Main Thread terminal user interface coordinating display, menu, and playback loop."""

import os
from queue import Empty, Queue
import select
import sys
import threading
import time

from core.controller import CoreController
from library.listing import format_duration
from library.playlist import PlaylistManager
from library.search import filter_songs, search_songs
from library.song import Song
from library.sorting import sort_songs
from lyrics.lyric_sync import LyricEvent
from ui.lyric_display import LyricDisplay, render_playlist
from ui.menu import (
    format_menu_bar,
    parse_extended_command,
    parse_menu_command,
    render_help,
)


class _NonBlockingInputReader:
    """Cross-platform non-blocking line reader for terminal stdin (Windows & Linux)."""

    def __init__(self) -> None:
        self._input_queue: Queue[str] = Queue()
        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None
        self._eof = False

    def _start_windows_reader(self) -> None:
        """Lazily start a daemon thread reading sys.stdin lines on Windows."""
        if self._reader_thread is not None or self._stop_event.is_set():
            return

        self._reader_thread = threading.Thread(
            target=self._windows_stdin_loop,
            name="StdinInputReaderThread",
            daemon=True,
        )
        self._reader_thread.start()

    def _windows_stdin_loop(self) -> None:
        """Read lines from sys.stdin in background and forward to Queue (no UI access)."""
        while not self._stop_event.is_set():
            try:
                line = sys.stdin.readline()
            except (OSError, ValueError):
                break

            if not line:
                self._eof = True
                break

            if self._stop_event.is_set():
                break

            self._input_queue.put(line.strip())

    def _read_windows(self) -> str | None:
        if self._eof and self._input_queue.empty():
            return None

        self._start_windows_reader()
        try:
            return self._input_queue.get_nowait()
        except Empty:
            return None

    def _read_posix(self) -> str | None:
        if self._eof:
            return None

        try:
            if select.select([sys.stdin], [], [], 0)[0]:
                line = sys.stdin.readline()
                if not line:
                    self._eof = True
                    return None
                return line.strip()
        except (OSError, ValueError):
            return None
        return None

    def read_line(self) -> str | None:
        """Return a stripped command line if available, else None."""
        if os.name == "nt":
            return self._read_windows()
        return self._read_posix()

    def stop(self) -> None:
        """Signal any background stdin reader to stop."""
        self._stop_event.set()


class TerminalUI:
    """Terminal UI controller running exclusively on the Main Thread (FR-11, NFR-04)."""

    def __init__(self) -> None:
        self.lyric_display = LyricDisplay()
        self._input_reader = _NonBlockingInputReader()
        self.playlist_manager = PlaylistManager()
        self._master_songs: list[Song] = []
        self._active_songs: list[Song] = []
        self._active_view_label = "Daftar Koleksi Lagu"

    def render_header(self) -> None:
        """Display the application banner."""
        print("=" * 60)
        print("  TERMINAL MUSIC & LYRIC PLAYER (CLI)")
        print("=" * 60)

    def show_library(self, songs: list[Song]) -> str:
        """Display the active song collection table in the terminal (FR-03)."""
        print(f"\n[{self._active_view_label.upper()}]")
        rendered = render_playlist(songs)
        print("-" * 60)
        return rendered

    def render_now_playing(self, song: Song, index: int | None = None, total: int | None = None) -> None:
        """Display metadata and LRC status for the currently loaded song."""
        track_pos = f" ({index + 1}/{total})" if index is not None and total else ""
        artist_text = song.artist if song.artist else "Unknown Artist"
        duration_text = format_duration(song.duration)
        lrc_info = (
            f"Tersedia ({song.lyric_path.name})"
            if song.has_lyrics and song.lyric_path is not None
            else "Tidak tersedia"
        )

        print("-" * 60)
        print(f"Now Playing{track_pos}: {song.title} - {artist_text} [{duration_text}]")
        print(f"Lirik: {lrc_info}")
        print("-" * 60)
        print(format_menu_bar())
        print("=" * 60)

    def process_lyric_events(self, events: list[LyricEvent]) -> str | None:
        """Render lyric updates received from Queue in Main Thread (FR-11, NFR-01)."""
        last_output: str | None = None
        for event in events:
            rendered = self.lyric_display.update(event)
            if rendered is not None:
                last_output = rendered
        return last_output

    def _switch_to_track(
        self,
        controller: CoreController,
        songs: list[Song],
        target_index: int,
    ) -> int:
        """Load and play the song at target_index and reset lyric display state."""
        song = songs[target_index]
        self.lyric_display.reset()
        controller.load_track(song.audio_path, song.lyric_path)
        controller.play()
        self.render_now_playing(song, index=target_index, total=len(songs))
        return target_index

    def _parse_bool_flag(self, raw_value: str) -> bool:
        """Convert CLI yes/no or true/false tokens into a bool."""
        normalized = raw_value.strip().lower()
        if normalized in {"yes", "ya", "true", "1"}:
            return True
        if normalized in {"no", "tidak", "false", "0"}:
            return False
        raise ValueError(
            f"Nilai filter LRC tidak valid: '{raw_value}'. Gunakan 'yes' atau 'no'."
        )

    def _handle_playlist_command(
        self,
        args: list[str],
        controller: CoreController,
        active_songs: list[Song],
        current_index: int,
    ) -> int:
        """Handle playlist subcommands (create, list, show, add, remove, play)."""
        if not args:
            print(
                "\n[ERROR] Subperintah playlist tidak lengkap. "
                "Gunakan: pl <create|list|show|add|remove|play>"
            )
            return current_index

        subcmd = args[0]

        if subcmd == "create":
            name = " ".join(args[1:]).strip()
            playlist = self.playlist_manager.create_playlist(name)
            print(f"\n[PLAYLIST] Playlist '{playlist.name}' berhasil dibuat.")
            return current_index

        if subcmd == "list":
            playlists = self.playlist_manager.list_playlists()
            if not playlists:
                print("\n[PLAYLIST] Belum ada playlist yang dibuat.")
            else:
                print("\n[DAFTAR PLAYLIST]")
                for idx, playlist in enumerate(playlists, start=1):
                    print(f"  {idx}. {playlist.name} ({len(playlist)} lagu)")
                print("-" * 60)
            return current_index

        if subcmd == "show":
            name = " ".join(args[1:]).strip()
            if not name:
                raise ValueError("Sertakan nama playlist. Contoh: pl show Favorit")
            pl_songs = self.playlist_manager.get_playlist_songs(name)
            print(f"\n[ISI PLAYLIST: {name}]")
            render_playlist(pl_songs)
            print("-" * 60)
            return current_index

        if subcmd == "add":
            if len(args) < 3 or not args[-1].isdigit():
                raise ValueError("Format salah. Gunakan: pl add <nama_playlist> <nomor_lagu>")
            track_number = int(args[-1])
            name = " ".join(args[1:-1]).strip()
            if not (1 <= track_number <= len(active_songs)):
                raise IndexError(
                    f"Nomor lagu {track_number} tidak valid (pilih 1 s/d {len(active_songs)})."
                )
            song = active_songs[track_number - 1]
            added = self.playlist_manager.add_song_to_playlist(name, song)
            if added:
                print(f"\n[PLAYLIST] '{song.title}' ditambahkan ke playlist '{name}'.")
            else:
                print(f"\n[PLAYLIST] '{song.title}' sudah ada di playlist '{name}'.")
            return current_index

        if subcmd == "remove":
            if len(args) < 3 or not args[-1].isdigit():
                raise ValueError("Format salah. Gunakan: pl remove <nama_playlist> <nomor_lagu>")
            track_number = int(args[-1])
            if track_number < 1:
                raise IndexError("Nomor lagu harus dimulai dari 1.")
            name = " ".join(args[1:-1]).strip()
            removed = self.playlist_manager.remove_song_from_playlist(name, track_number - 1)
            print(f"\n[PLAYLIST] '{removed.title}' dihapus dari playlist '{name}'.")
            return current_index

        if subcmd == "play":
            if len(args) < 2:
                raise ValueError("Format salah. Gunakan: pl play <nama_playlist> [nomor_lagu]")
            if len(args) >= 3 and args[-1].isdigit():
                track_number = int(args[-1])
                name = " ".join(args[1:-1]).strip()
            else:
                track_number = 1
                name = " ".join(args[1:]).strip()

            playlist = self.playlist_manager.get_playlist(name)
            if playlist is None:
                raise KeyError(f"Playlist '{name}' tidak ditemukan.")

            pl_songs = playlist.get_songs()
            if not pl_songs:
                raise ValueError(f"Playlist '{playlist.name}' masih kosong.")
            if not (1 <= track_number <= len(pl_songs)):
                raise IndexError(
                    f"Nomor lagu {track_number} tidak valid (pilih 1 s/d {len(pl_songs)})."
                )

            self._active_songs = pl_songs
            self._active_view_label = f"Playlist: {playlist.name}"
            controller.set_playlist(playlist.get_audio_paths())
            self.show_library(self._active_songs)
            return self._switch_to_track(controller, self._active_songs, track_number - 1)

        raise ValueError(
            f"Subperintah playlist '{subcmd}' tidak dikenal. "
            "Gunakan: create, list, show, add, remove, atau play."
        )

    def _apply_song_view(
        self,
        songs: list[Song],
        label: str,
        controller: CoreController,
    ) -> int:
        """Update active song view, sync controller playlist if non-empty, and display."""
        self._active_songs = songs
        self._active_view_label = label
        if self._active_songs:
            controller.set_playlist([s.audio_path for s in self._active_songs])
        self.show_library(self._active_songs)
        return 0

    def _handle_extended_command(
        self,
        raw_cmd: str,
        controller: CoreController,
        current_index: int,
    ) -> tuple[bool, int]:
        """Handle Stage 2 sorting, searching, filtering, reset, and playlist commands."""
        action, args = parse_extended_command(raw_cmd)
        master_songs = self._master_songs
        active_songs = self._active_songs

        try:
            if action == "sort":
                field, order = args[0], args[1]
                sorted_list = sort_songs(active_songs, sort_by=field, order=order)
                idx = self._apply_song_view(
                    sorted_list,
                    f"Daftar Lagu (Sort: {field} {order})",
                    controller,
                )
                return (True, idx)

            if action == "search":
                keyword = args[0]
                matched = search_songs(master_songs, keyword)
                idx = self._apply_song_view(
                    matched,
                    f"Hasil Pencarian: '{keyword}'",
                    controller,
                )
                return (True, idx)

            if action == "filter_lrc":
                has_lrc = self._parse_bool_flag(args[0])
                filtered = filter_songs(master_songs, {"has_lyrics": has_lrc})
                label_status = "Dengan LRC" if has_lrc else "Tanpa LRC"
                idx = self._apply_song_view(
                    filtered,
                    f"Filter LRC: {label_status}",
                    controller,
                )
                return (True, idx)

            if action == "filter_artist":
                artist_name = args[0]
                filtered = filter_songs(master_songs, {"artist": artist_name})
                idx = self._apply_song_view(
                    filtered,
                    f"Filter Artis: '{artist_name}'",
                    controller,
                )
                return (True, idx)

            if action == "reset":
                idx = self._apply_song_view(
                    list(master_songs),
                    "Daftar Koleksi Lagu",
                    controller,
                )
                return (True, idx)

            if action == "playlist":
                updated_index = self._handle_playlist_command(
                    args,
                    controller,
                    active_songs,
                    current_index,
                )
                return (True, updated_index)
        except (ValueError, KeyError, IndexError) as error:
            print(f"\n[ERROR] {error}")
            return (True, current_index)

        print(
            f"\n[ERROR] Perintah '{raw_cmd.strip()}' tidak dikenal. "
            "Ketik 'h' untuk bantuan atau gunakan: l, 1..N, p, r, n, b, s, q"
        )
        return (True, current_index)

    def handle_command(
        self,
        raw_cmd: str,
        controller: CoreController,
        songs: list[Song],
        current_index: int,
    ) -> tuple[bool, int]:
        """Execute a user command and return (continue_running, updated_index)."""
        if not self._master_songs and songs:
            self._master_songs = list(songs)
            self._active_songs = list(songs)

        active_songs = self._active_songs if self._master_songs else songs
        action, track_number = parse_menu_command(raw_cmd)

        if action == "empty":
            return (True, current_index)

        if action == "list":
            self.show_library(active_songs)
            return (True, current_index)

        if action == "help":
            print()
            render_help()
            return (True, current_index)

        if action == "pause":
            controller.pause()
            print("\n[PAUSED] Pemutaran dijeda.")
            return (True, current_index)

        if action == "resume":
            controller.resume()
            print("\n[RESUMED] Pemutaran dilanjutkan.")
            return (True, current_index)

        if action == "play":
            if not active_songs:
                print("\n[INFO] Daftar lagu aktif kosong. Ketik 'reset' untuk kembali ke semua lagu.")
                return (True, 0)
            safe_index = current_index if 0 <= current_index < len(active_songs) else 0
            controller.play()
            print(f"\n[PLAYING] Memutar ulang: {active_songs[safe_index].title}")
            return (True, safe_index)

        if action == "stop":
            controller.stop()
            self.lyric_display.reset()
            print("\n[STOPPED] Pemutaran dihentikan.")
            return (True, current_index)

        if action in {"next", "previous"}:
            if not active_songs:
                print("\n[INFO] Daftar lagu aktif kosong. Ketik 'reset' untuk kembali ke semua lagu.")
                return (True, 0)
            step = 1 if action == "next" else -1
            next_index = (current_index + step) % len(active_songs)
            print(f"\n[SWITCH TRACK] Memutar: {active_songs[next_index].title}")
            updated_index = self._switch_to_track(controller, active_songs, next_index)
            return (True, updated_index)

        if action == "select_track" and track_number is not None:
            if not active_songs:
                print("\n[INFO] Daftar lagu aktif kosong. Ketik 'reset' untuk kembali ke semua lagu.")
                return (True, 0)
            if 1 <= track_number <= len(active_songs):
                target_idx = track_number - 1
                print(f"\n[SELECT TRACK] Memutar #{track_number}: {active_songs[target_idx].title}")
                updated_index = self._switch_to_track(controller, active_songs, target_idx)
                return (True, updated_index)
            print(f"\n[ERROR] Nomor lagu {track_number} tidak valid (pilih 1 s/d {len(active_songs)}).")
            return (True, current_index)

        if action == "quit":
            print("\n[STOPPING] Menutup aplikasi dan membersihkan thread...")
            return (False, current_index)

        return self._handle_extended_command(raw_cmd, controller, current_index)

    def run(self, controller: CoreController, songs: list[Song]) -> None:
        """Start the interactive Main Thread event loop."""
        self._master_songs = list(songs)
        self._active_songs = list(songs)
        self._active_view_label = "Daftar Koleksi Lagu"

        self.render_header()
        self.show_library(self._active_songs)

        current_index = 0
        self._switch_to_track(controller, self._active_songs, current_index)

        is_running = True
        try:
            while is_running:
                # 1. Main Thread polls events from Queue (FR-10, FR-11)
                events = controller.poll_events()
                if events:
                    self.process_lyric_events(events)

                # 2. Check for user keyboard commands (non-blocking)
                cmd = self._input_reader.read_line()
                if cmd is not None:
                    is_running, current_index = self.handle_command(
                        cmd,
                        controller,
                        self._active_songs,
                        current_index,
                    )

                time.sleep(0.08)
        finally:
            self._input_reader.stop()
