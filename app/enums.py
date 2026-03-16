from enum import StrEnum


class JobStatus(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    UNPACKING = "unpacking"
    PROCESSING = "processing"
    PACKAGING = "packaging"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileStatus(StrEnum):
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"


class ProcessingPreset(StrEnum):
    DEFAULT = "default"
    NATURAL = "natural"
    BALANCED = "balanced"
    STRONG = "strong"


TERMINAL_STATUSES = {
    JobStatus.COMPLETED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
}
