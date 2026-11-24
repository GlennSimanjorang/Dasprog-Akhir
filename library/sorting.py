"""Pure sorting functions for song collections."""

from library.song import Song

_VALID_KEYS = {"title", "artist", "duration", "date_added"}
_VALID_ORDERS = {"asc", "desc"}


def _sort_value(song: Song, key: str) -> str | float | None:
    if key == "artist":
        return song.artist.casefold() if song.artist else None
    if key == "duration":
        return song.duration
    try:
        return song.audio_path.stat().st_mtime
    except OSError:
        return None


def sort_songs(songs: list[Song], sort_by: str = "title", order: str = "asc") -> list[Song]:
    """Return a new sorted list of songs without mutating the input list."""
    key = sort_by.strip().lower()
    direction = order.strip().lower()
    if key not in _VALID_KEYS:
        raise ValueError(f"Kriteria urut '{sort_by}' tidak valid. Pilih: title, artist, duration, date_added.")
    if direction not in _VALID_ORDERS:
        raise ValueError(f"Arah urut '{order}' tidak valid. Pilih: asc atau desc.")

    reverse = direction == "desc"
    if key == "title":
        return sorted(songs, key=lambda song: song.title.casefold(), reverse=reverse)

    # Keep entries with missing metadata at the bottom for both asc and desc orders.
    with_value: list[tuple[str | float, Song]] = []
    without_value: list[Song] = []
    for song in songs:
        value = _sort_value(song, key)
        if value is None:
            without_value.append(song)
        else:
            with_value.append((value, song))

    with_value.sort(key=lambda item: item[0], reverse=reverse)
    return [song for _, song in with_value] + without_value
