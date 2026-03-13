import pytest


@pytest.fixture(autouse=True)
def set_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("YANDEX_DISK_OAUTH_TOKEN", "token")
    monkeypatch.setenv("YANDEX_DISK_BASE_PATH", "/tmp")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("JOB_STORAGE_ROOT", str(tmp_path / "jobs"))
    monkeypatch.setenv("LEFT_LOGO_PATH", str(tmp_path / "left.png"))
    monkeypatch.setenv("RIGHT_LOGO_PATH", str(tmp_path / "right.png"))
    monkeypatch.setenv("MAX_ARCHIVE_SIZE_BYTES", "5368709120")
    monkeypatch.setenv("MAX_ARCHIVE_FILES", "300")
    monkeypatch.setenv("MAX_IMAGE_FILES", "200")
    monkeypatch.setenv("IMAGE_PROCESSING_CONCURRENCY", "2")
    monkeypatch.setenv("WORKER_CONCURRENCY", "1")
    monkeypatch.setenv("DOWNLOAD_CHUNK_SIZE", "1024")
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.setenv("API_PORT", "8000")
    monkeypatch.setenv("APP_TIMEZONE", "Europe/Moscow")

    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

