"""In-memory playlist manager for v1.0 without database or file persistence."""

from library.song import Song


class PlaylistManager:
    """Manage named playlists and their ordered song lists in memory."""

    def __init__(self) -> None:
        self._playlists: dict[str, list[Song]] = {}

    def create(self, name: str) -> None:
        """Create a new empty playlist with a unique non-empty name."""
        clean = name.strip()
        if not clean:
            raise ValueError("Nama playlist tidak boleh kosong.")
        if clean in self._playlists:
            raise ValueError(f"Playlist '{clean}' sudah ada.")
        self._playlists[clean] = []

    def list_names(self) -> list[str]:
        """Return all created playlist names."""
        return list(self._playlists.keys())

    def get_songs(self, name: str) -> list[Song]:
        """Return a shallow copy of songs in the named playlist."""
        return list(self._get_playlist(name))

    def add_song(self, name: str, song: Song) -> None:
        """Append a song to an existing playlist."""
        self._get_playlist(name).append(song)

    def remove_song(self, name: str, index: int) -> Song:
        """Remove and return the song at 0-based index from a playlist."""
        songs = self._get_playlist(name)
        if index < 0 or index >= len(songs):
            raise IndexError("Nomor lagu di playlist tidak valid.")
        return songs.pop(index)

    def _get_playlist(self, name: str) -> list[Song]:
        clean = name.strip()
        if clean not in self._playlists:
            raise KeyError(f"Playlist '{clean}' tidak ditemukan.")
        return self._playlists[clean]
