"""Formatting helpers for displaying the song library in the terminal."""

from library.song import Song


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds as mm:ss, or --:-- when unavailable."""
    if seconds is None or seconds < 0:
        return "--:--"
    total = int(seconds)
    return f"{total // 60:02d}:{total % 60:02d}"


def format_song_list(songs: list[Song]) -> str:
    """Format songs into an aligned text table with index, title, artist, duration, and LRC status."""
    if not songs:
        return "Daftar lagu kosong."

    headers = ("No", "Judul", "Artis", "Durasi", "LRC")
    rows = [
        (
            str(idx),
            song.title,
            song.artist or "-",
            format_duration(song.duration),
            "Ada" if song.has_lyrics else "Tidak ada",
        )
        for idx, song in enumerate(songs, start=1)
    ]

    widths = [max(len(header), *(len(row[i]) for row in rows)) for i, header in enumerate(headers)]
    format_row = lambda cols: "  ".join(val.ljust(width) for val, width in zip(cols, widths)).rstrip()
    divider = "  ".join("-" * width for width in widths)
    return "\n".join([format_row(headers), divider, *(format_row(row) for row in rows)])
