from __future__ import annotations

from abc import ABC, abstractmethod
from urllib.parse import urlparse

from app.config import get_settings
from app.core.models import MediaInfo, MediaKind, Variant


# Форматы, дружелюбные к Telegram: H.264 + AAC в mp4 проигрываются везде,
# включая iOS. Поэтому avc1/mp4a запрашиваем в первую очередь, а «что угодно»
# оставляем как fallback.
def video_format(height: int | None) -> str:
    cap = f"[height<={height}]" if height else ""
    return f"bv*[vcodec~='^(avc1|h264)']{cap}+ba[acodec~='^mp4a']/bv*{cap}+ba/b{cap}"


AUDIO_MP3 = Variant(
    key="mp3",
    label="🎧 Аудио (mp3)",
    kind=MediaKind.AUDIO,
    ydl_format="ba/b",
    merge_output_format=None,
    write_thumbnail=True,
    postprocessors=(
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
        {"key": "FFmpegThumbnailsConvertor", "format": "jpg"},
        {"key": "EmbedThumbnail"},
        {"key": "FFmpegMetadata", "add_metadata": True},
    ),
)


def video_variant(height: int) -> Variant:
    return Variant(
        key=f"v{height}",
        label=f"🎬 {height}p",
        kind=MediaKind.VIDEO,
        ydl_format=video_format(height),
        height=height,
    )


BEST_VIDEO = Variant(
    key="vbest",
    label="🎬 Видео",
    kind=MediaKind.VIDEO,
    ydl_format=video_format(None),
)


class Provider(ABC):
    """Источник ссылок.

    Чтобы добавить новый сервис — создай наследника, объяви `name` и `hosts`,
    верни варианты скачивания и зарегистрируй его в app/providers/__init__.py.
    Скачиванием занимается yt-dlp, провайдер только описывает специфику.
    """

    name: str = "base"
    title: str = "Источник"
    hosts: tuple[str, ...] = ()
    # Нужны ли cookies, чтобы вообще что-то отдать (для текста ошибки).
    needs_cookies: bool = False

    def matches(self, url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        host = host.removeprefix("www.")
        return any(host == h or host.endswith("." + h) for h in self.hosts)

    def ydl_opts(self) -> dict:
        """Специфика источника для yt-dlp: cookies, заголовки, extractor_args."""
        opts: dict = {}
        cookies = get_settings().cookies_dir / f"{self.name}.txt"
        if cookies.exists():
            opts["cookiefile"] = str(cookies)
        return opts

    @abstractmethod
    def variants(self, info: MediaInfo) -> list[Variant]:
        """Что предложить пользователю кнопками."""

    def cookies_hint(self) -> str:
        return (
            f"Похоже, {self.title} требует авторизации. "
            f"Положи cookies в `cookies/{self.name}.txt` (формат Netscape) и повтори."
        )
