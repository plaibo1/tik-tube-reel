from __future__ import annotations


class GrabberError(Exception):
    """Ошибка, текст которой можно показать пользователю как есть."""


class UnsupportedLink(GrabberError):
    pass


class TooLarge(GrabberError):
    pass


class TooLong(GrabberError):
    pass


class NeedsAuth(GrabberError):
    pass
