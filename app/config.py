from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    yandex_disk_oauth_token: str = Field(alias="YANDEX_DISK_OAUTH_TOKEN")
    yandex_disk_base_path: str = Field(alias="YANDEX_DISK_BASE_PATH")

    runtime_mode: str = Field(alias="APP_RUNTIME_MODE", default="docker")

    database_url_override: str | None = Field(alias="DATABASE_URL", default=None)
    redis_url_override: str | None = Field(alias="REDIS_URL", default=None)
    job_storage_root_override: str | None = Field(alias="JOB_STORAGE_ROOT", default=None)
    left_logo_path_override: str | None = Field(alias="LEFT_LOGO_PATH", default=None)
    right_logo_path_override: str | None = Field(alias="RIGHT_LOGO_PATH", default=None)

    docker_database_url: str = Field(
        alias="DOCKER_DATABASE_URL",
        default="postgresql+asyncpg://photo_user:photo_password@postgres:5432/photo_processing",
    )
    local_database_url: str = Field(
        alias="LOCAL_DATABASE_URL",
        default="postgresql+asyncpg://photo_user:photo_password@127.0.0.1:5432/photo_processing",
    )
    docker_redis_url: str = Field(alias="DOCKER_REDIS_URL", default="redis://redis:6379/0")
    local_redis_url: str = Field(alias="LOCAL_REDIS_URL", default="redis://127.0.0.1:6379/0")
    docker_job_storage_root: str = Field(alias="DOCKER_JOB_STORAGE_ROOT", default="/tmp/jobs")
    local_job_storage_root: str = Field(alias="LOCAL_JOB_STORAGE_ROOT", default="tmp/jobs-local")
    docker_left_logo_path: str = Field(alias="DOCKER_LEFT_LOGO_PATH", default="/app/assets/logo-left.png")
    local_left_logo_path: str = Field(alias="LOCAL_LEFT_LOGO_PATH", default="app/assets/logo-left.png")
    docker_right_logo_path: str = Field(alias="DOCKER_RIGHT_LOGO_PATH", default="/app/assets/logo-right.png")
    local_right_logo_path: str = Field(alias="LOCAL_RIGHT_LOGO_PATH", default="app/assets/logo-right.png")
    logo_opacity: float = Field(alias="LOGO_OPACITY", default=0.55)

    max_archive_size_bytes: int = Field(alias="MAX_ARCHIVE_SIZE_BYTES")
    max_archive_files: int = Field(alias="MAX_ARCHIVE_FILES")
    max_image_files: int = Field(alias="MAX_IMAGE_FILES")
    image_processing_concurrency: int = Field(alias="IMAGE_PROCESSING_CONCURRENCY")
    worker_concurrency: int = Field(alias="WORKER_CONCURRENCY")
    download_chunk_size: int = Field(alias="DOWNLOAD_CHUNK_SIZE")
    yandex_upload_chunk_size: int = Field(alias="YANDEX_UPLOAD_CHUNK_SIZE", default=8 * 1024 * 1024)
    yandex_upload_timeout_seconds: float = Field(alias="YANDEX_UPLOAD_TIMEOUT_SECONDS", default=3600.0)
    yandex_upload_max_attempts: int = Field(alias="YANDEX_UPLOAD_MAX_ATTEMPTS", default=3)
    yandex_upload_retry_delay_seconds: float = Field(
        alias="YANDEX_UPLOAD_RETRY_DELAY_SECONDS",
        default=5.0,
    )
    api_host: str = Field(alias="API_HOST")
    api_port: int = Field(alias="API_PORT")
    app_timezone: str = Field(alias="APP_TIMEZONE")
    decode_debug_exports_enabled: bool = Field(alias="DECODE_DEBUG_EXPORTS_ENABLED", default=False)

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        if self.runtime_mode == "local":
            return self.local_database_url
        return self.docker_database_url

    @property
    def redis_url(self) -> str:
        if self.redis_url_override:
            return self.redis_url_override
        if self.runtime_mode == "local":
            return self.local_redis_url
        return self.docker_redis_url

    @property
    def job_storage_root(self) -> str:
        if self.job_storage_root_override:
            return self.job_storage_root_override
        if self.runtime_mode == "local":
            return self.local_job_storage_root
        return self.docker_job_storage_root

    @property
    def left_logo_path(self) -> str:
        if self.left_logo_path_override:
            return self.left_logo_path_override
        if self.runtime_mode == "local":
            return self.local_left_logo_path
        return self.docker_left_logo_path

    @property
    def right_logo_path(self) -> str:
        if self.right_logo_path_override:
            return self.right_logo_path_override
        if self.runtime_mode == "local":
            return self.local_right_logo_path
        return self.docker_right_logo_path

    @property
    def redis_queue_name(self) -> str:
        return "photo_processing:jobs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
