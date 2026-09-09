from __future__ import annotations

from app.core.models import MediaInfo, Variant
from app.providers.base import AUDIO_MP3, BEST_VIDEO, Provider


class InstagramProvider(Provider):
    name = "instagram"
    title = "Instagram"
    hosts = ("instagram.com", "instagr.am", "ddinstagram.com")
    # Публичные Reels часто открываются и без cookies, но Instagram
    # ужесточает это без предупреждения — cookies решают почти всё.
    needs_cookies = True

    def variants(self, info: MediaInfo) -> list[Variant]:
        # Reels отдаются одним готовым mp4, выбирать высоту не из чего.
        return [BEST_VIDEO, AUDIO_MP3]
