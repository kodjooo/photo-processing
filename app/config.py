from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    yandex_disk_oauth_token: str = Field(alias="YANDEX_DISK_OAUTH_TOKEN")
    yandex_disk_base_path: str = Field(alias="YANDEX_DISK_BASE_PATH")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")
    job_storage_root: str = Field(alias="JOB_STORAGE_ROOT")
    left_logo_path: str = Field(alias="LEFT_LOGO_PATH")
    right_logo_path: str = Field(alias="RIGHT_LOGO_PATH")
    max_archive_size_bytes: int = Field(alias="MAX_ARCHIVE_SIZE_BYTES")
    max_archive_files: int = Field(alias="MAX_ARCHIVE_FILES")
    max_image_files: int = Field(alias="MAX_IMAGE_FILES")
    image_processing_concurrency: int = Field(alias="IMAGE_PROCESSING_CONCURRENCY")
    worker_concurrency: int = Field(alias="WORKER_CONCURRENCY")
    download_chunk_size: int = Field(alias="DOWNLOAD_CHUNK_SIZE")
    api_host: str = Field(alias="API_HOST")
    api_port: int = Field(alias="API_PORT")
    app_timezone: str = Field(alias="APP_TIMEZONE")
    decode_debug_exports_enabled: bool = Field(alias="DECODE_DEBUG_EXPORTS_ENABLED", default=False)

    @property
    def redis_queue_name(self) -> str:
        return "photo_processing:jobs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
