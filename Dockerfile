FROM python:3.12-slim

# ffmpeg обязателен: YouTube отдаёт видео и звук отдельными потоками (DASH),
# их надо склеивать, а mp3 — перекодировать.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY app ./app
CMD ["python", "-m", "app"]
