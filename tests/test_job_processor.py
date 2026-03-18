from pathlib import Path

from app.services.job_processor import DebugArchive


def test_debug_archive_keeps_separate_local_and_remote_names(tmp_path: Path) -> None:
    local_path = tmp_path / "decoded-auto-bright.zip"
    archive = DebugArchive(
        label="debug",
        local_path=local_path,
        remote_name="job-1-decoded-auto-bright.zip",
        public_url="",
    )

    assert archive.local_path.name == "decoded-auto-bright.zip"
    assert archive.remote_name == "job-1-decoded-auto-bright.zip"
