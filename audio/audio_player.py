"""Audio playback wrapper around pygame.mixer.music."""

from pathlib import Path
from types import ModuleType
from typing import Any

try:
    import pygame
except ImportError:
    # Fallback placeholder so unit tests can patch `pygame.mixer` even when pygame is uninstalled
    class _PygameFallback(ModuleType):
        mixer: Any = None
        error = Exception

    pygame = _PygameFallback("pygame")


class AudioPlayer:
    """Control playback of one local audio file at a time."""

    def __init__(self) -> None:
        self._initialized = False
        self._loaded_path: Path | None = None
        self._playlist: list[Path] = []
        self._current_index: int | None = None

    def initialize(self) -> None:
        """Initialize pygame's audio mixer."""
        if not self._initialized:
            if pygame is None:
                raise RuntimeError("Modul pygame tidak terinstall. Jalankan 'pip install -r requirements.txt'")
            pygame.mixer.init()
            self._initialized = True

    def load(self, path: Path | str) -> None:
        """Load an MP3 file for playback."""
        if not self._initialized:
            raise RuntimeError("Audio mixer belum diinisialisasi.")

        audio_path = Path(path)
        if not audio_path.is_file():
            raise FileNotFoundError(f"File audio tidak ditemukan: {audio_path}")

        try:
            pygame.mixer.music.load(str(audio_path))
        except pygame.error as error:
            raise ValueError(f"File audio tidak valid: {audio_path}") from error

        self._loaded_path = audio_path
        if audio_path in self._playlist:
            self._current_index = self._playlist.index(audio_path)

    def set_playlist(self, tracks: list[Path | str]) -> None:
        """Set the tracks used by next and previous."""
        self._playlist = [Path(track) for track in tracks]
        self._current_index = None
        if self._loaded_path in self._playlist:
            self._current_index = self._playlist.index(self._loaded_path)

    def next(self) -> Path:
        """Load and play the next track, wrapping at the playlist end."""
        return self._change_track(1)

    def previous(self) -> Path:
        """Load and play the previous track, wrapping at the playlist start."""
        return self._change_track(-1)

    def play(self) -> None:
        """Start the loaded track."""
        self._require_loaded_track()
        pygame.mixer.music.play()

    def pause(self) -> None:
        """Pause the current track."""
        self._require_loaded_track()
        pygame.mixer.music.pause()

    def resume(self) -> None:
        """Resume the paused track."""
        self._require_loaded_track()
        pygame.mixer.music.unpause()

    def stop(self) -> None:
        """Stop the current track."""
        if self._initialized:
            pygame.mixer.music.stop()

    def get_position(self) -> float | None:
        """Return playback position in seconds, when a track is active."""
        if not self._initialized or self._loaded_path is None:
            return None

        position_ms = pygame.mixer.music.get_pos()
        if position_ms < 0:
            return None
        return position_ms / 1000

    def cleanup(self) -> None:
        """Stop playback and release the mixer."""
        if self._initialized:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            self._initialized = False
            self._loaded_path = None
            self._playlist = []
            self._current_index = None

    def _change_track(self, step: int) -> Path:
        if not self._playlist:
            raise RuntimeError("Playlist belum diatur.")
        if self._current_index is None:
            self._current_index = 0
        else:
            self._current_index = (self._current_index + step) % len(self._playlist)

        track = self._playlist[self._current_index]
        self.load(track)
        self.play()
        return track

    def _require_loaded_track(self) -> None:
        if not self._initialized:
            raise RuntimeError("Audio mixer belum diinisialisasi.")
        if self._loaded_path is None:
            raise RuntimeError("Belum ada file audio yang dimuat.")