from app.config import get_settings


def test_settings_use_local_runtime_values(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("JOB_STORAGE_ROOT", raising=False)
    monkeypatch.delenv("LEFT_LOGO_PATH", raising=False)
    monkeypatch.delenv("RIGHT_LOGO_PATH", raising=False)
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("YANDEX_DISK_OAUTH_TOKEN", "disk")
    monkeypatch.setenv("YANDEX_DISK_BASE_PATH", "/results")
    monkeypatch.setenv("APP_RUNTIME_MODE", "local")
    monkeypatch.setenv("DOCKER_DATABASE_URL", "postgresql+asyncpg://docker")
    monkeypatch.setenv("LOCAL_DATABASE_URL", "postgresql+asyncpg://local")
    monkeypatch.setenv("DOCKER_REDIS_URL", "redis://docker")
    monkeypatch.setenv("LOCAL_REDIS_URL", "redis://local")
    monkeypatch.setenv("DOCKER_JOB_STORAGE_ROOT", "/tmp/docker-jobs")
    monkeypatch.setenv("LOCAL_JOB_STORAGE_ROOT", "tmp/local-jobs")
    monkeypatch.setenv("DOCKER_LEFT_LOGO_PATH", "/app/assets/docker-left.png")
    monkeypatch.setenv("LOCAL_LEFT_LOGO_PATH", "app/assets/local-left.png")
    monkeypatch.setenv("DOCKER_RIGHT_LOGO_PATH", "/app/assets/docker-right.png")
    monkeypatch.setenv("LOCAL_RIGHT_LOGO_PATH", "app/assets/local-right.png")
    monkeypatch.setenv("LOGO_OPACITY", "0.42")
    monkeypatch.setenv("MAX_ARCHIVE_SIZE_BYTES", "1")
    monkeypatch.setenv("MAX_ARCHIVE_FILES", "1")
    monkeypatch.setenv("MAX_IMAGE_FILES", "1")
    monkeypatch.setenv("IMAGE_PROCESSING_CONCURRENCY", "1")
    monkeypatch.setenv("WORKER_CONCURRENCY", "1")
    monkeypatch.setenv("DOWNLOAD_CHUNK_SIZE", "1")
    monkeypatch.setenv("YANDEX_UPLOAD_CHUNK_SIZE", "2")
    monkeypatch.setenv("YANDEX_UPLOAD_TIMEOUT_SECONDS", "1200")
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "8000")
    monkeypatch.setenv("APP_TIMEZONE", "Europe/Moscow")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == "postgresql+asyncpg://local"
    assert settings.redis_url == "redis://local"
    assert settings.job_storage_root == "tmp/local-jobs"
    assert settings.left_logo_path == "app/assets/local-left.png"
    assert settings.right_logo_path == "app/assets/local-right.png"
    assert settings.logo_opacity == 0.42
    assert settings.yandex_upload_chunk_size == 2
    assert settings.yandex_upload_timeout_seconds == 1200
    get_settings.cache_clear()


def test_settings_use_override_values_first(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("YANDEX_DISK_OAUTH_TOKEN", "disk")
    monkeypatch.setenv("YANDEX_DISK_BASE_PATH", "/results")
    monkeypatch.setenv("APP_RUNTIME_MODE", "docker")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://override")
    monkeypatch.setenv("REDIS_URL", "redis://override")
    monkeypatch.setenv("JOB_STORAGE_ROOT", "/override/jobs")
    monkeypatch.setenv("LEFT_LOGO_PATH", "/override/left.png")
    monkeypatch.setenv("RIGHT_LOGO_PATH", "/override/right.png")
    monkeypatch.setenv("DOCKER_DATABASE_URL", "postgresql+asyncpg://docker")
    monkeypatch.setenv("LOCAL_DATABASE_URL", "postgresql+asyncpg://local")
    monkeypatch.setenv("DOCKER_REDIS_URL", "redis://docker")
    monkeypatch.setenv("LOCAL_REDIS_URL", "redis://local")
    monkeypatch.setenv("DOCKER_JOB_STORAGE_ROOT", "/tmp/docker-jobs")
    monkeypatch.setenv("LOCAL_JOB_STORAGE_ROOT", "tmp/local-jobs")
    monkeypatch.setenv("DOCKER_LEFT_LOGO_PATH", "/app/assets/docker-left.png")
    monkeypatch.setenv("LOCAL_LEFT_LOGO_PATH", "app/assets/local-left.png")
    monkeypatch.setenv("DOCKER_RIGHT_LOGO_PATH", "/app/assets/docker-right.png")
    monkeypatch.setenv("LOCAL_RIGHT_LOGO_PATH", "app/assets/local-right.png")
    monkeypatch.setenv("LOGO_OPACITY", "0.61")
    monkeypatch.setenv("MAX_ARCHIVE_SIZE_BYTES", "1")
    monkeypatch.setenv("MAX_ARCHIVE_FILES", "1")
    monkeypatch.setenv("MAX_IMAGE_FILES", "1")
    monkeypatch.setenv("IMAGE_PROCESSING_CONCURRENCY", "1")
    monkeypatch.setenv("WORKER_CONCURRENCY", "1")
    monkeypatch.setenv("DOWNLOAD_CHUNK_SIZE", "1")
    monkeypatch.setenv("YANDEX_UPLOAD_CHUNK_SIZE", "4")
    monkeypatch.setenv("YANDEX_UPLOAD_TIMEOUT_SECONDS", "1800")
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "8000")
    monkeypatch.setenv("APP_TIMEZONE", "Europe/Moscow")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.database_url == "postgresql+asyncpg://override"
    assert settings.redis_url == "redis://override"
    assert settings.job_storage_root == "/override/jobs"
    assert settings.left_logo_path == "/override/left.png"
    assert settings.right_logo_path == "/override/right.png"
    assert settings.logo_opacity == 0.61
    assert settings.yandex_upload_chunk_size == 4
    assert settings.yandex_upload_timeout_seconds == 1800
    get_settings.cache_clear()
