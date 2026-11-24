"""Interactive Main-Thread terminal UI coordinating CoreController and library features."""

from queue import Empty, Queue
import sys
import threading
import time

from core.controller import CoreController
from library.playlist import PlaylistManager
from library.search import filter_songs, search_songs
from library.song import Song
from library.sorting import sort_songs
from ui.lyric_display import LyricDisplay, render_playlist
from ui.menu import parse_command, render_menu


def _read_stdin_loop(input_queue: Queue[str | None], stop_event: threading.Event) -> None:
    """Read lines from stdin into a queue so Windows and Linux stay non-blocking."""
    # Never print or touch UI from this reader thread; Main Thread owns all terminal output (NFR-04).
    while not stop_event.is_set():
        try:
            line = sys.stdin.readline()
        except (EOFError, OSError, ValueError):
            input_queue.put(None)
            break
        if line == "":
            input_queue.put(None)
            break
        input_queue.put(line)


class TerminalUI:
    """Manage interactive CLI playback, library commands, and lyric rendering on Main Thread."""

    def __init__(self) -> None:
        self._all_songs: list[Song] = []
        self._active_songs: list[Song] = []
        self._current_index: int | None = None
        self._current_song: Song | None = None
        self._status = "idle"
        self._playlists = PlaylistManager()
        self._lyric_display = LyricDisplay()

    def run(
        self,
        controller: CoreController,
        songs: list[Song],
        input_queue: Queue[str | None] | None = None,
    ) -> None:
        """Run the interactive Main-Thread loop polling lyric events and user commands."""
        self._all_songs = list(songs)
        self._active_songs = list(songs)
        self._sync_active_playlist(controller)

        print()
        print("-" * 55)
        print("Terminal Music & Lyric Player")
        print("-" * 55)
        print()
        render_playlist(self._active_songs)
        print()
        render_menu()
        print()
        print("Ketik nomor lagu atau perintah, lalu tekan Enter:")

        stop_event = threading.Event()
        if input_queue is None:
            input_queue = Queue()
            threading.Thread(
                target=_read_stdin_loop,
                args=(input_queue, stop_event),
                name="StdinReaderThread",
                daemon=True,
            ).start()

        running = True
        try:
            while running:
                self.poll_lyrics(controller)
                while running:
                    try:
                        raw_line = input_queue.get_nowait()
                    except Empty:
                        break
                    if raw_line is None:
                        running = False
                        break
                    running = self.handle_command(raw_line, controller)
                if running:
                    time.sleep(0.08)
        finally:
            stop_event.set()

    def poll_lyrics(self, controller: CoreController) -> bool:
        """Drain lyric events from CoreController and render only changed lines."""
        rendered = False
        for event in controller.poll_events():
            if self._lyric_display.update(event):
                rendered = True
        return rendered

    def handle_command(self, raw_command: str, controller: CoreController) -> bool:
        """Process one user command and return False when the user wants to quit."""
        action, args = parse_command(raw_command)
        if action == "empty":
            return True
        if action == "quit":
            controller.stop()
            print("Menutup pemutar musik...")
            return False

        handlers = {
            "help": lambda: render_menu(),
            "list": lambda: self._set_active_songs(list(self._all_songs), controller),
            "play_index": lambda: self._handle_play_index(args[0], controller),
            "pause": lambda: self._handle_pause(controller),
            "resume": lambda: self._handle_resume(controller),
            "stop": lambda: self._handle_stop(controller),
            "next": lambda: self._handle_step(1, controller),
            "prev": lambda: self._handle_step(-1, controller),
            "sort": lambda: self._handle_sort(args, controller),
            "search": lambda: self._handle_search(args, controller),
            "filter": lambda: self._handle_filter(args, controller),
            "playlist": lambda: self._handle_playlist(args, controller),
        }
        handler = handlers.get(action)
        if handler is None:
            print(f"Perintah '{args[0]}' tidak dikenal. Ketik 'help' untuk melihat daftar perintah.")
        else:
            handler()
        return True

    def _sync_active_playlist(self, controller: CoreController) -> None:
        controller.set_playlist([song.audio_path for song in self._active_songs])
        self._current_index = (
            self._active_songs.index(self._current_song)
            if self._current_song in self._active_songs
            else None
        )

    def _set_active_songs(self, songs: list[Song], controller: CoreController) -> None:
        self._active_songs = songs
        self._sync_active_playlist(controller)
        render_playlist(self._active_songs)

    def _parse_active_index(self, raw: str) -> int | None:
        if not self._active_songs:
            print("Daftar lagu aktif masih kosong.")
            return None
        if not (raw.isascii() and raw.isdigit()):
            print(f"Nomor lagu tidak valid. Pilih 1 sampai {len(self._active_songs)}.")
            return None
        index = int(raw) - 1
        if index < 0 or index >= len(self._active_songs):
            print(f"Nomor lagu tidak valid. Pilih 1 sampai {len(self._active_songs)}.")
            return None
        return index

    def _play_song_at(self, controller: CoreController, index: int) -> None:
        song = self._active_songs[index]
        try:
            controller.load_track(song.audio_path, song.lyric_path)
            # Drain any leftover queue events from the previous track before starting playback.
            controller.poll_events()
            self._lyric_display.reset()
            controller.play()
        except (FileNotFoundError, ValueError, RuntimeError, OSError) as err:
            print(f"Gagal memutar '{song.title}': {err}")
            return

        self._current_index = index
        self._current_song = song
        self._status = "playing"
        artist = song.artist or "Artis tidak diketahui"
        lyric_info = song.lyric_path.name if song.lyric_path else "Tanpa LRC"
        print(f"Memutar [{index + 1}/{len(self._active_songs)}]: {song.title} ({artist}) [{lyric_info}]")

    def _handle_play_index(self, index_text: str, controller: CoreController) -> None:
        index = self._parse_active_index(index_text)
        if index is not None:
            self._play_song_at(controller, index)

    def _handle_pause(self, controller: CoreController) -> None:
        if self._current_song is None or self._status != "playing":
            print("Pemutaran sudah dijeda." if self._status == "paused" else "Belum ada lagu yang sedang diputar.")
            return
        try:
            controller.pause()
        except RuntimeError as err:
            print(f"Gagal menjeda lagu: {err}")
            return
        self._status = "paused"
        print(f"Dijeda: {self._current_song.title}")

    def _handle_resume(self, controller: CoreController) -> None:
        if self._current_song is None or self._status != "paused":
            print("Lagu sedang diputar." if self._status == "playing" else "Tidak ada lagu yang dijeda.")
            return
        try:
            controller.resume()
        except RuntimeError as err:
            print(f"Gagal melanjutkan lagu: {err}")
            return
        self._status = "playing"
        print(f"Dilanjutkan: {self._current_song.title}")

    def _handle_stop(self, controller: CoreController) -> None:
        controller.stop()
        controller.poll_events()
        self._lyric_display.reset()
        self._status = "stopped"
        print(f"Dihentikan: {self._current_song.title}" if self._current_song else "Pemutaran dihentikan.")

    def _handle_step(self, step: int, controller: CoreController) -> None:
        if not self._active_songs:
            print("Daftar lagu aktif masih kosong.")
            return
        if self._current_index is None:
            target = 0 if step > 0 else len(self._active_songs) - 1
        else:
            target = (self._current_index + step) % len(self._active_songs)
        self._play_song_at(controller, target)

    def _handle_sort(self, args: list[str], controller: CoreController) -> None:
        if len(args) > 2:
            print("Format salah. Gunakan: sort <title|artist|duration|date_added> [asc|desc]")
            return
        sort_by = args[0] if len(args) >= 1 else "title"
        order = args[1] if len(args) >= 2 else "asc"
        try:
            sorted_list = sort_songs(self._active_songs, sort_by, order)
        except ValueError as err:
            print(err)
            return
        self._set_active_songs(sorted_list, controller)

    def _handle_search(self, args: list[str], controller: CoreController) -> None:
        keyword = " ".join(args).strip()
        if not keyword:
            print("Masukkan kata kunci pencarian. Contoh: search senja")
            return
        matches = search_songs(self._all_songs, keyword)
        if not matches:
            print(f"Tidak ada lagu yang cocok dengan '{keyword}'.")
            return
        self._set_active_songs(matches, controller)

    def _handle_filter(self, args: list[str], controller: CoreController) -> None:
        if len(args) < 2:
            print("Format filter: filter lrc <ya|tidak> atau filter artist <nama>")
            return
        kind = args[0].lower()
        value = " ".join(args[1:]).strip()
        if kind == "lrc":
            lowered = value.lower()
            if lowered in {"ya", "ada", "true", "1"}:
                criteria: dict[str, object] = {"has_lyrics": True}
            elif lowered in {"tidak", "none", "false", "0"}:
                criteria = {"has_lyrics": False}
            else:
                print("Nilai filter lrc tidak valid. Gunakan: ya atau tidak.")
                return
        elif kind == "artist":
            criteria = {"artist": value}
        else:
            print("Jenis filter tidak dikenal. Gunakan: filter lrc <ya|tidak> atau filter artist <nama>.")
            return

        matches = filter_songs(self._all_songs, criteria)
        if not matches:
            print("Tidak ada lagu yang sesuai kriteria filter.")
            return
        self._set_active_songs(matches, controller)

    def _handle_playlist(self, args: list[str], controller: CoreController) -> None:
        sub = args[0].lower() if args else "list"
        try:
            if sub == "list":
                names = self._playlists.list_names()
                if not names:
                    print("Belum ada playlist. Buat baru dengan: playlist new <nama>")
                    return
                for name in names:
                    print(f"- {name} ({len(self._playlists.get_songs(name))} lagu)")
                return

            if sub == "new":
                name = " ".join(args[1:]).strip()
                self._playlists.create(name)
                print(f"Playlist '{name}' dibuat.")
                return

            if sub in {"add", "remove"}:
                if len(args) < 3 or not (args[-1].isascii() and args[-1].isdigit()):
                    print(f"Format: playlist {sub} <nama> <nomor_lagu>")
                    return
                name = " ".join(args[1:-1]).strip()
                if sub == "add":
                    song_idx = self._parse_active_index(args[-1])
                    if song_idx is None:
                        return
                    song = self._active_songs[song_idx]
                    self._playlists.add_song(name, song)
                    print(f"Ditambahkan ke '{name}': {song.title}")
                else:
                    removed = self._playlists.remove_song(name, int(args[-1]) - 1)
                    print(f"Dihapus dari '{name}': {removed.title}")
                return

            if sub in {"show", "play"}:
                name = " ".join(args[1:]).strip()
                if not name:
                    print(f"Format: playlist {sub} <nama>")
                    return
                pl_songs = self._playlists.get_songs(name)
                if not pl_songs:
                    print(f"Playlist '{name}' masih kosong.")
                    return
                if sub == "show":
                    print(f"Playlist: {name}")
                    render_playlist(pl_songs)
                else:
                    self._set_active_songs(pl_songs, controller)
                    self._play_song_at(controller, 0)
                return

            print("Subperintah playlist tidak dikenal. Gunakan: list, new, add, remove, show, play.")
        except (ValueError, KeyError, IndexError) as err:
            print(err)
