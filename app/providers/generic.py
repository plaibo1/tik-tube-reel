from __future__ import annotations

from app.config import get_settings
from app.core.models import MediaInfo, Variant
from app.providers.base import AUDIO_MP3, Provider, video_variant

# yt-dlp знает больше тысячи сайтов. Всё, для чего нет своего провайдера,
# едет по общему пути: пробуем, и если экстрактор есть — работает.
FALLBACK_HEIGHTS = (1080, 720, 480)


class GenericProvider(Provider):
    name = "generic"
    title = "Ссылка"

    def matches(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    def variants(self, info: MediaInfo) -> list[Variant]:
        cap = get_settings().max_height
        available = {h for h in info.heights if h <= cap}
        heights = [h for h in FALLBACK_HEIGHTS if h in available] or [min(cap, 720)]
        return [video_variant(h) for h in heights[:3]] + [AUDIO_MP3]
