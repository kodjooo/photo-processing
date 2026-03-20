from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.enums import JobStatus
from app.repositories.jobs import JobRepository
from app.schemas import JobResponse
from app.services.queue import QueueService
from app.services.validators import validate_yandex_public_url


class JobManager:
    def __init__(self, session: AsyncSession):
        self.settings = get_settings()
        self.repository = JobRepository(session)
        self.queue = QueueService()

    async def create_job(
        self,
        telegram_user_id: int,
        telegram_chat_id: int,
        source_url: str | None,
        preset: str,
    ) -> JobResponse:
        source_reference = self._resolve_source_reference(source_url)
        job = await self.repository.create_job(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            source_url=source_reference,
            preset=preset,
        )
        job = await self.repository.set_status(job, JobStatus.VALIDATING, "Ссылка принята в обработку")
        job = await self.repository.set_status(job, JobStatus.QUEUED, "Задача поставлена в очередь")
        await self.queue.enqueue(job.id)
        return self._to_response(job)

    def _resolve_source_reference(self, source_url: str | None) -> str:
        if self.settings.archive_source_mode == "local":
            return self.settings.local_archive_source_path

        normalized_source = (source_url or "").strip()
        if not normalized_source:
            raise ValueError("Нужна публичная ссылка Яндекс Диска")
        validate_yandex_public_url(normalized_source)
        return normalized_source

    async def get_job(self, job_id: str) -> JobResponse | None:
        job = await self.repository.get_job(job_id)
        if job is None:
            return None
        return self._to_response(job)

    async def cancel_job(self, job_id: str) -> JobResponse | None:
        job = await self.repository.get_job(job_id)
        if job is None:
            return None
        job = await self.repository.request_cancel(job)
        return self._to_response(job)

    async def get_last_job(self, telegram_user_id: int) -> JobResponse | None:
        job = await self.repository.get_last_job_by_user(telegram_user_id)
        if job is None:
            return None
        return self._to_response(job)

    def _to_response(self, job) -> JobResponse:
        loaded_files = job.__dict__.get("files", [])
        return JobResponse(
            id=job.id,
            telegram_user_id=job.telegram_user_id,
            telegram_chat_id=job.telegram_chat_id,
            source_url=job.source_url,
            preset=job.preset,
            status=job.status,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            total_files=job.total_files,
            processed_files=job.processed_files,
            skipped_files=job.skipped_files,
            error_message=job.error_message,
            result_url=job.result_url,
            files=[
                {
                    "relative_path": item.relative_path,
                    "status": item.status,
                    "reason": item.reason,
                }
                for item in loaded_files
            ],
        )
