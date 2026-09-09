from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.config import get_settings
from app.providers import PROVIDERS

router = Router(name="common")

HELP = """*Скачивалка по ссылке*

Просто пришли ссылку — я предложу качество.

Умею: {sources} и ещё ~1000 сайтов через yt-dlp.

Лимиты: до {size} МБ на файл, до {minutes} мин длительности, максимум {height}p.
Плейлисты не качаю целиком — беру первое видео."""


@router.message(CommandStart())
@router.message(Command("help"))
async def start(message: Message) -> None:
    settings = get_settings()
    sources = ", ".join(p.title for p in PROVIDERS if p.name != "generic")
    await message.answer(
        HELP.format(
            sources=sources,
            size=settings.max_filesize_mb,
            minutes=settings.max_duration_sec // 60,
            height=settings.max_height,
        )
    )
