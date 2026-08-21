from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Job:
    id: int
    url: str
    filename: str
    status: str

    downloaded_bytes: int
    total_bytes: int

    download_attempts: int
    upload_attempts: int

    sha256: str | None
    error: str | None

    created_at: str | None
    started_at: str | None
    downloaded_at: str | None
    uploaded_at: str | None
    completed_at: str | None
    updated_at: str | None

    @classmethod
    def from_row(cls, row: Any) -> "Job":
        return cls(
            id=row["id"],
            url=row["url"],
            filename=row["filename"],
            status=row["status"],
            downloaded_bytes=row["downloaded_bytes"] or 0,
            total_bytes=row["total_bytes"] or 0,
            download_attempts=row["download_attempts"] or 0,
            upload_attempts=row["upload_attempts"] or 0,
            sha256=row["sha256"],
            error=row["error"],
            created_at=row["created_at"],
            started_at=row["started_at"],
            downloaded_at=row["downloaded_at"],
            uploaded_at=row["uploaded_at"],
            completed_at=row["completed_at"],
            updated_at=row["updated_at"],
        )

    @property
    def progress(self) -> float | None:
        if self.total_bytes <= 0:
            return None

        return min(
            100.0,
            self.downloaded_bytes / self.total_bytes * 100,
        )

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "filename": self.filename,
            "status": self.status,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "download_attempts": self.download_attempts,
            "upload_attempts": self.upload_attempts,
            "sha256": self.sha256,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "downloaded_at": self.downloaded_at,
            "uploaded_at": self.uploaded_at,
            "completed_at": self.completed_at,
            "updated_at": self.updated_at,
        }
