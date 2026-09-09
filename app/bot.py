from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiohttp_socks import ProxyConnectionError, ProxyError, ProxyTimeoutError

from app.config import get_settings
from app.handlers import router
from app.middlewares import WhitelistMiddleware

# Заливка большого файла в Telegram занимает минуты — дефолтных 60 с мало.
UPLOAD_TIMEOUT_SEC = 900
# Проверка связи при старте: если сети нет, пакеты дропаются молча и
# ядро досылает SYN ~2 минуты. Столько ждать диагноза незачем.
STARTUP_TIMEOUT_SEC = 10

# Ошибки aiohttp_socks — плоские наследники Exception, у них нет общей базы
# с aiohttp.ClientError, поэтому aiogram не оборачивает их в
# TelegramNetworkError и перечислять их приходится вручную.
NETWORK_ERRORS = (
    TelegramNetworkError,
    ProxyError,
    ProxyConnectionError,
    ProxyTimeoutError,
    OSError,
)


def build_bot() -> Bot:
    settings = get_settings()
    api = (
        TelegramAPIServer.from_base(settings.tg_api_base, is_local=True)
        if settings.tg_api_base
        else None
    )
    session_kwargs: dict = {"timeout": UPLOAD_TIMEOUT_SEC}
    if api:
        session_kwargs["api"] = api
    if settings.bot_api_proxy:
        session_kwargs["proxy"] = settings.bot_api_proxy
    session = AiohttpSession(**session_kwargs)
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
    logger = logging.getLogger("app")
    settings = get_settings()
    logger.info("config: %s", settings.describe())

    bot = build_bot()
    dispatcher = build_dispatcher()
    try:
        try:
            me = await bot.get_me(request_timeout=STARTUP_TIMEOUT_SEC)
        except NETWORK_ERRORS as exc:
            _log_no_network(logger, settings, exc)
            raise SystemExit(1) from None
        logger.info("bot: @%s (id=%s), начинаю polling", me.username, me.id)
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


def run() -> None:
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.getLogger(__name__).info("stopped")


def _log_no_network(logger: logging.Logger, settings, exc: Exception) -> None:
    """Сеть до Telegram недоступна — печатаем диагноз, а не стену traceback."""
    host = settings.tg_api_base or "https://api.telegram.org"
    logger.error("Нет связи с %s: %s", host, exc)
    if settings.bot_api_proxy:
        logger.error("Прокси задан, но соединение не открылось — проверь сам прокси.")
    else:
        logger.error(
            "Проверь с сервера: curl -sS -m 5 %s/ . Если висит в таймаут — "
            "исходящие соединения закрыты у хостера или файрволом. "
            "Задай TG_PROXY (socks5://user:pass@host:port или http://...) и передеплой.",
            host,
        )
