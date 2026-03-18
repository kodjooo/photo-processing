from types import SimpleNamespace

from app.enums import JobStatus, ProcessingPreset
from app.services.job_manager import JobManager


def test_job_response_contains_telegram_chat_id() -> None:
    manager = JobManager.__new__(JobManager)
    job = SimpleNamespace(
        id="job-1",
        telegram_user_id=1001,
        telegram_chat_id=2002,
        source_url="https://disk.yandex.ru/d/example",
        preset=ProcessingPreset.BALANCED,
        status=JobStatus.QUEUED,
        created_at=None,
        started_at=None,
        finished_at=None,
        total_files=0,
        processed_files=0,
        skipped_files=0,
        error_message=None,
        result_url=None,
        files=[],
    )

    response = manager._to_response(job)

    assert response.telegram_user_id == 1001
    assert response.telegram_chat_id == 2002
