"""Unit tests for Anggota 3 modules: library management, playlist, menu, and UI."""

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from core.controller import CoreController
from library.listing import format_duration, format_song_list
from library.playlist import PlaylistManager
from library.scanner import scan_directory
from library.search import filter_songs, search_songs
from library.song import Song
from library.sorting import sort_songs
from lyrics.lyric_sync import LyricEvent
from ui.lyric_display import LyricDisplay, render_lyric
from ui.menu import parse_command
from ui.terminal_ui import TerminalUI


class ScannerTest(unittest.TestCase):
    """Test directory scanning and MP3/LRC pairing (TC-01, TC-02, TC-03)."""

    def test_scan_mp3_and_pair_lrc_locations(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            music_dir = root / "music"
            lyrics_dir = root / "lyrics"
            music_dir.mkdir()
            lyrics_dir.mkdir()

            (music_dir / "lagu_satu.mp3").touch()
            (music_dir / "lagu_dua.mp3").touch()
            (music_dir / "catatan.txt").touch()
            (lyrics_dir / "lagu_satu.lrc").write_text(
                "[ti:Lagu Satu]\n[ar:Penyanyi A]\n[00:01.00]Halo\n",
                encoding="utf-8",
            )
            (music_dir / "lagu_dua.lrc").write_bytes(b"\xff\xfeinvalid")

            songs = scan_directory(music_dir, lyrics_dir=lyrics_dir)

            self.assertEqual(len(songs), 2)
            by_stem = {song.audio_path.stem: song for song in songs}
            self.assertEqual(by_stem["lagu_satu"].lyric_path, lyrics_dir / "lagu_satu.lrc")
            self.assertEqual(by_stem["lagu_satu"].title, "Lagu Satu")
            self.assertEqual(by_stem["lagu_satu"].artist, "Penyanyi A")
            self.assertEqual(by_stem["lagu_dua"].lyric_path, music_dir / "lagu_dua.lrc")
            self.assertEqual(by_stem["lagu_dua"].title, "Lagu Dua")
            self.assertIsNone(by_stem["lagu_dua"].artist)

    def test_scan_mp3_without_lrc_and_missing_folder(self) -> None:
        with TemporaryDirectory() as tmp:
            music_dir = Path(tmp) / "music"
            music_dir.mkdir()
            (music_dir / "tanpa_lirik.mp3").touch()

            songs = scan_directory(music_dir)
            self.assertEqual(len(songs), 1)
            self.assertIsNone(songs[0].lyric_path)
            self.assertEqual(songs[0].title, "Tanpa Lirik")
            self.assertIsNone(songs[0].artist)
            self.assertIsNone(songs[0].duration)
            self.assertFalse(songs[0].has_lyrics)
            self.assertEqual(scan_directory(Path(tmp) / "tidak_ada"), [])

    def test_scan_artist_title_filename_format(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            music_dir = root / "music"
            lyrics_dir = root / "lyrics"
            music_dir.mkdir()
            lyrics_dir.mkdir()

            (music_dir / "Reality Club - Anything You Want.mp3").touch()
            (lyrics_dir / "Reality Club - Anything You Want.lrc").write_text(
                "[00:01.00]Trails of smoke\n",
                encoding="utf-8",
            )
            (music_dir / "Reality Club - Anything You Want - Acoustic.mp3").touch()
            (music_dir / "contoh_lagu.mp3").touch()

            songs = scan_directory(music_dir, lyrics_dir=lyrics_dir)
            by_stem = {song.audio_path.stem: song for song in songs}

            self.assertEqual(by_stem["Reality Club - Anything You Want"].artist, "Reality Club")
            self.assertEqual(by_stem["Reality Club - Anything You Want"].title, "Anything You Want")
            self.assertEqual(
                by_stem["Reality Club - Anything You Want"].lyric_path,
                lyrics_dir / "Reality Club - Anything You Want.lrc",
            )
            self.assertEqual(
                by_stem["Reality Club - Anything You Want - Acoustic"].artist,
                "Reality Club",
            )
            self.assertEqual(
                by_stem["Reality Club - Anything You Want - Acoustic"].title,
                "Anything You Want - Acoustic",
            )
            self.assertIsNone(by_stem["contoh_lagu"].artist)
            self.assertEqual(by_stem["contoh_lagu"].title, "Contoh Lagu")

    @patch("library.scanner.pygame.mixer")
    def test_scan_reads_duration_and_handles_invalid_mp3(self, mixer: MagicMock) -> None:
        mixer.get_init.return_value = True

        def fake_sound(path_str: str) -> MagicMock:
            if path_str.endswith("rusak.mp3"):
                raise RuntimeError("corrupt mp3")
            sound = MagicMock()
            sound.get_length.return_value = 185.4
            return sound

        mixer.Sound.side_effect = fake_sound

        with TemporaryDirectory() as tmp:
            music_dir = Path(tmp)
            (music_dir / "valid.mp3").write_bytes(b"MP3DATA")
            (music_dir / "kosong.mp3").touch()
            (music_dir / "rusak.mp3").write_bytes(b"BADDATA")

            songs = scan_directory(music_dir)
            by_stem = {song.audio_path.stem: song for song in songs}

            self.assertEqual(by_stem["valid"].duration, 185.4)
            self.assertIsNone(by_stem["kosong"].duration)
            self.assertIsNone(by_stem["rusak"].duration)


class LibraryOperationsTest(unittest.TestCase):
    """Test listing, sorting (TC-09), searching (TC-10), and filtering (TC-11)."""

    def setUp(self) -> None:
        self.songs = [
            Song(Path("c.mp3"), Path("c.lrc"), "Cinta", "Raisa", 215.0),
            Song(Path("a.mp3"), None, "Angin", None, None),
            Song(Path("b.mp3"), Path("b.lrc"), "Bintang", "Andmesh", 180.0),
        ]

    def test_listing_formats_fields_and_empty_state(self) -> None:
        self.assertEqual(format_duration(None), "--:--")
        self.assertEqual(format_duration(125.9), "02:05")
        self.assertEqual(format_song_list([]), "Daftar lagu kosong.")

        table = format_song_list(self.songs)
        self.assertIn("Cinta", table)
        self.assertIn("Raisa", table)
        self.assertIn("03:35", table)
        self.assertIn("Ada", table)
        self.assertIn("Tidak ada", table)
        self.assertIn("--:--", table)

    def test_sort_songs_pure_and_orders(self) -> None:
        original = list(self.songs)

        asc = sort_songs(self.songs, "title", "asc")
        desc = sort_songs(self.songs, "title", "desc")
        by_artist = sort_songs(self.songs, "artist", "asc")
        by_duration = sort_songs(self.songs, "duration", "desc")

        self.assertEqual(self.songs, original)
        self.assertEqual([s.title for s in asc], ["Angin", "Bintang", "Cinta"])
        self.assertEqual([s.title for s in desc], ["Cinta", "Bintang", "Angin"])
        self.assertEqual([s.title for s in by_artist], ["Bintang", "Cinta", "Angin"])
        self.assertEqual([s.title for s in by_duration], ["Cinta", "Bintang", "Angin"])

        with TemporaryDirectory() as tmp:
            old_file = Path(tmp) / "lama.mp3"
            new_file = Path(tmp) / "baru.mp3"
            old_file.touch()
            new_file.touch()
            os.utime(old_file, (1000, 1000))
            os.utime(new_file, (2000, 2000))
            dated = [
                Song(old_file, None, "Lama", None, None),
                Song(new_file, None, "Baru", None, None),
            ]
            newest_first = sort_songs(dated, "date_added", "desc")
            self.assertEqual([s.title for s in newest_first], ["Baru", "Lama"])

        with self.assertRaises(ValueError):
            sort_songs(self.songs, "genre", "asc")

    def test_search_and_filter_songs(self) -> None:
        original = list(self.songs)

        by_title = search_songs(self.songs, "bInTaNg")
        by_artist = search_songs(self.songs, "raisa")
        self.assertEqual([s.title for s in by_title], ["Bintang"])
        self.assertEqual([s.title for s in by_artist], ["Cinta"])

        with_lrc = filter_songs(self.songs, {"has_lyrics": True})
        without_lrc = filter_songs(self.songs, {"has_lyrics": False})
        by_filter_artist = filter_songs(self.songs, {"has_lyrics": True, "artist": "ANDMESH"})

        self.assertEqual([s.title for s in with_lrc], ["Cinta", "Bintang"])
        self.assertEqual([s.title for s in without_lrc], ["Angin"])
        self.assertEqual([s.title for s in by_filter_artist], ["Bintang"])
        self.assertEqual(self.songs, original)


class PlaylistTest(unittest.TestCase):
    """Test basic in-memory playlist operations (FR-15)."""

    def test_playlist_crud_and_errors(self) -> None:
        manager = PlaylistManager()
        song_a = Song(Path("a.mp3"), None, "A", "Artis", 100.0)
        song_b = Song(Path("b.mp3"), None, "B", "Artis", 120.0)

        manager.create("Favorit")
        self.assertEqual(manager.list_names(), ["Favorit"])

        manager.add_song("Favorit", song_a)
        manager.add_song("Favorit", song_b)
        songs = manager.get_songs("Favorit")
        self.assertEqual(songs, [song_a, song_b])
        songs.clear()
        self.assertEqual(len(manager.get_songs("Favorit")), 2)

        removed = manager.remove_song("Favorit", 0)
        self.assertEqual(removed, song_a)
        self.assertEqual(manager.get_songs("Favorit"), [song_b])

        with self.assertRaises(ValueError):
            manager.create("Favorit")
        with self.assertRaises(KeyError):
            manager.get_songs("Kosong")
        with self.assertRaises(IndexError):
            manager.remove_song("Favorit", 5)


class UiTest(unittest.TestCase):
    """Test lyric rendering from Queue (TC-08), menu parser, and TerminalUI commands."""

    def test_lyric_display_skips_duplicate_renders(self) -> None:
        controller = CoreController(audio_player=MagicMock())
        controller.event_queue.put(LyricEvent(text="Baris pertama", timestamp=1.0, index=0))
        controller.event_queue.put(LyricEvent(text="Baris pertama", timestamp=1.0, index=0))
        controller.event_queue.put(LyricEvent(text="Baris kedua", timestamp=4.0, index=1))

        ui = TerminalUI()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rendered = ui.poll_lyrics(controller)
            render_lyric("Teks manual")
            render_lyric(None)

        output = buf.getvalue()
        self.assertTrue(rendered)
        self.assertEqual(output.count("Baris pertama"), 1)
        self.assertEqual(output.count("Baris kedua"), 1)
        self.assertIn("[Lirik] Teks manual", output)

        display = LyricDisplay()
        with redirect_stdout(io.StringIO()):
            self.assertTrue(display.update("Satu"))
            self.assertFalse(display.update("Satu"))

    def test_parse_command_variants(self) -> None:
        self.assertEqual(parse_command(""), ("empty", []))
        self.assertEqual(parse_command("2"), ("play_index", ["2"]))
        self.assertEqual(parse_command("p"), ("pause", []))
        self.assertEqual(parse_command("resume"), ("resume", []))
        self.assertEqual(parse_command("sort artist desc"), ("sort", ["artist", "desc"]))
        self.assertEqual(parse_command("search cinta"), ("search", ["cinta"]))
        self.assertEqual(parse_command("filter lrc ya"), ("filter", ["lrc", "ya"]))
        self.assertEqual(parse_command("playlist new santai"), ("playlist", ["new", "santai"]))
        self.assertEqual(parse_command("q"), ("quit", []))
        self.assertEqual(parse_command("²"), ("unknown", ["²"]))
        self.assertEqual(parse_command("xyz"), ("unknown", ["xyz"]))

    def test_terminal_ui_interactive_flow_and_error_handling(self) -> None:
        songs = [
            Song(Path("satu.mp3"), Path("satu.lrc"), "Satu", "Artis A", 120.0),
            Song(Path("dua.mp3"), None, "Dua", "Artis B", 150.0),
        ]
        controller = MagicMock()
        controller.poll_events.return_value = []

        commands: Queue[str | None] = Queue()
        for cmd in [
            "help",
            "1",
            "p",
            "r",
            "n",
            "b",
            "sort title desc",
            "search satu",
            "search tidak_ketemu",
            "filter lrc ya",
            "filter artist Artis B",
            "list",
            "playlist list",
            "playlist new favorit",
            "playlist add favorit 1",
            "playlist show favorit",
            "playlist play favorit",
            "playlist remove favorit 1",
            "playlist list",
            "99",
            "perintah_ngawur",
            "s",
            "q",
        ]:
            commands.put(cmd)

        ui = TerminalUI()
        buf = io.StringIO()
        with redirect_stdout(buf):
            ui.run(controller, songs, input_queue=commands)

        output = buf.getvalue()
        self.assertIn("Memutar [1/2]: Satu", output)
        self.assertIn("Dijeda: Satu", output)
        self.assertIn("Dilanjutkan: Satu", output)
        self.assertIn("Tidak ada lagu yang cocok", output)
        self.assertIn("Nomor lagu tidak valid", output)
        self.assertIn("Perintah 'perintah_ngawur' tidak dikenal", output)
        self.assertIn("Menutup pemutar musik", output)
        controller.stop.assert_called()

        failing_controller = MagicMock()
        failing_controller.poll_events.return_value = []
        failing_controller.load_track.side_effect = FileNotFoundError("file hilang")
        fail_cmds: Queue[str | None] = Queue()
        fail_cmds.put("1")
        fail_cmds.put("q")
        err_buf = io.StringIO()
        with redirect_stdout(err_buf):
            TerminalUI().run(failing_controller, songs, input_queue=fail_cmds)
        self.assertIn("Gagal memutar 'Satu': file hilang", err_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
