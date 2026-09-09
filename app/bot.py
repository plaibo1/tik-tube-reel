from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode

from app.config import get_settings
from app.handlers import router
from app.middlewares import WhitelistMiddleware

# Заливка большого файла в Telegram занимает минуты — дефолтных 60 с мало.
UPLOAD_TIMEOUT_SEC = 900


def build_bot() -> Bot:
    settings = get_settings()
    api = (
        TelegramAPIServer.from_base(settings.tg_api_base, is_local=True)
        if settings.tg_api_base
        else None
    )
    session = (
        AiohttpSession(api=api, timeout=UPLOAD_TIMEOUT_SEC)
        if api
        else AiohttpSession(timeout=UPLOAD_TIMEOUT_SEC)
    )
    return Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.message.middleware(WhitelistMiddleware())
    dispatcher.callback_query.middleware(WhitelistMiddleware())
    dispatcher.include_router(router)
    return dispatcher


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    bot = build_bot()
    dispatcher = build_dispatcher()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def run() -> None:
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("stopped")
