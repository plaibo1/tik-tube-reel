from __future__ import annotations

from app.core.models import MediaInfo, Variant
from app.providers.base import AUDIO_MP3, BEST_VIDEO, Provider


class TikTokProvider(Provider):
    name = "tiktok"
    title = "TikTok"
    hosts = ("tiktok.com", "vm.tiktok.com", "vt.tiktok.com")

    def variants(self, info: MediaInfo) -> list[Variant]:
        return [BEST_VIDEO, AUDIO_MP3]
