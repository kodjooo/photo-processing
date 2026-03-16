from aiogram import Bot

from app.config import get_settings


class NotificationService:
    def __init__(self) -> None:
        settings = get_settings()
        self.bot = Bot(settings.bot_token)

    async def send_job_completed(
        self,
        *,
        telegram_user_id: int,
        job_id: str,
        result_url: str,
        processed_files: int,
        skipped_files: int,
    ) -> None:
        text = (
            f"Задача завершена: {job_id}\n"
            f"Обработано: {processed_files}\n"
            f"Пропущено: {skipped_files}\n"
            f"Результат: {result_url}"
        )
        await self.bot.send_message(chat_id=telegram_user_id, text=text)

    async def send_job_failed(
        self,
        *,
        telegram_user_id: int,
        job_id: str,
        error_message: str,
    ) -> None:
        text = (
            f"Задача завершилась с ошибкой: {job_id}\n"
            f"Причина: {error_message}"
        )
        await self.bot.send_message(chat_id=telegram_user_id, text=text)

    async def close(self) -> None:
        await self.bot.session.close()

