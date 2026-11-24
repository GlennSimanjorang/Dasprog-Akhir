"""Pure search and filter functions for song collections."""

from library.song import Song


def search_songs(songs: list[Song], keyword: str) -> list[Song]:
    """Return songs whose title or artist matches keyword (case-insensitive)."""
    term = keyword.strip().casefold()
    if not term:
        return list(songs)
    return [
        song
        for song in songs
        if term in song.title.casefold()
        or (song.artist is not None and term in song.artist.casefold())
    ]


def filter_songs(songs: list[Song], criteria: dict) -> list[Song]:
    """Return songs matching criteria keys: has_lyrics (bool) and artist (str)."""
    result = list(songs)
    if "has_lyrics" in criteria and criteria["has_lyrics"] is not None:
        want_lyrics = bool(criteria["has_lyrics"])
        result = [song for song in result if song.has_lyrics is want_lyrics]

    if "artist" in criteria and criteria["artist"] is not None:
        artist_term = str(criteria["artist"]).strip().casefold()
        if artist_term:
            result = [
                song
                for song in result
                if song.artist is not None and artist_term in song.artist.casefold()
            ]
    return result
