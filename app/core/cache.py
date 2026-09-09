from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, TypeVar
from uuid import uuid4

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Короткая память процесса: id кнопки -> распознанная ссылка.

    Для одного инстанса этого достаточно. Если появится второй воркер —
    менять здесь на Redis, интерфейс тот же.
    """

    def __init__(self, ttl_sec: int) -> None:
        self._ttl = ttl_sec
        self._data: dict[str, _Entry[T]] = {}

    def put(self, value: T) -> str:
        self._prune()
        token = uuid4().hex[:12]
        self._data[token] = _Entry(value, time.monotonic() + self._ttl)
        return token

    def get(self, token: str) -> T | None:
        self._prune()
        entry = self._data.get(token)
        return entry.value if entry else None

    def _prune(self) -> None:
        now = time.monotonic()
        for token in [t for t, e in self._data.items() if e.expires_at < now]:
            del self._data[token]
