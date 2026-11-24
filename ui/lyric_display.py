"""Main-thread terminal rendering helpers for song lists and active lyrics."""

from library.listing import format_duration, format_song_list
from library.song import Song
from lyrics.lyric_sync import LyricEvent


def _extract_lyric(lyric: LyricEvent | str | None) -> tuple[str, float | None]:
    if lyric is None:
        return "", None
    if isinstance(lyric, str):
        return lyric.strip(), None
    return (lyric.text or "").strip(), lyric.timestamp


def render_playlist(songs: list[Song]) -> None:
    """Print the formatted song list to the terminal (Main Thread only)."""
    print(format_song_list(songs))


def render_lyric(lyric: LyricEvent | str | None) -> None:
    """Print the active lyric line to the terminal (Main Thread only)."""
    text, timestamp = _extract_lyric(lyric)
    if not text:
        return
    prefix = f"[Lirik {format_duration(timestamp)}]" if timestamp is not None else "[Lirik]"
    print(f"{prefix} {text}", flush=True)


class LyricDisplay:
    """Track the last displayed lyric text to skip duplicate re-renders (NFR-01)."""

    def __init__(self) -> None:
        self._last_text: str | None = None

    def reset(self) -> None:
        """Clear cached lyric state when changing or stopping tracks."""
        self._last_text = None

    def update(self, lyric: LyricEvent | str | None) -> bool:
        """Render lyric only when active text changed; return True if printed."""
        text, _ = _extract_lyric(lyric)
        if text == self._last_text:
            return False
        self._last_text = text
        if not text:
            return False
        render_lyric(lyric)
        return True
