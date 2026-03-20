import asyncio
import shutil
from pathlib import Path

from app.config import get_settings


class LocalArchiveService:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def copy_source_archive(self, target_path: Path) -> None:
        source_path = self._resolve_source_archive_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copyfile, source_path, target_path)

    async def store_result(self, local_path: Path, target_name: str) -> str:
        if not local_path.exists() or not local_path.is_file():
            raise ValueError("Файл результата для локального сохранения не найден")
        target_dir = Path(self.settings.local_archive_result_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / target_name
        await asyncio.to_thread(shutil.copyfile, local_path, target_path)
        return str(target_path)

    def _resolve_source_archive_path(self) -> Path:
        source_path = Path(self.settings.local_archive_source_path)
        if not source_path.exists():
            raise ValueError(f"Локальный архив не найден: {source_path}")
        if not source_path.is_file():
            raise ValueError(f"Локальный путь к архиву должен указывать на файл: {source_path}")
        if source_path.suffix.lower() != ".zip":
            raise ValueError("Локальный исходный файл должен быть ZIP-архивом")
        return source_path
