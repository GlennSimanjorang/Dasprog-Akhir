"""Tests for the audio playback wrapper."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from audio.audio_player import AudioPlayer


class AudioPlayerTest(unittest.TestCase):
    """Verify AudioPlayer behavior without requiring a real audio device."""

    @patch("audio.audio_player.pygame.mixer")
    def test_initialize_and_cleanup(self, mixer) -> None:
        player = AudioPlayer()

        player.initialize()
        player.cleanup()

        mixer.init.assert_called_once_with()
        mixer.music.stop.assert_called_once_with()
        mixer.quit.assert_called_once_with()

    @patch("audio.audio_player.pygame.mixer")
    def test_load_and_play(self, mixer) -> None:
        player = AudioPlayer()

        with TemporaryDirectory() as temporary_directory:
            audio_path = Path(temporary_directory) / "song.mp3"
            audio_path.touch()

            player.initialize()
            player.load(audio_path)
            player.play()

        mixer.music.load.assert_called_once_with(str(audio_path))
        mixer.music.play.assert_called_once_with()

    @patch("audio.audio_player.pygame.mixer")
    def test_pause_resume_and_stop(self, mixer) -> None:
        player = AudioPlayer()

        with TemporaryDirectory() as temporary_directory:
            audio_path = Path(temporary_directory) / "song.mp3"
            audio_path.touch()

            player.initialize()
            player.load(audio_path)
            player.pause()
            player.resume()
            player.stop()

        mixer.music.pause.assert_called_once_with()
        mixer.music.unpause.assert_called_once_with()
        mixer.music.stop.assert_called_once_with()

    @patch("audio.audio_player.pygame.mixer")
    def test_get_position_returns_seconds(self, mixer) -> None:
        mixer.music.get_pos.return_value = 1250
        player = AudioPlayer()

        with TemporaryDirectory() as temporary_directory:
            audio_path = Path(temporary_directory) / "song.mp3"
            audio_path.touch()

            player.initialize()
            player.load(audio_path)

            self.assertEqual(player.get_position(), 1.25)

    @patch("audio.audio_player.pygame.mixer")
    def test_load_requires_existing_file(self, mixer) -> None:
        player = AudioPlayer()
        player.initialize()

        with self.assertRaises(FileNotFoundError):
            player.load(Path("missing-song.mp3"))

    @patch("audio.audio_player.pygame.mixer")
    def test_next_and_previous_change_track(self, mixer) -> None:
        player = AudioPlayer()

        with TemporaryDirectory() as temporary_directory:
            first = Path(temporary_directory) / "first.mp3"
            second = Path(temporary_directory) / "second.mp3"
            first.touch()
            second.touch()

            player.initialize()
            player.set_playlist([first, second])
            player.load(first)
            player.play()

            self.assertEqual(player.next(), second)
            self.assertEqual(player.previous(), first)

        self.assertEqual(
            mixer.music.load.call_args_list[-1].args,
            (str(first),),
        )
        self.assertEqual(mixer.music.play.call_count, 3)


if __name__ == "__main__":
    unittest.main()
