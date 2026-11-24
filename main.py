"""Entry point aplikasi Terminal Music & Lyric Player."""

from pathlib import Path

from core.controller import CoreController
from library.scanner import scan_directory
from library.song import Song
from ui.terminal_ui import TerminalUI


PROJECT_ROOT = Path(__file__).parent
MUSIC_DIRECTORY = PROJECT_ROOT / "data" / "music"
LYRICS_DIRECTORY = PROJECT_ROOT / "data" / "lyrics"


def scan_local_tracks() -> list[Song]:
    """Scan local music and lyrics directories using Anggota 3 scanner."""
    return scan_directory(MUSIC_DIRECTORY, lyrics_dir=LYRICS_DIRECTORY)


def main() -> None:
    """Run interactive CLI music and synchronized lyric player."""
    songs = scan_local_tracks()
    if not songs:
        print(f"Belum ada file MP3 di {MUSIC_DIRECTORY}.")
        print("Tambahkan minimal 1 file MP3 (misal: data/music/contoh.mp3), lalu jalankan kembali.")
        return

    controller = CoreController()
    try:
        controller.initialize()
        TerminalUI().run(controller, songs)
    except KeyboardInterrupt:
        print("\nMenghentikan pemutaran...")
    finally:
        controller.shutdown()
        print("Aplikasi selesai dijalankan.")


if __name__ == "__main__":
    main()
