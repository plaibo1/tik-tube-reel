# media-grabber-bot

Личный Telegram-бот: присылаешь ссылку — получаешь файлом видео или mp3.
Скачиванием занимается [yt-dlp](https://github.com/yt-dlp/yt-dlp), склейкой — ffmpeg.

Из коробки: **YouTube**, **Instagram Reels**, **TikTok** и ещё ~1000 сайтов
через общий fallback-провайдер.

## Быстрый старт

```bash
cp .env.example .env      # вписать BOT_TOKEN и ALLOWED_USER_IDS
brew install ffmpeg       # обязательно
make install              # uv sync
make run
```

Токен — у [@BotFather](https://t.me/BotFather), свой user id — у [@userinfobot](https://t.me/userinfobot).

Через Docker (ffmpeg уже внутри):

```bash
docker compose up -d --build
```

## Лимит 50 МБ и как его обойти

Официальный Bot API не даёт боту отправить файл больше **50 МБ** — это ограничение
Telegram, а не бота. Поэтому `MAX_FILESIZE_MB=48`, и перед скачиванием бот
оценивает размер и предупреждает, если вариант не пролезет.

Снимается это только своим [Bot API server](https://github.com/tdlib/telegram-bot-api)
с флагом `--local` — тогда лимит 2000 МБ:

```bash
# в .env
TG_API_BASE=http://localhost:8081
MAX_FILESIZE_MB=1900
```

## Cookies: YouTube и Instagram

Рано или поздно YouTube ответит «Sign in to confirm you're not a bot» —
особенно с серверного IP. Лечится cookies залогиненного аккаунта:

1. Экспортируй cookies в формате Netscape (расширение вида *Get cookies.txt*).
2. Положи в `cookies/youtube.txt` — провайдер подхватит файл по своему `name`.
3. Для Instagram то же самое: `cookies/instagram.txt` (приватные и часть
   публичных Reels без этого не отдаются).

Если и это не помогло — нужен `PROXY` (жилой, не облачный) в `.env`.
Аккаунт для cookies лучше держать отдельный: за автоматизацию его могут
ограничить.

## Как добавить новый источник

Провайдер описывает только специфику сайта — скачивает всё равно yt-dlp.
Достаточно наследника и одной строки в реестре:

```python
# app/providers/vk.py
from app.core.models import MediaInfo, Variant
from app.providers.base import AUDIO_MP3, BEST_VIDEO, Provider


class VkProvider(Provider):
    name = "vk"            # cookies/vk.txt подхватится автоматически
    title = "VK"
    hosts = ("vk.com", "vkvideo.ru")

    def variants(self, info: MediaInfo) -> list[Variant]:
        return [BEST_VIDEO, AUDIO_MP3]
```

```python
# app/providers/__init__.py
PROVIDERS = (YouTubeProvider(), InstagramProvider(), TikTokProvider(), VkProvider(), GenericProvider())
```

`GenericProvider` всегда последний: он матчит любой http(s) и служит fallback-ом.
Если нужна лестница качеств вместо одной кнопки — смотри `YouTubeProvider.variants`,
там высоты берутся из `info.heights`. Для нестандартных заголовков, `extractor_args`
или отдельного прокси переопредели `ydl_opts()`.

## Если бот не стартует

Первая строка лога показывает, что бот реально увидел:

```
INFO app: config: token=есть whitelist=[410585945] limit=48MB ... proxy_telegram=нет
INFO app: bot: @your_bot (id=...), начинаю polling
```

**`Не заданы переменные окружения: BOT_TOKEN`** — переменные не доехали до
контейнера. В панелях вроде Dokploy значения из вкладки Environment идут
только в интерполяцию `${...}` в compose-файле, поэтому каждая переменная
должна быть перечислена в блоке `environment:` — см. `docker-compose.yml`.

**`Нет связи с https://api.telegram.org`** — с сервера не открывается
соединение до Telegram. Проверь с самого хоста:

```bash
curl -sS -m 5 https://api.telegram.org/
```

Если висит в таймаут — исходящие соединения закрыты файрволом или хостером
(частая история у российских провайдеров). Варианты: открыть исход на
`149.154.160.0/20` и `91.108.4.0/22:443`, поднять бота на другом хостинге
или пустить Bot API через прокси:

```bash
# в переменных окружения
TG_PROXY=socks5://user:pass@host:1080
```

`TG_PROXY` касается только Telegram; `PROXY` — только yt-dlp. Если задан
один `PROXY`, он используется и для Telegram тоже. Свой Bot API server от
блокировки не спасает — ему нужен тот же доступ к Telegram.

Схемы: `socks5://`, `socks4://`, `http://`. Для yt-dlp есть ещё
`socks5h://` — резолвит домены на стороне прокси, что нужно при подменённом
DNS; для Telegram эта схема приводится к `socks5://`, там удалённый DNS
включён по умолчанию.

## Эксплуатация

Главное регулярное действие — **обновлять yt-dlp**. YouTube меняет отдачу
раз в несколько недель, и старая версия просто перестаёт качать:

```bash
make update                        # локально
docker compose build --pull bot    # в докере
```

`ALLOWED_USER_IDS` лучше не оставлять пустым: без него бот отвечает всем,
а скачивания идут с твоего IP и твоих cookies.

## Что не делает

- не качает плейлисты целиком — берёт первое видео;
- не пишет прямые эфиры;
- не хранит файлы: отправил в Telegram — удалил с диска.

## Правовая рамка

Скачивание чужого контента нарушает ToS YouTube и других сервисов, а копия
защищённого произведения без разрешения — это нарушение авторских прав.
Бот рассчитан на личное использование: свои видео, CC-контент, материалы,
где правообладатель это разрешил. Публичный сервис на этом коде — уже
история про DMCA-претензии и разговор с хостером.
