import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError

from app.config import get_settings
from app.db import SessionLocal
from app.enums import FileStatus, JobStatus
from app.processing.images import ImageProcessor
from app.repositories.jobs import JobRepository
from app.services.notifications import NotificationService
from app.services.storage import StorageService
from app.services.yandex_disk import YandexDiskService

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessedFile:
    relative_path: str
    status: FileStatus
    reason: str | None = None


@dataclass(slots=True)
class DebugArchive:
    label: str
    remote_name: str
    public_url: str


class JobProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = StorageService()
        self.disk = YandexDiskService()
        self.images = ImageProcessor()
        self.notifications = NotificationService()

    async def process_job(self, job_id: str) -> None:
        async with SessionLocal() as session:
            repository = JobRepository(session)
            job = await repository.get_job(job_id)
            if job is None:
                logger.warning("Задача %s не найдена", job_id)
                return
            if job.status == JobStatus.CANCELLED:
                logger.info("Задача %s уже отменена", job_id)
                return

            paths = self.storage.prepare_job_paths(job_id)
            processed_entries: list[ProcessedFile] = []
            try:
                await repository.set_status(job, JobStatus.DOWNLOADING, "Скачивание архива")
                await self._ensure_not_cancelled(repository, job.id)
                await self._download_archive(job.source_url, paths.archive_path)
                self._validate_archive_size(paths.archive_path)

                await repository.set_status(job, JobStatus.UNPACKING, "Распаковка архива")
                await self._ensure_not_cancelled(repository, job.id)
                self.storage.unpack_archive(paths.archive_path, paths.unpacked_dir)
                scan_result = self.storage.scan_unpacked_files(paths.unpacked_dir)
                processed_entries.extend(
                    ProcessedFile(relative_path=relative_path, status=FileStatus.SKIPPED, reason=reason)
                    for relative_path, reason in scan_result.skipped_files
                )
                await repository.update_counters(job, total_files=scan_result.total_files)

                await repository.set_status(job, JobStatus.PROCESSING, "Обработка изображений")
                processed_entries.extend(
                    await self._process_images(
                        repository=repository,
                        job_id=job.id,
                        source_paths=scan_result.supported_files,
                        unpacked_dir=paths.unpacked_dir,
                        output_dir=paths.output_dir,
                        preset=job.preset,
                    )
                )

                processed_count = sum(1 for entry in processed_entries if entry.status == FileStatus.PROCESSED)
                skipped_count = sum(1 for entry in processed_entries if entry.status != FileStatus.PROCESSED)
                await repository.replace_files(
                    job,
                    [(entry.relative_path, entry.status, entry.reason) for entry in processed_entries],
                )
                await repository.update_counters(
                    job,
                    total_files=scan_result.total_files,
                    processed_files=processed_count,
                    skipped_files=skipped_count,
                )

                await repository.set_status(job, JobStatus.PACKAGING, "Упаковка результата")
                await self._ensure_not_cancelled(repository, job.id)
                self.storage.package_result(paths.output_dir, paths.result_archive_path)
                debug_archives: list[DebugArchive] = []
                if self.settings.decode_debug_exports_enabled:
                    debug_archives = await self._build_debug_decode_archives(
                        repository=repository,
                        job_id=job.id,
                        source_paths=scan_result.supported_files,
                        unpacked_dir=paths.unpacked_dir,
                        paths=paths,
                    )

                await repository.set_status(job, JobStatus.UPLOADING, "Загрузка результата на Яндекс Диск")
                await self._ensure_not_cancelled(repository, job.id)
                result_url = await self.disk.upload_result(paths.result_archive_path, f"{job.id}.zip")
                for archive in debug_archives:
                    archive.public_url = await self.disk.upload_result(
                        paths.result_dir / archive.remote_name,
                        archive.remote_name,
                    )
                await repository.update_counters(job, result_url=result_url)
                await repository.set_status(job, JobStatus.COMPLETED, "Обработка завершена")
                for archive in debug_archives:
                    await repository.add_event(
                        job_id=job.id,
                        status=JobStatus.COMPLETED,
                        message=f"Тестовый архив {archive.label}: {archive.public_url}",
                    )
                await self._notify_completed(
                    telegram_chat_id=job.telegram_chat_id,
                    job_id=job.id,
                    result_url=result_url,
                    processed_files=processed_count,
                    skipped_files=skipped_count,
                    debug_archives=debug_archives,
                )
            except asyncio.CancelledError:
                logger.info("Задача %s отменена во время выполнения", job_id)
                await repository.set_status(job, JobStatus.CANCELLED, "Задача отменена во время выполнения")
            except Exception as error:
                logger.exception("Ошибка обработки задачи %s", job_id)
                await repository.update_counters(job, error_message=str(error))
                await repository.set_status(job, JobStatus.FAILED, "Ошибка обработки")
                await self._notify_failed(
                    telegram_chat_id=job.telegram_chat_id,
                    job_id=job.id,
                    error_message=str(error),
                )
            finally:
                self.storage.cleanup(paths.root)

    async def close(self) -> None:
        await self.notifications.close()

    async def _notify_completed(
        self,
        *,
        telegram_chat_id: int,
        job_id: str,
        result_url: str,
        processed_files: int,
        skipped_files: int,
        debug_archives: list[DebugArchive],
    ) -> None:
        try:
            await self.notifications.send_job_completed(
                telegram_chat_id=telegram_chat_id,
                job_id=job_id,
                result_url=result_url,
                processed_files=processed_files,
                skipped_files=skipped_files,
                debug_archives=debug_archives,
            )
        except TelegramForbiddenError:
            logger.warning("Не удалось отправить уведомление по задаче %s: чат недоступен для бота", job_id)
        except TelegramAPIError:
            logger.exception("Ошибка Telegram API при отправке уведомления по задаче %s", job_id)

    async def _notify_failed(
        self,
        *,
        telegram_chat_id: int,
        job_id: str,
        error_message: str,
    ) -> None:
        try:
            await self.notifications.send_job_failed(
                telegram_chat_id=telegram_chat_id,
                job_id=job_id,
                error_message=error_message,
            )
        except TelegramForbiddenError:
            logger.warning("Не удалось отправить ошибку по задаче %s: чат недоступен для бота", job_id)
        except TelegramAPIError:
            logger.exception("Ошибка Telegram API при отправке ошибки по задаче %s", job_id)

    async def _download_archive(self, source_url: str, target_path: Path) -> None:
        resource_info = await self.disk.get_public_resource_info(source_url)
        if resource_info.get("type") != "file":
            raise ValueError("По ссылке должен быть доступен файл")
        if resource_info.get("file") is None and resource_info.get("mime_type") != "application/zip":
            raise ValueError("По ссылке должен быть ZIP-архив")
        size = resource_info.get("size")
        if size and int(size) > self.settings.max_archive_size_bytes:
            raise ValueError("Размер архива превышает лимит 5 ГБ")
        download_url = await self.disk.get_public_download_url(source_url)
        await self.disk.stream_download_to_file(download_url, target_path)

    def _validate_archive_size(self, archive_path: Path) -> None:
        size = archive_path.stat().st_size
        if size > self.settings.max_archive_size_bytes:
            raise ValueError("Размер скачанного архива превышает лимит 5 ГБ")

    async def _process_images(
        self,
        *,
        repository: JobRepository,
        job_id: str,
        source_paths: list[Path],
        unpacked_dir: Path,
        output_dir: Path,
        preset,
    ) -> list[ProcessedFile]:
        semaphore = asyncio.Semaphore(self.settings.image_processing_concurrency)
        results: list[ProcessedFile] = []

        for index, source_path in enumerate(source_paths, start=1):
            await self._ensure_not_cancelled(repository, job_id)
            result = await self._process_single_file(
                semaphore=semaphore,
                source_path=source_path,
                unpacked_dir=unpacked_dir,
                output_dir=output_dir,
                preset=preset,
            )
            results.append(result)
            await repository.add_event(
                job_id=job_id,
                status=JobStatus.PROCESSING,
                message=f"Прогресс обработки: {index}/{len(source_paths)}",
            )

        return results

    async def _build_debug_decode_archives(
        self,
        *,
        repository: JobRepository,
        job_id: str,
        source_paths: list[Path],
        unpacked_dir: Path,
        paths,
    ) -> list[DebugArchive]:
        await repository.add_event(
            job_id=job_id,
            status=JobStatus.PACKAGING,
            message="Тестовый режим: подготовка архивов декодирования RAW",
        )
        for source_path in source_paths:
            await asyncio.to_thread(
                self.images.export_decoded_image,
                source_path,
                self.storage.build_output_path(unpacked_dir, paths.decode_auto_bright_dir, source_path),
                raw_auto_bright=True,
            )
            await asyncio.to_thread(
                self.images.export_decoded_image,
                source_path,
                self.storage.build_output_path(unpacked_dir, paths.decode_natural_dir, source_path),
                raw_auto_bright=False,
            )

        self.storage.package_result(paths.decode_auto_bright_dir, paths.decode_auto_bright_archive_path)
        self.storage.package_result(paths.decode_natural_dir, paths.decode_natural_archive_path)

        return [
            DebugArchive(
                label="декодирование с автоосветлением",
                remote_name=f"{job_id}-decoded-auto-bright.zip",
                public_url="",
            ),
            DebugArchive(
                label="декодирование без автоосветления",
                remote_name=f"{job_id}-decoded-natural.zip",
                public_url="",
            ),
        ]

    async def _process_single_file(
        self,
        *,
        semaphore: asyncio.Semaphore,
        source_path: Path,
        unpacked_dir: Path,
        output_dir: Path,
        preset,
    ) -> ProcessedFile:
        relative_path = str(source_path.relative_to(unpacked_dir))
        async with semaphore:
            try:
                target_path = self.storage.build_output_path(unpacked_dir, output_dir, source_path)
                await asyncio.to_thread(
                    self.images.process_image,
                    source_path,
                    target_path,
                    preset=preset,
                    left_logo_path=self.settings.left_logo_path,
                    right_logo_path=self.settings.right_logo_path,
                )
                return ProcessedFile(relative_path=relative_path, status=FileStatus.PROCESSED)
            except Exception as error:
                return ProcessedFile(relative_path=relative_path, status=FileStatus.FAILED, reason=str(error))

    async def _ensure_not_cancelled(self, repository: JobRepository, job_id: str) -> None:
        current_job = await repository.get_job(job_id)
        if current_job is not None and current_job.status == JobStatus.CANCELLED:
            raise asyncio.CancelledError()
