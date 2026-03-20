from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import FileStatus, JobStatus, ProcessingPreset


class CreateJobRequest(BaseModel):
    telegram_user_id: int
    telegram_chat_id: int | None = None
    source_url: str | None = None
    preset: ProcessingPreset = ProcessingPreset.DEFAULT


class JobFileResponse(BaseModel):
    relative_path: str
    status: FileStatus
    reason: str | None = None


class JobResponse(BaseModel):
    id: str
    telegram_user_id: int
    telegram_chat_id: int
    source_url: str
    preset: ProcessingPreset
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    total_files: int
    processed_files: int
    skipped_files: int
    error_message: str | None
    result_url: str | None
    files: list[JobFileResponse] = Field(default_factory=list)


class CancelJobResponse(BaseModel):
    id: str
    status: JobStatus


class HealthResponse(BaseModel):
    status: str = "ok"
