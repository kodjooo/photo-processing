from pathlib import Path

import pytest

from app.services.local_archive import LocalArchiveService


@pytest.mark.asyncio
async def test_copy_source_archive_uses_configured_project_path(monkeypatch, tmp_path: Path) -> None:
    source_path = tmp_path / "incoming" / "archive.zip"
    source_path.parent.mkdir(parents=True)
    source_path.write_bytes(b"zip-data")
    monkeypatch.setenv("LOCAL_ARCHIVE_SOURCE_PATH", str(source_path))

    service = LocalArchiveService()
    target_path = tmp_path / "job" / "input" / "archive.zip"
    await service.copy_source_archive(target_path)

    assert target_path.read_bytes() == b"zip-data"


@pytest.mark.asyncio
async def test_store_result_copies_archive_to_project_output_dir(monkeypatch, tmp_path: Path) -> None:
    result_dir = tmp_path / "results"
    monkeypatch.setenv("LOCAL_ARCHIVE_RESULT_DIR", str(result_dir))

    service = LocalArchiveService()
    archive_path = tmp_path / "job.zip"
    archive_path.write_bytes(b"result-data")

    stored_path = await service.store_result(archive_path, "stored.zip")

    assert stored_path == str(result_dir / "stored.zip")
    assert (result_dir / "stored.zip").read_bytes() == b"result-data"
