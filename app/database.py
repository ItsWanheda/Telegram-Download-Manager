from __future__ import annotations

import aiosqlite

from app.models import Job


class Database:
    def __init__(self, path):
        self.path = str(path)

    async def _connect(self):
        db = await aiosqlite.connect(self.path)
        db.row_factory = aiosqlite.Row

        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA synchronous=NORMAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute("PRAGMA foreign_keys=ON")

        return db

    async def initialize(self):
        async with await self._connect() as db:
            await db.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    downloaded_bytes INTEGER NOT NULL DEFAULT 0,
                    total_bytes INTEGER NOT NULL DEFAULT 0,
                    download_attempts INTEGER NOT NULL DEFAULT 0,
                    upload_attempts INTEGER NOT NULL DEFAULT 0,
                    sha256 TEXT,
                    error TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    downloaded_at TIMESTAMP,
                    uploaded_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_status
                ON jobs(status);

                CREATE INDEX IF NOT EXISTS idx_jobs_created
                ON jobs(created_at);

                CREATE INDEX IF NOT EXISTS idx_jobs_url
                ON jobs(url);

                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    total_jobs INTEGER NOT NULL DEFAULT 0,
                    completed_jobs INTEGER NOT NULL DEFAULT 0,
                    failed_jobs INTEGER NOT NULL DEFAULT 0,
                    cancelled_jobs INTEGER NOT NULL DEFAULT 0,
                    total_bytes_downloaded INTEGER NOT NULL DEFAULT 0,
                    total_bytes_uploaded INTEGER NOT NULL DEFAULT 0,
                    total_download_time REAL NOT NULL DEFAULT 0,
                    total_upload_time REAL NOT NULL DEFAULT 0,
                    total_download_attempts INTEGER NOT NULL DEFAULT 0,
                    total_upload_attempts INTEGER NOT NULL DEFAULT 0,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                INSERT OR IGNORE INTO statistics (id) VALUES (1);
                """
            )
            await db.commit()

    async def _increment_statistics(
        self,
        db,
        *,
        total_jobs=0,
        completed_jobs=0,
        failed_jobs=0,
        cancelled_jobs=0,
        total_bytes_downloaded=0,
        total_bytes_uploaded=0,
        total_download_time=0.0,
        total_upload_time=0.0,
        total_download_attempts=0,
        total_upload_attempts=0,
        retry_count=0,
    ):
        await db.execute(
            """
            UPDATE statistics
            SET
                total_jobs = total_jobs + ?,
                completed_jobs = completed_jobs + ?,
                failed_jobs = failed_jobs + ?,
                cancelled_jobs = cancelled_jobs + ?,
                total_bytes_downloaded = total_bytes_downloaded + ?,
                total_bytes_uploaded = total_bytes_uploaded + ?,
                total_download_time = total_download_time + ?,
                total_upload_time = total_upload_time + ?,
                total_download_attempts = total_download_attempts + ?,
                total_upload_attempts = total_upload_attempts + ?,
                retry_count = retry_count + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (
                total_jobs,
                completed_jobs,
                failed_jobs,
                cancelled_jobs,
                total_bytes_downloaded,
                total_bytes_uploaded,
                total_download_time,
                total_upload_time,
                total_download_attempts,
                total_upload_attempts,
                retry_count,
            ),
        )

    async def increment_statistics(self, **values):
        async with await self._connect() as db:
            await self._increment_statistics(db, **values)
            await db.commit()

    async def create_job(self, url: str, filename: str) -> int:
        async with await self._connect() as db:
            cursor = await db.execute(
                """
                INSERT INTO jobs (url, filename, status)
                VALUES (?, ?, 'queued')
                """,
                (url, filename),
            )
            await self._increment_statistics(
                db,
                total_jobs=1,
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def create_job_if_not_duplicate(
        self,
        url: str,
        filename: str,
    ) -> tuple[int | None, bool]:
        async with await self._connect() as db:
            cursor = await db.execute(
                """
                SELECT id
                FROM jobs
                WHERE url = ?
                  AND status NOT IN ('completed', 'cancelled')
                ORDER BY id DESC
                LIMIT 1
                """,
                (url,),
            )
            row = await cursor.fetchone()

            if row:
                return int(row["id"]), False

            cursor = await db.execute(
                """
                INSERT INTO jobs (url, filename, status)
                VALUES (?, ?, 'queued')
                """,
                (url, filename),
            )

            await self._increment_statistics(
                db,
                total_jobs=1,
            )
            await db.commit()

            return int(cursor.lastrowid), True

    async def update(self, job_id: int, **fields):
        if not fields:
            return

        allowed = {
            "filename",
            "status",
            "downloaded_bytes",
            "total_bytes",
            "download_attempts",
            "upload_attempts",
            "sha256",
            "error",
            "started_at",
            "downloaded_at",
            "uploaded_at",
            "completed_at",
        }

        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(
                "Unknown database fields: "
                + ", ".join(sorted(unknown))
            )

        expression_fields = {"CURRENT_TIMESTAMP"}
        sets = []
        values = []

        for key, value in fields.items():
            if isinstance(value, str) and value in expression_fields:
                sets.append(f"{key} = {value}")
            else:
                sets.append(f"{key} = ?")
                values.append(value)

        sets.append("updated_at = CURRENT_TIMESTAMP")
        values.append(job_id)

        async with await self._connect() as db:
            await db.execute(
                f"""
                UPDATE jobs
                SET {", ".join(sets)}
                WHERE id = ?
                """,
                values,
            )
            await db.commit()

    async def get(self, job_id: int) -> Job | None:
        async with await self._connect() as db:
            cursor = await db.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            )
            row = await cursor.fetchone()
            return Job.from_row(row) if row else None

    async def list_jobs(self, limit: int = 50) -> list[Job]:
        async with await self._connect() as db:
            cursor = await db.execute(
                """
                SELECT *
                FROM jobs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [Job.from_row(row) for row in rows]

    async def pending(self) -> list[Job]:
        async with await self._connect() as db:
            cursor = await db.execute(
                """
                SELECT *
                FROM jobs
                WHERE status IN ('queued', 'downloading', 'uploading')
                ORDER BY id
                """
            )
            rows = await cursor.fetchall()
            return [Job.from_row(row) for row in rows]

    async def recover_stale_jobs(self):
        async with await self._connect() as db:
            await db.execute(
                """
                UPDATE jobs
                SET
                    status = 'queued',
                    error = 'Recovered after previous process shutdown',
                    updated_at = CURRENT_TIMESTAMP
                WHERE status IN ('downloading', 'uploading')
                """
            )
            await db.commit()

    async def cancel(self, job_id: int) -> bool:
        async with await self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE jobs
                SET status = 'cancelled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND status NOT IN ('completed', 'cancelled')
                """,
                (job_id,),
            )
            changed = cursor.rowcount > 0

            if changed:
                await self._increment_statistics(
                    db,
                    cancelled_jobs=1,
                )

            await db.commit()
            return changed

    async def retry(self, job_id: int) -> bool:
        async with await self._connect() as db:
            cursor = await db.execute(
                """
                UPDATE jobs
                SET status = 'queued',
                    error = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND status IN ('failed', 'cancelled')
                """,
                (job_id,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def delete_completed(self) -> int:
        async with await self._connect() as db:
            cursor = await db.execute(
                "DELETE FROM jobs WHERE status = 'completed'"
            )
            await db.commit()
            return cursor.rowcount

    async def get_statistics(self) -> dict:
        async with await self._connect() as db:
            cursor = await db.execute(
                "SELECT * FROM statistics WHERE id = 1"
            )
            row = await cursor.fetchone()
            return dict(row) if row else {}
