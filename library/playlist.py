"""Basic playlist management models and operations (FR-15)."""

from pathlib import Path

from library.song import Song


class Playlist:
    """Represents a named user playlist containing Song entries."""

    def __init__(self, name: str, songs: list[Song] | None = None) -> None:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Nama playlist tidak boleh kosong.")
        self.name = cleaned_name
        self._songs: list[Song] = list(songs) if songs else []

    @property
    def songs(self) -> list[Song]:
        """Return a defensive copy of songs in this playlist."""
        return list(self._songs)

    def add_song(self, song: Song, allow_duplicate: bool = False) -> bool:
        """Add a song to the playlist; returns False if duplicate is disallowed."""
        if not allow_duplicate and any(
            existing.audio_path == song.audio_path for existing in self._songs
        ):
            return False
        self._songs.append(song)
        return True

    def remove_song(self, song: Song) -> bool:
        """Remove the first matching song (by equality or audio_path)."""
        for idx, existing in enumerate(self._songs):
            if existing == song or existing.audio_path == song.audio_path:
                self._songs.pop(idx)
                return True
        return False

    def remove_at(self, index: int) -> Song:
        """Remove and return the song at the given 0-based index."""
        if index < 0 or index >= len(self._songs):
            raise IndexError(
                f"Indeks lagu {index} di luar jangkauan playlist '{self.name}'."
            )
        return self._songs.pop(index)

    def get_songs(self) -> list[Song]:
        """Return a copy of all songs in the playlist."""
        return list(self._songs)

    def select_song(self, index: int) -> Song:
        """Return the song at the given 0-based index without removing it."""
        if index < 0 or index >= len(self._songs):
            raise IndexError(
                f"Indeks lagu {index} di luar jangkauan playlist '{self.name}'."
            )
        return self._songs[index]

    def get_audio_paths(self) -> list[Path]:
        """Return audio_path list compatible with CoreController.set_playlist()."""
        return [song.audio_path for song in self._songs]

    def clear(self) -> None:
        """Remove all songs from the playlist."""
        self._songs.clear()

    def __len__(self) -> int:
        return len(self._songs)


class PlaylistManager:
    """Manages creation, lookup, and editing of multiple named playlists."""

    def __init__(self) -> None:
        self._playlists: dict[str, Playlist] = {}

    def _normalize_key(self, name: str) -> str:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Nama playlist tidak boleh kosong.")
        return cleaned.lower()

    def create_playlist(self, name: str) -> Playlist:
        """Create and register a new named playlist."""
        key = self._normalize_key(name)
        if key in self._playlists:
            raise ValueError(f"Playlist '{name.strip()}' sudah ada.")
        playlist = Playlist(name=name)
        self._playlists[key] = playlist
        return playlist

    def get_playlist(self, name: str) -> Playlist | None:
        """Find a playlist by name (case-insensitive), or None if not found."""
        cleaned = name.strip()
        if not cleaned:
            return None
        return self._playlists.get(cleaned.lower())

    def _require_playlist(self, name: str) -> Playlist:
        playlist = self.get_playlist(name)
        if playlist is None:
            raise KeyError(f"Playlist '{name.strip()}' tidak ditemukan.")
        return playlist

    def delete_playlist(self, name: str) -> bool:
        """Delete a playlist by name; returns True if deleted."""
        cleaned = name.strip()
        if not cleaned:
            return False
        return self._playlists.pop(cleaned.lower(), None) is not None

    def list_playlists(self) -> list[Playlist]:
        """Return all registered playlists."""
        return list(self._playlists.values())

    def add_song_to_playlist(self, name: str, song: Song) -> bool:
        """Add a song to the specified playlist."""
        playlist = self._require_playlist(name)
        return playlist.add_song(song)

    def remove_song_from_playlist(self, name: str, index: int) -> Song:
        """Remove and return the song at 0-based index from the playlist."""
        playlist = self._require_playlist(name)
        return playlist.remove_at(index)

    def get_playlist_songs(self, name: str) -> list[Song]:
        """Return all songs in the specified playlist."""
        playlist = self._require_playlist(name)
        return playlist.get_songs()

    def select_song_from_playlist(self, name: str, index: int) -> Song:
        """Select and return a song at 0-based index from the specified playlist."""
        playlist = self._require_playlist(name)
        return playlist.select_song(index)
