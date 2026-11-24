"""Directory scanner for discovering local MP3 tracks and matching LRC lyrics."""

from pathlib import Path
import re

try:
    import pygame
except ImportError:
    pygame = None

from library.song import Song

_META_TAG_RE = re.compile(r"^\[(ti|ar):(.+)\]$", re.IGNORECASE)


def _find_lyric_file(audio_path: Path, root: Path, lyrics_dir: Path | str | None) -> Path | None:
    """Locate a matching .lrc file by stem across standard lyric directories."""
    candidates: list[Path] = []
    lrc_name = f"{audio_path.stem}.lrc"
    if lyrics_dir is not None:
        candidates.append(Path(lyrics_dir) / lrc_name)
    candidates.extend([
        root / "lyrics" / lrc_name,
        root.parent / "lyrics" / lrc_name,
        audio_path.with_suffix(".lrc"),
    ])

    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _read_lrc_metadata(lyric_path: Path) -> tuple[str | None, str | None]:
    """Read optional [ti:...] and [ar:...] metadata tags from an LRC file."""
    try:
        try:
            content = lyric_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = lyric_path.read_text(encoding="latin-1")
    except (OSError, UnicodeError):
        return None, None

    title: str | None = None
    artist: str | None = None
    for line in content.splitlines():
        match = _META_TAG_RE.match(line.strip())
        if not match:
            continue
        tag = match.group(1).lower()
        value = match.group(2).strip()
        if not value:
            continue
        if tag == "ti" and title is None:
            title = value
        elif tag == "ar" and artist is None:
            artist = value
    return title, artist


def _parse_filename_metadata(stem: str) -> tuple[str | None, str]:
    """Extract (artist, title) from 'Artist - Title' filenames, with fallback title."""
    if " - " in stem:
        artist, title = (part.strip() for part in stem.split(" - ", 1))
        if artist and title:
            return artist, title
    fallback_title = re.sub(r"[_-]+", " ", stem).strip().title() or stem
    return None, fallback_title


def _read_duration(audio_path: Path) -> float | None:
    """Read MP3 duration in seconds using pygame.mixer, or None if unavailable."""
    if pygame is None:
        return None
    try:
        # Skip 0-byte dummy files from tests without starting the audio mixer.
        if audio_path.stat().st_size == 0:
            return None
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        length = float(pygame.mixer.Sound(str(audio_path)).get_length())
        return length if length > 0 else None
    except Exception:
        return None


def _collect_mp3_files(directory: Path) -> list[Path]:
    """Walk directory recursively using pathlib while skipping unreadable entries (NFR-02)."""
    found: list[Path] = []
    try:
        entries = list(directory.iterdir())
    except OSError:
        return found

    for entry in entries:
        try:
            if entry.is_dir() and not entry.is_symlink():
                found.extend(_collect_mp3_files(entry))
            elif entry.is_file() and entry.suffix.lower() == ".mp3":
                found.append(entry)
        except OSError:
            continue
    return found


def scan_directory(path: Path | str, lyrics_dir: Path | str | None = None) -> list[Song]:
    """Scan a directory recursively for MP3 files and pair matching LRC files."""
    root = Path(path)
    try:
        if not root.exists() or not root.is_dir():
            return []
    except OSError:
        return []

    entries = sorted(_collect_mp3_files(root), key=lambda p: (p.name.lower(), str(p)))
    try:
        mixer_was_init = pygame is not None and bool(pygame.mixer.get_init())
    except Exception:
        mixer_was_init = False

    songs: list[Song] = []
    try:
        for entry in entries:
            lyric_path = _find_lyric_file(entry, root, lyrics_dir)
            file_artist, file_title = _parse_filename_metadata(entry.stem)

            if file_artist is not None:
                # Prefer explicit "Artist - Title" filenames so band and title never mix or swap.
                artist, title = file_artist, file_title
            else:
                lrc_title, lrc_artist = _read_lrc_metadata(lyric_path) if lyric_path else (None, None)
                title = lrc_title or file_title
                artist = lrc_artist

            songs.append(
                Song(
                    audio_path=entry,
                    lyric_path=lyric_path,
                    title=title,
                    artist=artist,
                    duration=_read_duration(entry),
                )
            )
    finally:
        # Release mixer if scanner initialized it so CoreController starts cleanly.
        if not mixer_was_init and pygame is not None:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.quit()
            except Exception:
                pass
    return songs
