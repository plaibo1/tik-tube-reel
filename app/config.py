from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(min_length=1)
    # NoDecode обязателен: без него pydantic-settings пытается json.loads
    # значение из env и падает на списке через запятую.
    allowed_user_ids: Annotated[set[int], NoDecode] = Field(default_factory=set)

    # Официальный Bot API: не больше 50 МБ на отправку файла ботом.
    # С локальным Bot API server (--local) лимит 2000 МБ — тогда ставим MAX_FILESIZE_MB=1900.
    tg_api_base: str | None = None
    max_filesize_mb: int = 48

    download_dir: Path = Path("./downloads")
    cookies_dir: Path = Path("./cookies")
    proxy: str | None = None

    max_duration_sec: int = 3 * 60 * 60
    max_height: int = 1080
    max_concurrent_downloads: int = 2

    # Сколько живёт распознанная ссылка (кнопки выбора качества) до истечения.
    link_ttl_sec: int = 30 * 60

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def _split_ids(cls, value: object) -> object:
        # Принимаем «111», «111,222», «111 222» и пустую строку.
        if value is None or value == "":
            return set()
        if isinstance(value, int):
            return {value}
        if isinstance(value, str):
            return {int(chunk) for chunk in value.replace(",", " ").split()}
        return value

    @property
    def max_filesize_bytes(self) -> int:
        return self.max_filesize_mb * 1024 * 1024

    def describe(self) -> str:
        """Строка для лога при старте: что бот реально увидел. Без секретов."""
        cookies = sorted(p.name for p in self.cookies_dir.glob("*.txt"))
        return (
            f"token={'есть' if self.bot_token else 'НЕТ'} "
            f"whitelist={sorted(self.allowed_user_ids) or 'ПУСТО (бот открыт всем)'} "
            f"limit={self.max_filesize_mb}MB "
            f"max_height={self.max_height}p "
            f"api={self.tg_api_base or 'api.telegram.org'} "
            f"proxy={'есть' if self.proxy else 'нет'} "
            f"cookies={cookies or 'нет'} "
            f"downloads={self.download_dir}"
        )


@lru_cache
def get_settings() -> Settings:
    try:
        settings = Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        missing = sorted({str(error["loc"][0]).upper() for error in exc.errors()})
        raise SystemExit(
            "Не заданы переменные окружения: "
            + ", ".join(missing)
            + ".\nЛокально: cp .env.example .env и заполни."
            "\nВ Docker/Dokploy: переменные должны быть перечислены в блоке"
            " environment: в docker-compose.yml — панель прокидывает свои"
            " значения только в интерполяцию ${...}, а не в контейнер."
        ) from exc

    settings.download_dir.mkdir(parents=True, exist_ok=True)
    settings.cookies_dir.mkdir(parents=True, exist_ok=True)
    return settings
