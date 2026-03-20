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

Проект поддерживает два режима запуска, которые переключаются через `APP_RUNTIME_MODE` в `.env`:

- `docker` — приложение и инфраструктура работают в контейнерах;
- `local` — `api`, `bot` и `worker` запускаются из локального Python-окружения.

### Docker-режим

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

### Local-режим

В `.env` нужно установить:

```env
APP_RUNTIME_MODE=local
```

Локальный режим использует значения `LOCAL_DATABASE_URL`, `LOCAL_REDIS_URL`, `LOCAL_JOB_STORAGE_ROOT`, `LOCAL_LEFT_LOGO_PATH`, `LOCAL_RIGHT_LOGO_PATH`.

Если PostgreSQL и Redis вы хотите оставить в Docker, можно поднять только инфраструктуру:

```bash
docker compose up -d postgres redis
```

После этого запускать приложение локально:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main init-db
python -m app.main api
python -m app.main bot
python -m app.main worker
```

## Полезные команды

```bash
docker compose up --build -d
docker compose logs -f api bot worker
docker compose down
docker compose down -v
docker compose run --rm migrate
docker compose run --rm api pytest
```

Для локального режима:

```bash
source .venv/bin/activate
python -m pytest -q
```

## Переменные окружения

Обязательно заполните в `.env`:
- `BOT_TOKEN`
- `YANDEX_DISK_OAUTH_TOKEN`
- `YANDEX_DISK_BASE_PATH`
- `APP_RUNTIME_MODE`
- значения `DOCKER_*` и `LOCAL_*` для нужного режима
- `YANDEX_UPLOAD_CHUNK_SIZE` и `YANDEX_UPLOAD_TIMEOUT_SECONDS`, если для больших архивов нужно увеличить размер чанка или длительность одной попытки загрузки
- при необходимости override-переменные `DATABASE_URL`, `REDIS_URL`, `JOB_STORAGE_ROOT`, `LEFT_LOGO_PATH`, `RIGHT_LOGO_PATH`

## Развертывание на удаленном сервере из Git

Ниже схема для Linux-сервера, где проект поднимается напрямую из репозитория Git и работает только через Docker.

### 1. Подготовить сервер

На сервере должны быть установлены:
- `git`
- Docker Engine
- Docker Compose plugin

Проверка:

```bash
git --version
docker --version
docker compose version
```

Если Docker еще не установлен, ставьте его по официальной инструкции для вашей ОС.

### 2. Подключиться к серверу и забрать проект

```bash
ssh <user>@<server-ip>
cd /opt
git clone https://github.com/kodjooo/photo-processing.git
cd photo-processing
git checkout main
```

Если репозиторий уже был склонирован ранее, обновление делается так:

```bash
cd /opt/photo-processing
git fetch origin
git checkout main
git pull origin main
```

### 3. Подготовить `.env`

Создайте локальный конфиг на сервере:

```bash
cp .env.example .env
```

После этого заполните `.env`:
- `BOT_TOKEN` — токен Telegram-бота от BotFather
- `YANDEX_DISK_OAUTH_TOKEN` — OAuth-токен Яндекс Диска с правом загрузки файлов
- `YANDEX_DISK_BASE_PATH` — путь папки на Яндекс Диске, куда загружается результат
- `LEFT_LOGO_PATH` и `RIGHT_LOGO_PATH` — пути к логотипам внутри контейнера

По умолчанию проект ожидает логотипы по путям:

```env
LEFT_LOGO_PATH=/app/assets/logo-left.png
RIGHT_LOGO_PATH=/app/assets/logo-right.png
```

Если вы используете свои логотипы, положите их в `app/assets/` до сборки образа.

### 4. Собрать и запустить проект

```bash
docker compose up -d --build
```

После запуска будут подняты контейнеры:
- `api`
- `bot`
- `worker`
- `postgres`
- `redis`

### 5. Проверить состояние после запуска

```bash
docker compose ps
docker compose logs -f api bot worker
curl http://localhost:8000/health
```

Ожидаемый ответ healthcheck:

```json
{"status":"ok"}
```

### 6. Обновление проекта на сервере

Когда в репозитории появились новые изменения:

```bash
cd /opt/photo-processing
git fetch origin
git checkout main
git pull origin main
docker compose up -d --build
```

### 7. Полезные команды для эксплуатации

Запуск и пересборка:

```bash
docker compose up -d --build
```

Остановка:

```bash
docker compose down
```

Просмотр логов:

```bash
docker compose logs -f api bot worker
```

Перезапуск только бота:

```bash
docker compose up -d --build bot
```

Запуск тестов внутри контейнера:

```bash
docker compose run --rm api pytest -q
```

### 8. Что важно не делать

- Не коммитьте `.env` в Git.
- Не храните реальные токены в репозитории.
- Если токены уже использовались в логах или тестах, перевыпустите их.
