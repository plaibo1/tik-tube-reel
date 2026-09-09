from __future__ import annotations

from aiogram.types import FSInputFile, Message

from app.core.models import DownloadResult, MediaKind
from app.core.progress import human_duration, human_size


async def send_result(message: Message, result: DownloadResult) -> None:
    file = FSInputFile(result.path, filename=result.path.name)
    caption = _caption(result)

    if result.kind is MediaKind.VIDEO:
        await message.answer_video(
            video=file,
            caption=caption,
            duration=result.duration,
            width=result.width,
            height=result.height,
            supports_streaming=True,
        )
    else:
        await message.answer_audio(
            audio=file,
            caption=caption,
            title=result.title[:64],
            performer=(result.uploader or "")[:64] or None,
            duration=result.duration,
        )


def _caption(result: DownloadResult) -> str:
    meta = [human_size(result.size)]
    if result.duration:
        meta.append(human_duration(result.duration))
    if result.height:
        meta.append(f"{result.height}p")
    return f"{result.title}\n{' · '.join(meta)}"[:1024]
