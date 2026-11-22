"""Formatting and listing utilities for song collections (FR-03)."""

from library.song import Song


def format_duration(duration: float | None) -> str:
    """Format duration in seconds into mm:ss string, or '--:--' if unavailable."""
    if duration is None or duration < 0:
        return "--:--"
    total_seconds = int(duration)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


def format_lrc_status(song: Song) -> str:
    """Return human-readable LRC availability status for a song."""
    return "Tersedia" if song.has_lyrics else "Tidak ada"


def get_song_listing(songs: list[Song]) -> list[dict[str, object]]:
    """Convert a list of Song objects into structured dictionary entries."""
    listing: list[dict[str, object]] = []
    for idx, song in enumerate(songs, start=1):
        listing.append(
            {
                "number": idx,
                "title": song.title,
                "artist": song.artist or "Unknown Artist",
                "duration": format_duration(song.duration),
                "has_lyrics": song.has_lyrics,
                "lrc_status": format_lrc_status(song),
                "audio_path": song.audio_path,
                "lyric_path": song.lyric_path,
            }
        )
    return listing


def format_song_entry(index: int, song: Song) -> str:
    """Format a single Song row for terminal table display."""
    artist_display = song.artist if song.artist else "Unknown Artist"
    duration_display = format_duration(song.duration)
    lrc_display = format_lrc_status(song)
    return (
        f"{index:>3}. {song.title:<25} | "
        f"{artist_display:<18} | "
        f"{duration_display:^7} | "
        f"LRC: {lrc_display}"
    )


def format_song_list(songs: list[Song]) -> str:
    """Format a collection of Song objects into a readable terminal table."""
    if not songs:
        return "Belum ada lagu di dalam daftar."

    header = (
        f"{'No.':>3}  {'Judul Lagu':<25} | "
        f"{'Artis':<18} | "
        f"{'Durasi':^7} | "
        f"{'Status LRC'}"
    )
    separator = "-" * len(header)
    rows = [format_song_entry(idx, song) for idx, song in enumerate(songs, start=1)]
    return "\n".join([header, separator, *rows])
