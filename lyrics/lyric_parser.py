"""Data structures and parser for LRC lyric files."""

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class LyricLine:
    """Represents a single timed line of lyric."""

    timestamp: float  # Timestamp in seconds
    text: str


# Regex matching [mm:ss.xx] or [mm:ss.xxx]
_TIMESTAMP_REGEX = re.compile(r"\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]")


def parse_timestamp(minutes_str: str, seconds_str: str, fraction_str: str | None) -> float:
    """Convert minutes, seconds, and fractional seconds into total seconds (float)."""
    minutes = int(minutes_str)
    seconds = int(seconds_str)
    fraction = 0.0
    if fraction_str:
        fraction = float(f"0.{fraction_str}")
    return minutes * 60 + seconds + fraction


def parse_lrc(path: Path | str) -> list[LyricLine]:
    """Parse an LRC file into an ordered list of LyricLine objects.

    Handles single and multi-timestamp lines (e.g. [00:10.00][00:20.00]Chorus).
    Ignores metadata tags like [ar:Artist], [ti:Title], or malformed lines.
    Returns entries strictly sorted by timestamp.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"File lirik tidak ditemukan: {file_path}")

    lines: list[LyricLine] = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="latin-1")

    for raw_line in content.splitlines():
        trimmed = raw_line.strip()
        if not trimmed:
            continue

        timestamps_matches = list(_TIMESTAMP_REGEX.finditer(trimmed))
        if not timestamps_matches:
            # Metadata tag (e.g., [ar: Singer]) or plain text without timestamp
            continue

        # Extract text following the last timestamp
        last_match = timestamps_matches[-1]
        text_content = trimmed[last_match.end() :].strip()

        # Parse each timestamp in the line (supports multi-timestamp lines)
        for match in timestamps_matches:
            minutes_s, seconds_s, fraction_s = match.groups()
            ts = parse_timestamp(minutes_s, seconds_s, fraction_s)
            lines.append(LyricLine(timestamp=ts, text=text_content))

    # Sort lyrics chronologically by timestamp
    lines.sort(key=lambda item: item.timestamp)
    return lines
