from __future__ import annotations

from app.providers.base import Provider
from app.providers.generic import GenericProvider
from app.providers.instagram import InstagramProvider
from app.providers.tiktok import TikTokProvider
from app.providers.youtube import YouTubeProvider

# Порядок важен: generic матчит любой http(s) и должен быть последним.
PROVIDERS: tuple[Provider, ...] = (
    YouTubeProvider(),
    InstagramProvider(),
    TikTokProvider(),
    GenericProvider(),
)


def resolve(url: str) -> Provider:
    for provider in PROVIDERS:
        if provider.matches(url):
            return provider
    return PROVIDERS[-1]


def by_name(name: str) -> Provider:
    for provider in PROVIDERS:
        if provider.name == name:
            return provider
    return PROVIDERS[-1]


__all__ = ["PROVIDERS", "Provider", "by_name", "resolve"]
