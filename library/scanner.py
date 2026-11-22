"""Directory scanner for discovering MP3 files and matching LRC lyric files."""

from pathlib import Path
import re

from library.song import Song

_LRC_TITLE_REGEX = re.compile(r"^\[ti:(.*?)\]$", re.IGNORECASE)
_LRC_ARTIST_REGEX = re.compile(r"^\[ar:(.*?)\]$", re.IGNORECASE)


def _extract_lrc_metadata(lrc_path: Path) -> tuple[str | None, str | None]:
    """Read optional [ti:...] and [ar:...] metadata tags from an LRC file."""
    title: str | None = None
    artist: str | None = None

    try:
        try:
            content = lrc_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = lrc_path.read_text(encoding="latin-1")

        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if title is None:
                title_match = _LRC_TITLE_REGEX.match(line)
                if title_match and title_match.group(1).strip():
                    title = title_match.group(1).strip()

            if artist is None:
                artist_match = _LRC_ARTIST_REGEX.match(line)
                if artist_match and artist_match.group(1).strip():
                    artist = artist_match.group(1).strip()

            if title is not None and artist is not None:
                break
    except OSError:
        return None, None

    return title, artist


def _find_matching_lrc(audio_file: Path, search_dirs: list[Path]) -> Path | None:
    """Find a matching .lrc file with the same base name (stem) as the audio file."""
    target_name_lower = f"{audio_file.stem.lower()}.lrc"

    for directory in search_dirs:
        if not directory.is_dir():
            continue

        direct_candidate = directory / f"{audio_file.stem}.lrc"
        if direct_candidate.is_file():
            return direct_candidate

        try:
            for entry in directory.iterdir():
                if entry.is_file() and entry.name.lower() == target_name_lower:
                    return entry
        except OSError:
            continue

    return None


def scan_directory(path: Path | str, lyrics_dir: Path | str | None = None) -> list[Song]:
    """Scan a directory for MP3 files and pair them with matching LRC files.

    Matches `<name>.mp3` with `<name>.lrc` in the provided lyrics directory,
    a sibling/child `lyrics` directory, or the same directory as the MP3 file.
    Handles invalid or unreadable entries gracefully without failing the whole scan.
    """
    base_path = Path(path)
    if not base_path.exists() or not base_path.is_dir():
        return []

    # Support scanning either a direct music folder or a parent data folder containing music/
    music_dir = base_path
    try:
        has_direct_mp3 = any(
            entry.is_file() and entry.suffix.lower() == ".mp3"
            for entry in base_path.iterdir()
        )
    except OSError:
        return []

    if not has_direct_mp3 and (base_path / "music").is_dir():
        music_dir = base_path / "music"

    # Build ordered list of directories to search for matching .lrc files
    lrc_search_dirs: list[Path] = []
    if lyrics_dir is not None:
        lrc_search_dirs.append(Path(lyrics_dir))

    for candidate_dir in (
        music_dir.parent / "lyrics",
        base_path / "lyrics",
        music_dir,
    ):
        if candidate_dir not in lrc_search_dirs:
            lrc_search_dirs.append(candidate_dir)

    try:
        mp3_files = sorted(
            (
                entry
                for entry in music_dir.iterdir()
                if entry.is_file() and entry.suffix.lower() == ".mp3"
            ),
            key=lambda item: item.name.lower(),
        )
    except OSError:
        return []

    songs: list[Song] = []
    for audio_file in mp3_files:
        try:
            matching_lrc = _find_matching_lrc(audio_file, lrc_search_dirs)
            default_title = audio_file.stem.replace("_", " ").title()
            artist = "Unknown Artist"

            if matching_lrc is not None:
                _, lrc_artist = _extract_lrc_metadata(matching_lrc)
                if lrc_artist:
                    artist = lrc_artist

            song = Song(
                audio_path=audio_file,
                lyric_path=matching_lrc,
                title=default_title,
                artist=artist,
                duration=None,
            )
            songs.append(song)
        except OSError:
            # NFR-02: Satu file bermasalah tidak boleh menggagalkan seluruh library
            continue

    return songs
