from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from uuid import uuid4

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YdlDownloadError

from app.config import get_settings
from app.core.errors import GrabberError, NeedsAuth, TooLarge, TooLong, UnsupportedLink
from app.core.models import DownloadResult, MediaInfo, MediaKind, Variant
from app.core.progress import ProgressState, human_size
from app.providers import Provider

_AUTH_MARKERS = (
    "sign in",
    "log in",
    "login required",
    "confirm you're not a bot",
    "private video",
    "members-only",
    "rate-limit reached",
)
_THUMB_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _base_opts(provider: Provider) -> dict:
    settings = get_settings()
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "noplaylist": True,
        "restrictfilenames": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
    }
    if settings.proxy:
        opts["proxy"] = settings.proxy
    opts.update(provider.ydl_opts())
    return opts


def _translate(error: Exception, provider: Provider) -> GrabberError:
    text = str(error).lower()
    if any(marker in text for marker in _AUTH_MARKERS):
        return NeedsAuth(provider.cookies_hint())
    if "unsupported url" in text or "no video formats" in text:
        return UnsupportedLink("Не понимаю эту ссылку — yt-dlp не знает такой сайт или страницу.")
    return GrabberError(f"Не получилось: {error}")


# --- probe ---------------------------------------------------------------


async def probe(url: str, provider: Provider) -> MediaInfo:
    return await asyncio.to_thread(_probe_sync, url, provider)


def _probe_sync(url: str, provider: Provider) -> MediaInfo:
    try:
        with YoutubeDL(_base_opts(provider)) as ydl:
            raw = ydl.extract_info(url, download=False)
    except YdlDownloadError as exc:
        raise _translate(exc, provider) from exc

    if raw is None:
        raise UnsupportedLink("По ссылке ничего не нашлось.")
    if raw.get("_type") == "playlist":
        entries = [e for e in (raw.get("entries") or []) if e]
        if not entries:
            raise UnsupportedLink("Это плейлист без доступных видео.")
        # Плейлисты пока не качаем целиком — берём первый элемент.
        raw = entries[0]

    heights = sorted(
        {
            f["height"]
            for f in (raw.get("formats") or [])
            if f.get("height") and f.get("vcodec") not in (None, "none")
        },
        reverse=True,
    )
    info = MediaInfo(
        url=raw.get("webpage_url") or url,
        title=raw.get("title") or "media",
        extractor=raw.get("extractor_key") or provider.name,
        duration=int(raw["duration"]) if raw.get("duration") else None,
        heights=tuple(heights),
        is_live=bool(raw.get("is_live")),
        uploader=raw.get("uploader") or raw.get("channel"),
        raw=raw,
    )

    settings = get_settings()
    if info.is_live:
        raise UnsupportedLink("Это прямой эфир — скачать целиком нельзя.")
    if info.duration and info.duration > settings.max_duration_sec:
        raise TooLong(
            f"Слишком длинное: {info.duration // 60} мин, "
            f"лимит {settings.max_duration_sec // 60} мин."
        )
    return info


# --- download ------------------------------------------------------------


async def download(
    info: MediaInfo,
    variant: Variant,
    provider: Provider,
    state: ProgressState,
) -> tuple[DownloadResult, Path]:
    """Скачивает вариант. Возвращает результат и папку джобы — её чистит вызывающий."""
    job_dir = get_settings().download_dir / uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = await asyncio.to_thread(_download_sync, info, variant, provider, state, job_dir)
        return result, job_dir
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise


def _download_sync(
    info: MediaInfo,
    variant: Variant,
    provider: Provider,
    state: ProgressState,
    job_dir: Path,
) -> DownloadResult:
    settings = get_settings()

    estimated = (
        info.estimated_audio_size()
        if variant.kind is MediaKind.AUDIO
        else info.estimated_video_size(variant.height)
    )
    if estimated and estimated > settings.max_filesize_bytes:
        raise TooLarge(
            f"Этот вариант весит ~{human_size(estimated)}, "
            f"а Telegram примет от бота максимум {settings.max_filesize_mb} МБ.\n"
            f"Возьми качество ниже или mp3."
        )

    def progress_hook(payload: dict) -> None:
        status = payload.get("status")
        if status == "downloading":
            state.stage = "downloading"
            state.downloaded = payload.get("downloaded_bytes") or 0
            state.total = payload.get("total_bytes") or payload.get("total_bytes_estimate")
            state.speed = payload.get("speed")
            state.eta = payload.get("eta")
        elif status == "finished":
            state.stage = "processing"

    opts = _base_opts(provider) | {
        "format": variant.ydl_format,
        "outtmpl": {"default": str(job_dir / "%(title).120s.%(ext)s")},
        "progress_hooks": [progress_hook],
        "writethumbnail": variant.write_thumbnail,
    }
    if variant.merge_output_format:
        opts["merge_output_format"] = variant.merge_output_format
    if variant.postprocessors:
        opts["postprocessors"] = list(variant.postprocessors)

    try:
        with YoutubeDL(opts) as ydl:
            raw = ydl.extract_info(info.url, download=True)
    except YdlDownloadError as exc:
        raise _translate(exc, provider) from exc

    path = _resulting_file(raw, job_dir)
    size = path.stat().st_size
    if size > settings.max_filesize_bytes:
        raise TooLarge(
            f"Файл получился {human_size(size)} — Telegram примет от бота максимум "
            f"{settings.max_filesize_mb} МБ. Возьми качество ниже или mp3."
        )

    return DownloadResult(
        path=path,
        kind=variant.kind,
        title=info.title,
        duration=info.duration,
        width=raw.get("width") if variant.kind is MediaKind.VIDEO else None,
        height=raw.get("height") if variant.kind is MediaKind.VIDEO else None,
        uploader=info.uploader,
    )


def _resulting_file(raw: dict | None, job_dir: Path) -> Path:
    """yt-dlp сообщает итоговый файл в requested_downloads; иначе ищем на диске."""
    for entry in (raw or {}).get("requested_downloads") or []:
        candidate = entry.get("filepath") or entry.get("_filename")
        if candidate and Path(candidate).exists():
            return Path(candidate)

    files = [
        p
        for p in job_dir.iterdir()
        if p.is_file() and p.suffix.lower() not in _THUMB_SUFFIXES and not p.name.endswith(".part")
    ]
    if not files:
        raise GrabberError("Скачивание завершилось, но файла нет. Попробуй ещё раз.")
    return max(files, key=lambda p: p.stat().st_size)
