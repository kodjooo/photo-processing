from datetime import datetime, timezone

import pytest

from app.enums import JobStatus, ProcessingPreset
from app.services.job_manager import JobManager


class FakeRepository:
    def __init__(self) -> None:
        self.created_source_url = None
        self.job = type(
            "Job",
            (),
            {
                "id": "job-local",
                "telegram_user_id": 1,
                "telegram_chat_id": 2,
                "source_url": "",
                "preset": ProcessingPreset.BALANCED,
                "status": JobStatus.CREATED,
                "created_at": datetime.now(timezone.utc),
                "started_at": None,
                "finished_at": None,
                "total_files": 0,
                "processed_files": 0,
                "skipped_files": 0,
                "error_message": None,
                "result_url": None,
                "files": [],
            },
        )()

    async def create_job(self, telegram_user_id: int, telegram_chat_id: int, source_url: str, preset: str):
        self.created_source_url = source_url
        self.job.telegram_user_id = telegram_user_id
        self.job.telegram_chat_id = telegram_chat_id
        self.job.source_url = source_url
        self.job.preset = preset
        return self.job

    async def set_status(self, job, status, message=None):
        job.status = status
        return job


class FakeQueue:
    def __init__(self) -> None:
        self.enqueued_job_id = None

    async def enqueue(self, job_id: str) -> None:
        self.enqueued_job_id = job_id


@pytest.mark.asyncio
async def test_create_job_uses_configured_local_archive_path(monkeypatch) -> None:
    monkeypatch.setenv("ARCHIVE_SOURCE_MODE", "local")
    monkeypatch.setenv("LOCAL_ARCHIVE_SOURCE_PATH", "local-archives/input/archive.zip")

    manager = JobManager.__new__(JobManager)
    manager.settings = type(
        "Settings",
        (),
        {
            "archive_source_mode": "local",
            "local_archive_source_path": "local-archives/input/archive.zip",
        },
    )()
    manager.repository = FakeRepository()
    manager.queue = FakeQueue()

    job = await manager.create_job(
        telegram_user_id=1,
        telegram_chat_id=2,
        source_url=None,
        preset=ProcessingPreset.BALANCED,
    )

    assert manager.repository.created_source_url == "local-archives/input/archive.zip"
    assert manager.queue.enqueued_job_id == "job-local"
    assert job.source_url == "local-archives/input/archive.zip"
