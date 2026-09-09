from __future__ import annotations

import asyncio
import logging
import re
import shutil
from contextlib import suppress
from dataclasses import dataclass

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.chat_action import ChatActionSender

from app.config import get_settings
from app.core.cache import TTLCache
from app.core.downloader import download, probe
from app.core.errors import GrabberError
from app.core.models import MediaInfo, MediaKind, Variant
from app.core.progress import ProgressState, human_duration
from app.core.sender import send_result
from app.providers import Provider, by_name, resolve

logger = logging.getLogger(__name__)
router = Router(name="link")

URL_RE = re.compile(r"https?://\S+")
PROGRESS_INTERVAL_SEC = 3.0


@dataclass
class PendingLink:
    info: MediaInfo
    provider_name: str


class DownloadCB(CallbackData, prefix="dl"):
    token: str
    variant: str


_links: TTLCache[PendingLink] = TTLCache(get_settings().link_ttl_sec)
_slots = asyncio.Semaphore(get_settings().max_concurrent_downloads)


@router.message(F.text.regexp(URL_RE))
async def on_link(message: Message) -> None:
    url = URL_RE.search(message.text or "")
    if url is None:
        return
    provider = resolve(url.group(0))

    status = await message.answer("🔍 Читаю ссылку…")
    try:
        info = await probe(url.group(0), provider)
    except GrabberError as exc:
        await status.edit_text(f"⚠️ {exc}")
        return
    except Exception:
        logger.exception("probe failed: %s", url.group(0))
        await status.edit_text("⚠️ Не смог прочитать ссылку. Подробности в логах.")
        return

    token = _links.put(PendingLink(info=info, provider_name=provider.name))
    await status.edit_text(
        f"*{info.title}*\n{provider.title} · {human_duration(info.duration)}\n\nЧто скачать?",
        reply_markup=_keyboard(token, provider.variants(info)),
    )


@router.message(F.text & ~F.text.startswith("/"))
async def on_not_a_link(message: Message) -> None:
    await message.answer("Пришли ссылку на видео. /help — что умею.")


@router.callback_query(DownloadCB.filter())
async def on_variant(callback: CallbackQuery, callback_data: DownloadCB) -> None:
    pending = _links.get(callback_data.token)
    if pending is None or not isinstance(callback.message, Message):
        await callback.answer("Ссылка устарела — пришли её заново.", show_alert=True)
        return

    provider = by_name(pending.provider_name)
    variant = next(
        (v for v in provider.variants(pending.info) if v.key == callback_data.variant),
        None,
    )
    if variant is None:
        await callback.answer("Этот вариант больше недоступен.", show_alert=True)
        return

    await callback.answer()
    await _run_job(callback.message, pending.info, provider, variant)


async def _run_job(status: Message, info: MediaInfo, provider: Provider, variant: Variant) -> None:
    state = ProgressState()
    await status.edit_text(state.render(), reply_markup=None)
    reporter = asyncio.create_task(_report(status, state))
    action = "upload_video" if variant.kind is MediaKind.VIDEO else "upload_voice"

    try:
        async with _slots:
            state.stage = "downloading"
            result, job_dir = await download(info, variant, provider, state)
        try:
            state.stage = "uploading"
            async with ChatActionSender(bot=status.bot, chat_id=status.chat.id, action=action):
                await send_result(status, result)
        finally:
            shutil.rmtree(job_dir, ignore_errors=True)
    except GrabberError as exc:
        await _safe_edit(status, f"⚠️ {exc}")
        return
    except Exception:
        logger.exception("download failed: %s", info.url)
        await _safe_edit(status, "⚠️ Скачивание упало. Подробности в логах.")
        return
    finally:
        reporter.cancel()

    await _safe_delete(status)


async def _report(status: Message, state: ProgressState) -> None:
    """Обновляет одно и то же сообщение, не чаще раза в PROGRESS_INTERVAL_SEC.

    Telegram ругается на слишком частые edit и на edit тем же текстом,
    поэтому храним последний отправленный текст.
    """
    last = ""
    while True:
        await asyncio.sleep(PROGRESS_INTERVAL_SEC)
        text = state.render()
        if text != last:
            last = text
            await _safe_edit(status, text)


async def _safe_edit(message: Message, text: str) -> None:
    # «message is not modified» и «message to edit not found» — не наши проблемы.
    with suppress(TelegramBadRequest):
        await message.edit_text(text)


async def _safe_delete(message: Message) -> None:
    with suppress(TelegramBadRequest):
        await message.delete()


def _keyboard(token: str, variants: list[Variant]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=v.label,
                callback_data=DownloadCB(token=token, variant=v.key).pack(),
            )
        ]
        for v in variants
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
