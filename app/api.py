from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.logging import configure_logging
from app.schemas import CancelJobResponse, CreateJobRequest, HealthResponse, JobResponse
from app.services.job_manager import JobManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.settings = get_settings()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Photo Processing Service", lifespan=lifespan)

    @app.get("/health", response_model=HealthResponse)
    async def healthcheck() -> HealthResponse:
        return HealthResponse()

    @app.post("/jobs", response_model=JobResponse)
    async def create_job(
        payload: CreateJobRequest,
        session: AsyncSession = Depends(get_session),
    ) -> JobResponse:
        manager = JobManager(session)
        try:
            return await manager.create_job(
                telegram_user_id=payload.telegram_user_id,
                telegram_chat_id=payload.telegram_chat_id or payload.telegram_user_id,
                source_url=payload.source_url,
                preset=payload.preset,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get("/jobs/{job_id}", response_model=JobResponse)
    async def get_job(job_id: str, session: AsyncSession = Depends(get_session)) -> JobResponse:
        manager = JobManager(session)
        job = await manager.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        return job

    @app.post("/jobs/{job_id}/cancel", response_model=CancelJobResponse)
    async def cancel_job(job_id: str, session: AsyncSession = Depends(get_session)) -> CancelJobResponse:
        manager = JobManager(session)
        job = await manager.cancel_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        return CancelJobResponse(id=job.id, status=job.status)

    @app.get("/users/{telegram_user_id}/jobs/last", response_model=JobResponse)
    async def get_last_job(telegram_user_id: int, session: AsyncSession = Depends(get_session)) -> JobResponse:
        manager = JobManager(session)
        job = await manager.get_last_job(telegram_user_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Задачи пользователя не найдены")
        return job

    return app
