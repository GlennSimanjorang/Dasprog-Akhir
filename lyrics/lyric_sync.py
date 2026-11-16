"""Synchronization worker for aligning audio playback with lyrics via thread-safe Queue."""

from dataclasses import dataclass
from queue import Queue
import threading
import time
from typing import Callable

from lyrics.lyric_parser import LyricLine


@dataclass(frozen=True)
class LyricEvent:
    """Event sent through Queue to communicate lyric updates to Main Thread."""

    text: str
    timestamp: float | None
    index: int | None
    is_end: bool = False


def find_active_lyric_index(lyrics: list[LyricLine], position_seconds: float) -> int | None:
    """Find the index of the active lyric line for the given playback position.

    According to business rules: The active line is the latest timestamp <= current position.
    Returns None if position is before the first timestamp or lyrics are empty.
    """
    if not lyrics:
        return None

    # Binary search or backward traversal since lyrics are sorted
    active_idx: int | None = None
    for idx, line in enumerate(lyrics):
        if line.timestamp <= position_seconds:
            active_idx = idx
        else:
            break

    return active_idx


class LyricSyncWorker:
    """Background worker thread that polls audio playback position and emits LyricEvent on changes."""

    def __init__(
        self,
        get_position: Callable[[], float | None],
        lyrics: list[LyricLine],
        event_queue: Queue,
        stop_event: threading.Event,
        poll_interval: float = 0.08,
    ) -> None:
        self._get_position = get_position
        self._lyrics = lyrics
        self._queue = event_queue
        self._stop_event = stop_event
        self._poll_interval = poll_interval
        self._thread: threading.Thread | None = None
        self._last_index: int | None = -1  # Sentinel to track change

    def start(self) -> threading.Thread:
        """Start the background synchronization thread."""
        self._thread = threading.Thread(
            target=self._run_loop,
            name="LyricSyncWorkerThread",
            daemon=True,
        )
        self._thread.start()
        return self._thread

    def _run_loop(self) -> None:
        """Worker loop checking audio position until stop_event is set."""
        while not self._stop_event.is_set():
            position = self._get_position()
            if position is not None:
                current_idx = find_active_lyric_index(self._lyrics, position)
                # Only emit event when the active lyric actually changes (FR-10)
                if current_idx != self._last_index:
                    self._last_index = current_idx
                    if current_idx is not None:
                        active_line = self._lyrics[current_idx]
                        self._queue.put(
                            LyricEvent(
                                text=active_line.text,
                                timestamp=active_line.timestamp,
                                index=current_idx,
                                is_end=False,
                            )
                        )
                    else:
                        # Position is before any lyrics start (intro)
                        self._queue.put(
                            LyricEvent(
                                text="",
                                timestamp=None,
                                index=None,
                                is_end=False,
                            )
                        )

            # Wait poll_interval or wake immediately if stop_event is signaled
            if self._stop_event.wait(self._poll_interval):
                break

    def stop(self, timeout: float = 1.0) -> None:
        """Signal the worker to stop and wait for completion."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            if threading.current_thread() != self._thread:
                self._thread.join(timeout=timeout)
