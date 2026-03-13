import zipfile
from pathlib import Path

import pytest

from app.services.storage import StorageService


def test_unpack_archive_blocks_path_traversal(tmp_path: Path) -> None:
    storage = StorageService()
    archive_path = tmp_path / "archive.zip"
    destination = tmp_path / "out"
    destination.mkdir()

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", "bad")

    with pytest.raises(ValueError, match="небезопасный путь"):
        storage.unpack_archive(archive_path, destination)


def test_scan_unpacked_files_collects_supported_and_skipped(tmp_path: Path) -> None:
    storage = StorageService()
    unpacked_dir = tmp_path / "unpacked"
    unpacked_dir.mkdir()
    (unpacked_dir / "photo.jpg").write_bytes(b"1")
    (unpacked_dir / "raw.cr2").write_bytes(b"2")

    result = storage.scan_unpacked_files(unpacked_dir)

    assert result.total_files == 2
    assert len(result.supported_files) == 1
    assert result.skipped_files == [("raw.cr2", "Неподдерживаемый формат файла")]
