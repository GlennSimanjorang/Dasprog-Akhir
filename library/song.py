from dataclasses import dataclass
from pathlib import Path

@dataclass
class Song:
    audio_path: Path
    lyric_path: Path | None
    title: str
    artist: str | None
    duration: float | None

    @property
    def has_lyrics(self) -> bool:
        return self.lyric_path is not None