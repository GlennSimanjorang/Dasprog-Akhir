"""Entry point aplikasi Terminal Music & Lyric Player."""

from pathlib import Path
import select
import sys
import time

from core.controller import CoreController
from library.song import Song


PROJECT_ROOT = Path(__file__).parent
MUSIC_DIRECTORY = PROJECT_ROOT / "data" / "music"
LYRICS_DIRECTORY = PROJECT_ROOT / "data" / "lyrics"


def scan_local_tracks() -> list[Song]:
    """Simple track discovery scanning local directories (Developer 1 & 3 integration)."""
    songs: list[Song] = []
    if not MUSIC_DIRECTORY.exists():
        return songs

    for audio_file in sorted(MUSIC_DIRECTORY.glob("*.mp3")):
        # Look for matching .lrc file in lyrics directory or same directory
        matching_lrc = LYRICS_DIRECTORY / f"{audio_file.stem}.lrc"
        if not matching_lrc.is_file():
            same_dir_lrc = audio_file.with_suffix(".lrc")
            matching_lrc = same_dir_lrc if same_dir_lrc.is_file() else None
        else:
            matching_lrc = matching_lrc

        song = Song(
            audio_path=audio_file,
            lyric_path=matching_lrc,
            title=audio_file.stem.replace("_", " ").title(),
            artist="Unknown Artist",
            duration=None,
        )
        songs.append(song)
    return songs


def check_input_non_blocking() -> str | None:
    """Read a single line from stdin if available (non-blocking for Unix)."""
    if select.select([sys.stdin], [], [], 0)[0]:
        line = sys.stdin.readline()
        return line.strip().lower()
    return None


def main() -> None:
    """Run interactive playback loop with real-time synchronized lyric display."""
    songs = scan_local_tracks()
    if not songs:
        print(f"Belum ada file MP3 di {MUSIC_DIRECTORY}.")
        print("Tambahkan minimal 1 file MP3 (misal: data/music/contoh.mp3), lalu jalankan kembali.")
        return

    controller = CoreController()
    try:
        controller.initialize()
        controller.set_playlist([s.audio_path for s in songs])

        current_index = 0
        current_song = songs[current_index]

        controller.load_track(current_song.audio_path, current_song.lyric_path)
        controller.play()

        print("=" * 60)
        print("  TERMINAL MUSIC & LYRIC PLAYER (CLI)")
        print("=" * 60)
        print(f"Now Playing: {current_song.title}")
        print(f"Lirik: {'Tersedia (' + current_song.lyric_path.name + ')' if current_song.has_lyrics else 'Tidak tersedia'}")
        print("-" * 60)
        print("Perintah: [p]ause | [r]esume | [n]ext | [b]ack | [s]top | [q]uit")
        print("=" * 60)

        displayed_lyric = ""
        is_running = True

        while is_running:
            # 1. Main thread polls events from Queue (FR-10, FR-11)
            events = controller.poll_events()
            for ev in events:
                if ev.text != displayed_lyric:
                    displayed_lyric = ev.text
                    pos_text = f"[{int(ev.timestamp // 60):02d}:{int(ev.timestamp % 60):02d}]" if ev.timestamp is not None else "[--:--]"
                    if displayed_lyric:
                        print(f"\r♪ {pos_text} {displayed_lyric}   ")
                        sys.stdout.flush()

            # 2. Check for user keyboard commands (non-blocking)
            cmd = check_input_non_blocking()
            if cmd:
                if cmd == "p":
                    controller.pause()
                    print("\n[PAUSED]")
                elif cmd == "r":
                    controller.resume()
                    print("\n[RESUMED]")
                elif cmd in {"n", "b"}:
                    current_index = (current_index + 1) % len(songs) if cmd == "n" else (current_index - 1) % len(songs)
                    current_song = songs[current_index]
                    print(f"\n[SWITCH TRACK] Memutar: {current_song.title}")
                    controller.load_track(current_song.audio_path, current_song.lyric_path)
                    controller.play()
                    displayed_lyric = ""
                elif cmd in {"s", "q"}:
                    print("\n[STOPPING] Menutup aplikasi dan membersihkan thread...")
                    is_running = False
                else:
                    print(f"\nPerintah '{cmd}' tidak dikenal. Gunakan: p, r, n, b, s, q")

            time.sleep(0.08)

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Menghentikan pemutaran...")
    finally:
        controller.shutdown()
        print("Aplikasi selesai dijalankan.")


if __name__ == "__main__":
    main()
