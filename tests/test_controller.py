"""Unit tests for CoreController lifecycle and queue integration."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock

from core.controller import CoreController
from lyrics.lyric_parser import LyricLine


class CoreControllerTest(unittest.TestCase):
    """Test CoreController interaction between audio, lyrics, and worker."""

    def test_load_track_with_lyrics(self) -> None:
        mock_player = MagicMock()
        controller = CoreController(audio_player=mock_player)

        sample_lrc = "[00:01.00]First\n[00:05.00]Second\n"
        with TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "test.mp3"
            lrc_path = Path(temp_dir) / "test.lrc"
            audio_path.touch()
            lrc_path.write_text(sample_lrc, encoding="utf-8")

            controller.load_track(audio_path, lrc_path)
            self.assertEqual(len(controller._current_lyrics), 2)
            mock_player.load.assert_called_once_with(audio_path)

    def test_load_track_without_lyrics_graceful(self) -> None:
        mock_player = MagicMock()
        controller = CoreController(audio_player=mock_player)

        with TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "test.mp3"
            audio_path.touch()

            # Lyric path is None or non-existent
            controller.load_track(audio_path, None)
            self.assertEqual(len(controller._current_lyrics), 0)

            controller.play()
            mock_player.play.assert_called_once()
            # Worker shouldn't start when no lyrics
            self.assertIsNone(controller._sync_worker)

    def test_poll_events_drains_queue(self) -> None:
        controller = CoreController(audio_player=MagicMock())
        self.assertEqual(controller.poll_events(), [])

        from lyrics.lyric_sync import LyricEvent
        controller.event_queue.put(LyricEvent(text="Line 1", timestamp=1.0, index=0))
        controller.event_queue.put(LyricEvent(text="Line 2", timestamp=2.0, index=1))

        events = controller.poll_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].text, "Line 1")
        self.assertEqual(events[1].text, "Line 2")
        self.assertEqual(controller.active_lyric.text, "Line 2")
        self.assertTrue(controller.event_queue.empty())

    def test_shutdown_cleans_up(self) -> None:
        mock_player = MagicMock()
        controller = CoreController(audio_player=mock_player)
        controller.shutdown()
        mock_player.cleanup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
