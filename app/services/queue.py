import logging

from redis.asyncio import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)

    async def enqueue(self, job_id: str) -> None:
        await self.redis.lpush(self.settings.redis_queue_name, job_id)

    async def dequeue(self, timeout: int = 5) -> str | None:
        item = await self.redis.brpop(self.settings.redis_queue_name, timeout=timeout)
        if item is None:
            return None
        _, job_id = item
        return job_id

    async def close(self) -> None:
        await self.redis.close()

