"""Sorting utilities for song collections (FR-12).

Implements pure sorting functions that return a new sorted list without
modifying the original source list (Business Rule 3).
"""

from datetime import datetime
from typing import Any

from library.song import Song

_VALID_SORT_FIELDS = {
    "title": "title",
    "judul": "title",
    "artist": "artist",
    "artis": "artist",
    "duration": "duration",
    "durasi": "duration",
    "date": "date",
    "date_added": "date",
    "added_at": "date",
    "tanggal": "date",
}

_VALID_ORDERS = {
    "asc": False,
    "ascending": False,
    "desc": True,
    "descending": True,
}


def _get_song_date_value(song: Song) -> float | None:
    """Extract comparable timestamp for a song if date metadata or file stat is available."""
    for attr_name in ("added_at", "date_added"):
        value = getattr(song, attr_name, None)
        if isinstance(value, datetime):
            return value.timestamp()
        if isinstance(value, (int, float)):
            return float(value)

    try:
        if song.audio_path.exists():
            return song.audio_path.stat().st_mtime
    except OSError:
        return None
    return None


def _extract_sort_value(song: Song, field: str) -> Any:
    """Return the comparable sort value for a song field, or None when unavailable."""
    if field == "title":
        return song.title.lower()

    if field == "artist":
        if song.artist is None or not song.artist.strip():
            return None
        return song.artist.strip().lower()

    if field == "duration":
        if song.duration is None:
            return None
        return float(song.duration)

    if field == "date":
        return _get_song_date_value(song)

    return None


def sort_songs(
    songs: list[Song],
    sort_by: str = "title",
    order: str = "asc",
) -> list[Song]:
    """Return a new list of songs sorted by the given field and order.

    Args:
        songs: Source list of Song objects (never mutated).
        sort_by: Criterion — 'title', 'artist', 'duration', or 'date'
            (also accepts 'judul', 'artis', 'durasi', 'date_added', 'tanggal').
        order: Sort direction — 'asc' (default) or 'desc'.

    Returns:
        A new list[Song] ordered according to the specified criteria.
        Songs missing metadata for the chosen field are placed at the end.

    Raises:
        ValueError: If sort_by or order is not supported.
    """
    normalized_field = _VALID_SORT_FIELDS.get(sort_by.strip().lower())
    if normalized_field is None:
        raise ValueError(
            f"Kriteria sorting tidak valid: '{sort_by}'. "
            "Gunakan: title, artist, duration, atau date."
        )

    is_descending = _VALID_ORDERS.get(order.strip().lower())
    if is_descending is None:
        raise ValueError(
            f"Urutan sorting tidak valid: '{order}'. Gunakan: asc atau desc."
        )

    present: list[tuple[Any, Song]] = []
    missing: list[Song] = []

    for song in songs:
        value = _extract_sort_value(song, normalized_field)
        if value is None:
            missing.append(song)
        else:
            present.append((value, song))

    present.sort(key=lambda item: item[0], reverse=is_descending)
    return [song for _, song in present] + missing
