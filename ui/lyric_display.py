"""Terminal rendering functions for playlists and synchronized active lyrics."""

import sys

from library.listing import format_duration, format_song_list
from library.song import Song
from lyrics.lyric_parser import LyricLine
from lyrics.lyric_sync import LyricEvent


def format_lyric_line(
    lyric: LyricEvent | LyricLine | str | None,
    timestamp: float | None = None,
) -> str:
    """Format an active lyric entry or string into a terminal display line."""
    if lyric is None:
        return ""

    if isinstance(lyric, LyricEvent):
        text = lyric.text.strip()
        ts = lyric.timestamp if timestamp is None else timestamp
    elif isinstance(lyric, LyricLine):
        text = lyric.text.strip()
        ts = lyric.timestamp if timestamp is None else timestamp
    else:
        text = str(lyric).strip()
        ts = timestamp

    if not text:
        return ""

    if ts is not None and ts >= 0:
        pos_text = f"[{format_duration(ts)}]"
        return f"♪ {pos_text} {text}"

    return f"♪ {text}"


def render_playlist(songs: list[Song]) -> str:
    """Render the list of songs to the terminal (Main Thread only, FR-03)."""
    table_text = format_song_list(songs)
    print(table_text)
    return table_text


def render_lyric(
    lyric: LyricEvent | LyricLine | str | None,
    timestamp: float | None = None,
) -> str | None:
    """Render the active lyric entry to the terminal (Main Thread only, FR-11)."""
    formatted = format_lyric_line(lyric, timestamp=timestamp)
    if not formatted:
        return None

    print(f"\r{formatted}   ")
    sys.stdout.flush()
    return formatted


class LyricDisplay:
    """Stateful lyric renderer that prevents redundant re-renders (NFR-01)."""

    def __init__(self) -> None:
        self._last_rendered: str | None = None

    @property
    def last_rendered(self) -> str | None:
        """Return the last rendered lyric line string."""
        return self._last_rendered

    def reset(self) -> None:
        """Reset cached lyric state (e.g. when changing or stopping tracks)."""
        self._last_rendered = None

    def update(self, lyric: LyricEvent | LyricLine | str | None) -> str | None:
        """Render the lyric only when the formatted output has changed."""
        formatted = format_lyric_line(lyric)
        if not formatted or formatted == self._last_rendered:
            return None

        self._last_rendered = formatted
        print(f"\r{formatted}   ")
        sys.stdout.flush()
        return formatted
