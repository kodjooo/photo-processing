# Photo Processing Service

Сервис принимает публичную ссылку Яндекс Диска на ZIP-архив с фотографиями, обрабатывает изображения, добавляет два логотипа и загружает результат обратно на Яндекс Диск. Взаимодействие с пользователем идет через Telegram-бота.

Поддерживаемые форматы внутри ZIP:
- `JPG`
- `JPEG`
- `PNG`
- `WEBP`
- `CR2`
- `ARW`

## Запуск

Проект запускается только через Docker Desktop.

```bash
cp .env.example .env
docker compose up --build
```

Основные контейнеры:
- `api` — HTTP API и healthcheck на `http://localhost:8000/health`
- `bot` — Telegram-бот
- `worker` — обработчик задач
- `postgres` — хранение задач и отчетов
- `redis` — очередь задач

## Полезные команды

```bash
docker compose up --build -d
docker compose logs -f api bot worker
docker compose down
docker compose down -v
docker compose run --rm migrate
docker compose run --rm api pytest
```

## Переменные окружения

Обязательно заполните в `.env`:
- `BOT_TOKEN`
- `YANDEX_DISK_OAUTH_TOKEN`
- `YANDEX_DISK_BASE_PATH`
- пути к логотипам `LEFT_LOGO_PATH` и `RIGHT_LOGO_PATH`, если используются не стандартные файлы внутри контейнера

## Деплой на удаленный сервер

На сервере нужен Docker Engine с поддержкой `docker compose`. Достаточно перенести проект, заполнить `.env` и выполнить:

```bash
docker compose up --build -d
```
