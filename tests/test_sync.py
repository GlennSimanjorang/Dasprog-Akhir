"""Unit tests for lyric synchronization worker and active lyric index determination."""

from queue import Queue
import threading
import time
import unittest

from lyrics.lyric_parser import LyricLine
from lyrics.lyric_sync import LyricEvent, LyricSyncWorker, find_active_lyric_index


class LyricSyncTest(unittest.TestCase):
    """Test sync algorithm and background worker thread."""

    def setUp(self) -> None:
        self.sample_lyrics = [
            LyricLine(timestamp=2.0, text="Intro ends, line 1"),
            LyricLine(timestamp=5.0, text="Line 2 sings here"),
            LyricLine(timestamp=9.0, text="Line 3 finale"),
        ]

    def test_find_active_lyric_index(self) -> None:
        # Before any lyrics
        self.assertIsNone(find_active_lyric_index(self.sample_lyrics, 0.5))
        self.assertIsNone(find_active_lyric_index(self.sample_lyrics, 1.99))

        # At exactly first timestamp
        self.assertEqual(find_active_lyric_index(self.sample_lyrics, 2.0), 0)

        # In between timestamps
        self.assertEqual(find_active_lyric_index(self.sample_lyrics, 3.5), 0)
        self.assertEqual(find_active_lyric_index(self.sample_lyrics, 5.0), 1)
        self.assertEqual(find_active_lyric_index(self.sample_lyrics, 7.0), 1)

        # After last timestamp
        self.assertEqual(find_active_lyric_index(self.sample_lyrics, 9.0), 2)
        self.assertEqual(find_active_lyric_index(self.sample_lyrics, 99.0), 2)

    def test_find_active_lyric_empty(self) -> None:
        self.assertIsNone(find_active_lyric_index([], 10.0))

    def test_worker_emits_event_only_on_change(self) -> None:
        queue: Queue[LyricEvent] = Queue()
        stop_event = threading.Event()
        current_pos = 0.0

        def get_pos() -> float:
            return current_pos

        worker = LyricSyncWorker(
            get_position=get_pos,
            lyrics=self.sample_lyrics,
            event_queue=queue,
            stop_event=stop_event,
            poll_interval=0.01,
        )

        worker.start()

        try:
            # At pos 0.0 -> initial event (empty text/intro)
            time.sleep(0.04)
            self.assertFalse(queue.empty())
            initial_event = queue.get_nowait()
            self.assertIsNone(initial_event.index)

            # Move to 2.5s (line 0)
            current_pos = 2.5
            time.sleep(0.04)
            self.assertFalse(queue.empty())
            event1 = queue.get_nowait()
            self.assertEqual(event1.index, 0)
            self.assertEqual(event1.text, "Intro ends, line 1")

            # Still in line 0 -> should NOT emit new events (FR-10)
            current_pos = 3.0
            time.sleep(0.03)
            self.assertTrue(queue.empty())

            # Move to 6.0s (line 1)
            current_pos = 6.0
            time.sleep(0.04)
            self.assertFalse(queue.empty())
            event2 = queue.get_nowait()
            self.assertEqual(event2.index, 1)
            self.assertEqual(event2.text, "Line 2 sings here")

        finally:
            worker.stop()

    def test_worker_stop_event(self) -> None:
        queue: Queue[LyricEvent] = Queue()
        stop_event = threading.Event()

        worker = LyricSyncWorker(
            get_position=lambda: 1.0,
            lyrics=self.sample_lyrics,
            event_queue=queue,
            stop_event=stop_event,
            poll_interval=0.02,
        )

        thread = worker.start()
        self.assertTrue(thread.is_alive())

        worker.stop()
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main()
