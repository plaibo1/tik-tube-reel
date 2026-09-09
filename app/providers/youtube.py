from __future__ import annotations

from app.config import get_settings
from app.core.models import MediaInfo, Variant
from app.providers.base import AUDIO_MP3, Provider, video_variant

# Показываем не все высоты, а понятную лестницу — иначе кнопок становится 12.
PREFERRED_HEIGHTS = (2160, 1440, 1080, 720, 480, 360)


class YouTubeProvider(Provider):
    name = "youtube"
    title = "YouTube"
    hosts = ("youtube.com", "youtu.be", "youtube-nocookie.com")

    def ydl_opts(self) -> dict:
        opts = super().ydl_opts()
        # YouTube иногда отдаёт формат только определённому клиенту.
        # Если поймал «Sign in to confirm you're not a bot» — читай README,
        # обычно лечится cookies + свежим yt-dlp.
        opts["extractor_args"] = {"youtube": {"player_client": ["default"]}}
        return opts

    def variants(self, info: MediaInfo) -> list[Variant]:
        cap = get_settings().max_height
        available = {h for h in info.heights if h <= cap}
        heights = [h for h in PREFERRED_HEIGHTS if h in available]
        if not heights:
            # Высоты неизвестны (бывает на некоторых стримах) — даём одну кнопку.
            heights = [min(cap, 720)]
        return [video_variant(h) for h in heights[:4]] + [AUDIO_MP3]
