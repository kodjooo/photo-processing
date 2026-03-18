from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_database() -> None:
    from app import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.exec_driver_sql(
            "ALTER TABLE jobs ALTER COLUMN telegram_user_id TYPE BIGINT"
        )
        await connection.exec_driver_sql(
            "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS telegram_chat_id BIGINT"
        )
        await connection.exec_driver_sql(
            "UPDATE jobs SET telegram_chat_id = telegram_user_id WHERE telegram_chat_id IS NULL"
        )
        await connection.exec_driver_sql(
            "ALTER TABLE jobs ALTER COLUMN telegram_chat_id SET NOT NULL"
        )
