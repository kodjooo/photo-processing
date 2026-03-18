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
    (unpacked_dir / "notes.txt").write_bytes(b"3")
    macos_dir = unpacked_dir / "__MACOSX"
    macos_dir.mkdir()
    (macos_dir / "._raw.cr2").write_bytes(b"4")

    result = storage.scan_unpacked_files(unpacked_dir)

    assert result.total_files == 4
    assert len(result.supported_files) == 2
    assert {path.name for path in result.supported_files} == {"photo.jpg", "raw.cr2"}
    assert result.skipped_files == [
        ("notes.txt", "Неподдерживаемый формат файла"),
        ("__MACOSX/._raw.cr2", "Служебный файл macOS пропущен"),
    ]


def test_build_output_path_converts_raw_extension_to_jpg(tmp_path: Path) -> None:
    storage = StorageService()
    unpacked_dir = tmp_path / "unpacked"
    output_dir = tmp_path / "output"
    unpacked_dir.mkdir()
    output_dir.mkdir()
    source_path = unpacked_dir / "nested" / "photo.arw"
    source_path.parent.mkdir()
    source_path.write_bytes(b"1")

    result_path = storage.build_output_path(unpacked_dir, output_dir, source_path)

    assert result_path.name == "photo.jpg"
    assert result_path.parent == output_dir / "nested"


def test_prepare_job_paths_contains_debug_decode_locations() -> None:
    storage = StorageService()

    paths = storage.prepare_job_paths("job-1")

    assert paths.decode_auto_bright_dir.name == "decoded-auto-bright"
    assert paths.decode_natural_dir.name == "decoded-natural"
    assert paths.decode_auto_bright_archive_path.name == "decoded-auto-bright.zip"
    assert paths.decode_natural_archive_path.name == "decoded-natural.zip"
