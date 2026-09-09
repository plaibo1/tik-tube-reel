from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class MediaKind(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"


@dataclass(frozen=True)
class MediaInfo:
    """Результат probe: что за ссылка, без скачивания."""

    url: str
    title: str
    extractor: str
    duration: int | None
    heights: tuple[int, ...]
    is_live: bool
    uploader: str | None
    raw: dict

    def estimated_video_size(self, height: int | None) -> int | None:
        """Оценка размера video+audio, если yt-dlp знает размеры форматов."""
        formats = self.raw.get("formats") or []
        video = _largest(
            f
            for f in formats
            if f.get("vcodec") not in (None, "none")
            and (height is None or f.get("height") == height)
        )
        if video is None:
            return None
        return video + (self.estimated_audio_size() or 0)

    def estimated_audio_size(self) -> int | None:
        """Оценка размера только звуковой дорожки (для mp3-варианта)."""
        formats = self.raw.get("formats") or []
        return _largest(
            f
            for f in formats
            if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
        )


def _largest(formats: Iterable[dict]) -> int | None:
    sizes = [f.get("filesize") or f.get("filesize_approx") for f in formats]
    sizes = [s for s in sizes if s]
    return max(sizes) if sizes else None


@dataclass(frozen=True)
class Variant:
    """Один вариант скачивания — то, что становится кнопкой под сообщением."""

    key: str
    label: str
    kind: MediaKind
    ydl_format: str
    height: int | None = None
    merge_output_format: str | None = "mp4"
    postprocessors: tuple[dict, ...] = field(default_factory=tuple)
    write_thumbnail: bool = False


@dataclass
class DownloadResult:
    path: Path
    kind: MediaKind
    title: str
    duration: int | None
    width: int | None
    height: int | None
    uploader: str | None

    @property
    def size(self) -> int:
        return self.path.stat().st_size
