"""Core controller coordinating Audio, LyricSync, Queue, and Main Thread."""

from pathlib import Path
from queue import Empty, Queue
import threading
from typing import Callable

from audio.audio_player import AudioPlayer
from lyrics.lyric_parser import LyricLine, parse_lrc
from lyrics.lyric_sync import LyricEvent, LyricSyncWorker


class CoreController:
    """Manages playback lifecycle, background lyric sync worker, and thread-safe queue."""

    def __init__(self, audio_player: AudioPlayer | None = None) -> None:
        self.player = audio_player or AudioPlayer()
        self.event_queue: Queue[LyricEvent] = Queue()
        self._sync_worker: LyricSyncWorker | None = None
        self._stop_event = threading.Event()
        self._current_lyrics: list[LyricLine] = []
        self._on_lyric_change: Callable[[LyricEvent], None] | None = None
        self._active_lyric: LyricEvent | None = None

    def initialize(self) -> None:
        """Initialize underlying audio subsystem."""
        self.player.initialize()

    def set_playlist(self, tracks: list[Path | str]) -> None:
        """Set playlist on player."""
        self.player.set_playlist(tracks)

    def load_track(self, audio_path: Path | str, lyric_path: Path | str | None = None) -> None:
        """Load track and prepare lyrics parser/sync worker."""
        # Stop any existing worker before switching tracks (business rule 4)
        self.stop_sync_worker()

        # Load audio in player
        self.player.load(audio_path)

        # Parse lyrics if file provided and exists (FR-16: graceful handling)
        self._current_lyrics = []
        self._active_lyric = None
        if lyric_path is not None:
            lrc_file = Path(lyric_path)
            if lrc_file.is_file():
                try:
                    self._current_lyrics = parse_lrc(lrc_file)
                except Exception:
                    self._current_lyrics = []

    def play(self) -> None:
        """Start playback and launch lyric sync worker if lyrics are available."""
        self.player.play()
        self._start_sync_worker()

    def pause(self) -> None:
        """Pause playback."""
        self.player.pause()

    def resume(self) -> None:
        """Resume playback."""
        self.player.resume()

    def stop(self) -> None:
        """Stop playback and stop sync worker."""
        self.stop_sync_worker()
        self.player.stop()

    def next_track(self, lyric_path: Path | str | None = None) -> Path:
        """Switch to next track and restart worker."""
        self.stop_sync_worker()
        next_path = self.player.next()
        self.load_track(next_path, lyric_path)
        self.play()
        return next_path

    def previous_track(self, lyric_path: Path | str | None = None) -> Path:
        """Switch to previous track and restart worker."""
        self.stop_sync_worker()
        prev_path = self.player.previous()
        self.load_track(prev_path, lyric_path)
        self.play()
        return prev_path

    def _start_sync_worker(self) -> None:
        """Start background LyricSyncWorker thread."""
        self.stop_sync_worker()
        if not self._current_lyrics:
            return

        self._stop_event = threading.Event()
        self._sync_worker = LyricSyncWorker(
            get_position=self.player.get_position,
            lyrics=self._current_lyrics,
            event_queue=self.event_queue,
            stop_event=self._stop_event,
        )
        self._sync_worker.start()

    def stop_sync_worker(self) -> None:
        """Safely stop and join existing sync worker thread (FR-17)."""
        if self._sync_worker is not None:
            self._sync_worker.stop()
            self._sync_worker = None

    def poll_events(self) -> list[LyricEvent]:
        """Drain events from Queue in Main Thread (non-blocking)."""
        events: list[LyricEvent] = []
        while True:
            try:
                ev = self.event_queue.get_nowait()
                self._active_lyric = ev
                events.append(ev)
            except Empty:
                break
        return events

    @property
    def active_lyric(self) -> LyricEvent | None:
        """Return the most recently received active lyric event."""
        return self._active_lyric

    def get_position(self) -> float | None:
        """Get current playback position in seconds."""
        return self.player.get_position()

    def shutdown(self) -> None:
        """Clean shutdown of audio, threads, and resources (FR-18)."""
        self.stop_sync_worker()
        self.player.cleanup()
        # Drain queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except Empty:
                break
