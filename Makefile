.PHONY: install run lint update

install:
	uv sync

run:
	uv run python -m app

lint:
	uv run ruff check app
	uv run ruff format --check app

# Главная регулярная операция: свежий yt-dlp.
update:
	uv lock --upgrade-package yt-dlp && uv sync
