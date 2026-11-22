"""Searching and filtering utilities for song collections (FR-13, FR-14).

Implements pure functions that return filtered song lists without
modifying the original source list (Business Rule 3).
"""

from library.song import Song

_VALID_FILTER_KEYS = {"has_lyrics", "artist"}


def search_songs(songs: list[Song], keyword: str) -> list[Song]:
    """Return songs whose title or artist matches keyword (case-insensitive).

    Args:
        songs: Source list of Song objects (never mutated).
        keyword: Search string to match against song title or artist.

    Returns:
        A new list[Song] containing matching songs, or a shallow copy of songs
        if keyword is empty/whitespace.
    """
    query = keyword.strip().lower()
    if not query:
        return list(songs)

    return [
        song
        for song in songs
        if query in song.title.lower()
        or (song.artist is not None and query in song.artist.lower())
    ]


def filter_songs(
    songs: list[Song],
    criteria: dict[str, object] | None = None,
) -> list[Song]:
    """Filter songs by LRC availability and/or artist name.

    Args:
        songs: Source list of Song objects (never mutated).
        criteria: Optional mapping supporting keys:
            - 'has_lyrics': bool
            - 'artist': str (case-insensitive substring match)

    Returns:
        A new list[Song] matching all specified criteria.

    Raises:
        ValueError: If criteria contains unknown keys or invalid value types.
    """
    if not criteria:
        return list(songs)

    unknown_keys = set(criteria.keys()) - _VALID_FILTER_KEYS
    if unknown_keys:
        raise ValueError(
            f"Kriteria filter tidak dikenali: {', '.join(sorted(unknown_keys))}. "
            "Gunakan: has_lyrics atau artist."
        )

    has_lyrics_filter: bool | None = None
    if "has_lyrics" in criteria and criteria["has_lyrics"] is not None:
        raw_has_lyrics = criteria["has_lyrics"]
        if not isinstance(raw_has_lyrics, bool):
            raise ValueError("Kriteria 'has_lyrics' harus bertipe bool (True/False).")
        has_lyrics_filter = raw_has_lyrics

    artist_query: str | None = None
    if "artist" in criteria and criteria["artist"] is not None:
        raw_artist = criteria["artist"]
        if not isinstance(raw_artist, str):
            raise ValueError("Kriteria 'artist' harus bertipe str.")
        cleaned_artist = raw_artist.strip().lower()
        if cleaned_artist:
            artist_query = cleaned_artist

    results: list[Song] = []
    for song in songs:
        if has_lyrics_filter is not None and song.has_lyrics is not has_lyrics_filter:
            continue
        if artist_query is not None:
            if song.artist is None or artist_query not in song.artist.lower():
                continue
        results.append(song)

    return results
