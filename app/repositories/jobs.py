from datetime import datetime, timezone

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.enums import FileStatus, JobStatus, TERMINAL_STATUSES
from app.models import Job, JobEvent, JobFile


class JobRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, telegram_user_id: int, source_url: str, preset: str) -> Job:
        job = Job(telegram_user_id=telegram_user_id, source_url=source_url, preset=preset, status=JobStatus.CREATED)
        self.session.add(job)
        self.session.add(JobEvent(job=job, status=JobStatus.CREATED, message="Задача создана"))
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> Job | None:
        query: Select[tuple[Job]] = (
            select(Job)
            .where(Job.id == job_id)
            .options(selectinload(Job.files), selectinload(Job.events))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_last_job_by_user(self, telegram_user_id: int) -> Job | None:
        query = (
            select(Job)
            .where(Job.telegram_user_id == telegram_user_id)
            .order_by(desc(Job.created_at))
            .options(selectinload(Job.files))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def set_status(self, job: Job, status: JobStatus, message: str | None = None) -> Job:
        job.status = status
        if status == JobStatus.DOWNLOADING and job.started_at is None:
            job.started_at = datetime.now(timezone.utc)
        if status in TERMINAL_STATUSES:
            job.finished_at = datetime.now(timezone.utc)
        self.session.add(JobEvent(job_id=job.id, status=status, message=message))
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def add_event(self, job_id: str, status: JobStatus, message: str) -> None:
        self.session.add(JobEvent(job_id=job_id, status=status, message=message))
        await self.session.commit()

    async def request_cancel(self, job: Job) -> Job:
        if job.status in TERMINAL_STATUSES:
            return job
        job.status = JobStatus.CANCELLED
        job.finished_at = datetime.now(timezone.utc)
        self.session.add(JobEvent(job_id=job.id, status=JobStatus.CANCELLED, message="Отменено пользователем"))
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def replace_files(self, job: Job, file_entries: list[tuple[str, FileStatus, str | None]]) -> None:
        await self.session.execute(JobFile.__table__.delete().where(JobFile.job_id == job.id))
        for relative_path, status, reason in file_entries:
            self.session.add(JobFile(job_id=job.id, relative_path=relative_path, status=status, reason=reason))
        await self.session.commit()

    async def update_counters(
        self,
        job: Job,
        *,
        total_files: int | None = None,
        processed_files: int | None = None,
        skipped_files: int | None = None,
        result_url: str | None = None,
        error_message: str | None = None,
    ) -> Job:
        if total_files is not None:
            job.total_files = total_files
        if processed_files is not None:
            job.processed_files = processed_files
        if skipped_files is not None:
            job.skipped_files = skipped_files
        if result_url is not None:
            job.result_url = result_url
        if error_message is not None:
            job.error_message = error_message
        await self.session.commit()
        await self.session.refresh(job)
        return job
