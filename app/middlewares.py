from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import get_settings


class WhitelistMiddleware(BaseMiddleware):
    """Личный бот: пускаем только своих.

    Если ALLOWED_USER_IDS пуст, бот открыт всем — на публичном хосте так делать
    не стоит, чужие скачивания пойдут с твоего IP и твоих cookies.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        allowed = get_settings().allowed_user_ids
        user = data.get("event_from_user")
        if allowed and (user is None or user.id not in allowed):
            if isinstance(event, Message):
                await event.answer(f"Бот приватный. Твой id: `{user.id if user else '?'}`")
            elif isinstance(event, CallbackQuery):
                await event.answer("Бот приватный.", show_alert=True)
            return None
        return await handler(event, data)
