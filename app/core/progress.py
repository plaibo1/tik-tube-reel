from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProgressState:
    """Состояние джобы, которое пишет поток yt-dlp и читает асинхронный цикл.

    Хуки yt-dlp вызываются в рабочем потоке, поэтому здесь только простые
    присваивания — обращаться из потока к event loop не нужно.
    """

    stage: str = "queued"
    downloaded: int = 0
    total: int | None = None
    speed: float | None = None
    eta: int | None = None

    def render(self) -> str:
        if self.stage == "queued":
            return "⏳ В очереди…"
        if self.stage == "processing":
            return "🎛 Склеиваю видео и звук…"
        if self.stage == "uploading":
            return "📤 Отправляю в Telegram…"

        parts = [f"⬇️ Скачиваю {self._percent()}"]
        if self.total:
            parts.append(f"{human_size(self.downloaded)} / {human_size(self.total)}")
        else:
            parts.append(human_size(self.downloaded))
        if self.speed:
            parts.append(f"{human_size(int(self.speed))}/s")
        if self.eta:
            parts.append(f"осталось ~{self.eta} с")
        return "\n".join([parts[0], "  ".join(parts[1:])])

    def _percent(self) -> str:
        if not self.total:
            return ""
        done = min(int(self.downloaded / self.total * 10), 10)
        return f"{'█' * done}{'░' * (10 - done)} {self.downloaded / self.total:.0%}"


def human_size(num: int | None) -> str:
    if not num:
        return "0 B"
    value = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def human_duration(seconds: int | None) -> str:
    if not seconds:
        return "—"
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
