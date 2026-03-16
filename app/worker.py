import asyncio
import logging

from app.config import get_settings
from app.logging import configure_logging
from app.services.job_processor import JobProcessor
from app.services.queue import QueueService

logger = logging.getLogger(__name__)


async def run_worker() -> None:
    configure_logging()
    settings = get_settings()
    queue = QueueService()
    processor = JobProcessor()
    semaphore = asyncio.Semaphore(settings.worker_concurrency)
    logger.info("Worker запущен")
    try:
        while True:
            job_id = await queue.dequeue(timeout=5)
            if job_id is None:
                await asyncio.sleep(1)
                continue
            logger.info("Получена задача %s", job_id)
            async with semaphore:
                await processor.process_job(job_id)
    finally:
        await processor.close()
        await queue.close()
