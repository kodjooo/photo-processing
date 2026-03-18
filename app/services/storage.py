import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".cr2", ".arw"}


@dataclass(slots=True)
class JobPaths:
    root: Path
    input_dir: Path
    unpacked_dir: Path
    output_dir: Path
    decode_auto_bright_dir: Path
    decode_natural_dir: Path
    result_dir: Path
    archive_path: Path
    result_archive_path: Path
    decode_auto_bright_archive_path: Path
    decode_natural_archive_path: Path


@dataclass(slots=True)
class ScanResult:
    supported_files: list[Path]
    skipped_files: list[tuple[str, str]]
    total_files: int


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def prepare_job_paths(self, job_id: str) -> JobPaths:
        root = Path(self.settings.job_storage_root) / job_id
        input_dir = root / "input"
        unpacked_dir = input_dir / "unpacked"
        output_dir = root / "output"
        decode_auto_bright_dir = root / "decoded-auto-bright"
        decode_natural_dir = root / "decoded-natural"
        result_dir = root / "result"
        input_dir.mkdir(parents=True, exist_ok=True)
        unpacked_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        decode_auto_bright_dir.mkdir(parents=True, exist_ok=True)
        decode_natural_dir.mkdir(parents=True, exist_ok=True)
        result_dir.mkdir(parents=True, exist_ok=True)
        return JobPaths(
            root=root,
            input_dir=input_dir,
            unpacked_dir=unpacked_dir,
            output_dir=output_dir,
            decode_auto_bright_dir=decode_auto_bright_dir,
            decode_natural_dir=decode_natural_dir,
            result_dir=result_dir,
            archive_path=input_dir / "archive.zip",
            result_archive_path=result_dir / "result.zip",
            decode_auto_bright_archive_path=result_dir / "decoded-auto-bright.zip",
            decode_natural_archive_path=result_dir / "decoded-natural.zip",
        )

    def unpack_archive(self, archive_path: Path, destination: Path) -> None:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                member_path = destination / member.filename
                resolved = member_path.resolve()
                if not str(resolved).startswith(str(destination.resolve())):
                    raise ValueError("Обнаружен небезопасный путь внутри архива")
                archive.extract(member, destination)

    def scan_unpacked_files(self, unpacked_dir: Path) -> ScanResult:
        supported_files: list[Path] = []
        skipped_files: list[tuple[str, str]] = []
        all_files = [path for path in unpacked_dir.rglob("*") if path.is_file()]

        if len(all_files) > self.settings.max_archive_files:
            raise ValueError("Превышено максимальное количество файлов в архиве")

        for path in all_files:
            relative_path = str(path.relative_to(unpacked_dir))
            if self._is_macos_service_file(path, unpacked_dir):
                skipped_files.append((relative_path, "Служебный файл macOS пропущен"))
                continue
            suffix = path.suffix.lower()
            if suffix in SUPPORTED_IMAGE_SUFFIXES:
                supported_files.append(path)
                continue
            skipped_files.append((relative_path, "Неподдерживаемый формат файла"))

        if len(supported_files) > self.settings.max_image_files:
            raise ValueError("Превышено максимальное количество изображений в задаче")

        return ScanResult(
            supported_files=supported_files,
            skipped_files=skipped_files,
            total_files=len(all_files),
        )

    def build_output_path(self, unpacked_dir: Path, output_dir: Path, source_path: Path) -> Path:
        relative = source_path.relative_to(unpacked_dir)
        if source_path.suffix.lower() in {".cr2", ".arw"}:
            relative = relative.with_suffix(".jpg")
        target = output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def package_result(self, output_dir: Path, result_archive_path: Path) -> None:
        with zipfile.ZipFile(result_archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in output_dir.rglob("*"):
                if file_path.is_file():
                    archive.write(file_path, file_path.relative_to(output_dir))

    def cleanup(self, job_root: Path) -> None:
        shutil.rmtree(job_root, ignore_errors=True)

    def _is_macos_service_file(self, path: Path, unpacked_dir: Path) -> bool:
        relative_parts = path.relative_to(unpacked_dir).parts
        return "__MACOSX" in relative_parts or path.name.startswith("._")
