from __future__ import annotations

from aiogram import Router

from app.handlers import common, link

router = Router(name="root")
router.include_router(common.router)
# link последним: в нём есть общий текстовый хендлер-заглушка.
router.include_router(link.router)

__all__ = ["router"]
