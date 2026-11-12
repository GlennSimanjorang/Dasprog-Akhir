"""Entry point aplikasi Terminal Music & Lyric Player."""

from pathlib import Path

from audio.audio_player import AudioPlayer


PROJECT_ROOT = Path(__file__).parent
MUSIC_DIRECTORY = PROJECT_ROOT / "data" / "music"


def main() -> None:
    """Play the first MP3 and handle basic playback controls."""
    tracks = sorted(MUSIC_DIRECTORY.glob("*.mp3"))
    if not tracks:
        print(f"Belum ada file MP3 di {MUSIC_DIRECTORY}.")
        print("Tambahkan satu file MP3, lalu jalankan kembali aplikasi.")
        return

    player = AudioPlayer()
    try:
        player.initialize()
        player.set_playlist(tracks)
        player.load(tracks[0])
        player.play()
        print(f"Memutar: {tracks[0].name}")
        print("Perintah: [p]ause, [r]esume, [n]ext, [b]ack, [s]top, [q]uit")
        while True:
            command = input("> ").strip().lower()
            if command == "p":
                player.pause()
                print("Playback dijeda.")
            elif command == "r":
                player.resume()
                print("Playback dilanjutkan.")
            elif command in {"n", "b"}:
                track = player.next() if command == "n" else player.previous()
                print(f"Memutar: {track.name}")
            elif command in {"s", "q"}:
                player.stop()
                print("Playback dihentikan.")
                break
            else:
                print("Perintah tidak dikenal. Gunakan p, r, n, b, s, atau q.")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Gagal menjalankan audio: {error}")
    finally:
        player.stop()
        player.cleanup()


if __name__ == "__main__":
    main()
