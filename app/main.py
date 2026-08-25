from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
import time

from app.config import load_config
from app.database import Database
from app.downloader import (
    DownloadError,
    MultiPartDownloader,
)
from app.telegram import TelegramUploader
from app.utils import (
    format_bytes,
    format_duration,
    sanitize_filename,
)

logger = logging.getLogger("download_manager")


def configure_logging(config):
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            config.log_file,
            encoding="utf-8",
        ),
    ]

    logging.basicConfig(
        level=getattr(
            logging,
            config.log_level,
            logging.INFO,
        ),
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        handlers=handlers,
    )


class Application:
    def __init__(self):
        self.config = load_config()
        configure_logging(self.config)

        self.db = Database(
            self.config.db_path
        )

        self.downloader = MultiPartDownloader(
            self.config.download_dir,
            self.config.part_size,
            self.config.part_workers,
            self.config.chunk_size,
            self.config.max_retries,
            self.config.request_timeout,
            resume=self.config.resume_downloads,
            allow_private_hosts=(
                self.config.allow_private_hosts
            ),
            min_free_disk_space=(
                self.config.min_free_disk_space
            ),
            max_file_size=(
                self.config.max_file_size
            ),
            retry_callback=self._record_retry,
        )

        self.uploader = TelegramUploader(
            self.config.telegram_bot_token,
            self.config.telegram_chat_id,
            self.config.max_retries,
            self.config.upload_timeout,
            retry_callback=self._record_retry,
        )

        self.stop_event = asyncio.Event()

    async def _record_retry(self):
        await self.db.increment_statistics(
            retry_count=1
        )

    async def start(self):
        await self.db.initialize()

        if self.config.recover_stale_jobs:
            await self.db.recover_stale_jobs()

        await self.downloader.start()
        await self.uploader.start()

    async def close(self):
        await self.downloader.close()
        await self.uploader.close()

    def request_shutdown(self):
        if not self.stop_event.is_set():
            logger.warning(
                "Shutdown requested."
            )
            self.stop_event.set()

    async def run_job(
        self,
        job_id: int,
        url: str,
        filename: str,
    ):
        job = await self.db.get(job_id)

        if not job:
            logger.error(
                "Job %s no longer exists.",
                job_id,
            )
            return

        downloaded = job.downloaded_bytes
        last_report = downloaded
        total = job.total_bytes

        progress_lock = asyncio.Lock()

        async def progress(delta):
            nonlocal downloaded
            nonlocal last_report

            async with progress_lock:
                downloaded += delta

                should_update = (
                    downloaded - last_report
                    >= 8 * 1024 * 1024
                    or (
                        total > 0
                        and downloaded >= total
                    )
                )

                if not should_update:
                    return

                last_report = downloaded

                await self.db.update(
                    job_id,
                    downloaded_bytes=downloaded,
                    total_bytes=total,
                )

                if total:
                    percentage = (
                        downloaded / total * 100
                    )

                    logger.info(
                        "Job %s: %.1f%% (%s / %s)",
                        job_id,
                        percentage,
                        format_bytes(downloaded),
                        format_bytes(total),
                    )
                else:
                    logger.info(
                        "Job %s: %s downloaded",
                        job_id,
                        format_bytes(downloaded),
                    )

        download_started = time.monotonic()

        try:
            logger.info(
                "Starting job %s: %s",
                job_id,
                url,
            )

            await self.db.update(
                job_id,
                status="downloading",
                started_at="CURRENT_TIMESTAMP",
                error=None,
                download_attempts=(
                    job.download_attempts + 1
                ),
            )

            await self.db.increment_statistics(
                total_download_attempts=1
            )

            probed_total, _, detected_name = (
                await self.downloader.probe(url)
            )

            if detected_name:
                filename = sanitize_filename(
                    detected_name
                )

                await self.db.update(
                    job_id,
                    filename=filename,
                )

            total = probed_total or total

            await self.db.update(
                job_id,
                total_bytes=total or 0,
            )

            path, total = (
                await self.downloader.download(
                    url,
                    filename,
                    progress,
                )
            )

            download_elapsed = (
                time.monotonic()
                - download_started
            )

            size = path.stat().st_size

            if total and size != total:
                raise DownloadError(
                    f"Final file size mismatch: "
                    f"{size}/{total}"
                )

            await self.db.update(
                job_id,
                downloaded_bytes=size,
                total_bytes=total or size,
                downloaded_at="CURRENT_TIMESTAMP",
            )

            checksum = None

            if self.config.verify_checksum:
                logger.info(
                    "Job %s: calculating SHA-256.",
                    job_id,
                )

                checksum = (
                    await self.downloader.checksum(
                        path
                    )
                )

                await self.db.update(
                    job_id,
                    sha256=checksum,
                )

                logger.info(
                    "Job %s SHA-256: %s",
                    job_id,
                    checksum,
                )

            current = await self.db.get(job_id)

            if current and current.status == "cancelled":
                logger.warning(
                    "Job %s was cancelled.",
                    job_id,
                )
                return

            upload_attempt_number = (
                current.upload_attempts + 1
                if current
                else 1
            )

            await self.db.update(
                job_id,
                status="uploading",
                upload_attempts=upload_attempt_number,
            )

            await self.db.increment_statistics(
                total_upload_attempts=1
            )

            caption = (
                f"📦 {filename}\n"
                f"Job: #{job_id}\n"
                f"Size: {format_bytes(size)}"
            )

            if checksum:
                caption += (
                    f"\nSHA-256: {checksum}"
                )

            logger.info(
                "Job %s: uploading to Telegram.",
                job_id,
            )

            upload_started = time.monotonic()

            await self.uploader.upload(
                path,
                caption=caption,
            )

            upload_elapsed = (
                time.monotonic()
                - upload_started
            )

            await self.db.update(
                job_id,
                status="completed",
                uploaded_at="CURRENT_TIMESTAMP",
                completed_at="CURRENT_TIMESTAMP",
                error=None,
            )

            await self.db.increment_statistics(
                completed_jobs=1,
                total_bytes_downloaded=size,
                total_bytes_uploaded=size,
                total_download_time=(
                    download_elapsed
                ),
                total_upload_time=(
                    upload_elapsed
                ),
            )

            logger.info(
                "Job %s completed. "
                "Download: %.1fs | Upload: %.1fs",
                job_id,
                download_elapsed,
                upload_elapsed,
            )

            if self.config.delete_after_upload:
                try:
                    path.unlink(
                        missing_ok=True
                    )

                    logger.info(
                        "Job %s: local file deleted.",
                        job_id,
                    )

                except OSError as exc:
                    logger.warning(
                        "Job %s: unable to delete "
                        "local file: %s",
                        job_id,
                        exc,
                    )

        except asyncio.CancelledError:
            await self.db.update(
                job_id,
                status="failed",
                error="Task cancelled",
            )
            raise

        except Exception as exc:
            logger.exception(
                "Job %s failed.",
                job_id,
            )

            await self.db.update(
                job_id,
                status="failed",
                error=str(exc),
            )

            await self.db.increment_statistics(
                failed_jobs=1
            )

            if self.config.cleanup_failed_parts:
                self.cleanup_job_files(
                    filename
                )

    def cleanup_job_files(
        self,
        filename: str,
    ):
        directory = self.config.download_dir

        for path in directory.glob(
            f"{filename}.part*"
        ):
            try:
                path.unlink(
                    missing_ok=True
                )
            except OSError:
                logger.warning(
                    "Unable to remove %s",
                    path,
                )

        assembling = (
            directory /
            f"{filename}.assembling"
        )

        assembling.unlink(
            missing_ok=True
        )

    async def process_urls(
        self,
        urls: list[str],
    ):
        semaphore = asyncio.Semaphore(
            self.config.max_download_workers
        )

        async def worker(url: str):
            filename = (
                self.downloader.filename_from_url(
                    url
                )
            )

            job_id, created = (
                await self.db.create_job_if_not_duplicate(
                    url,
                    filename,
                )
            )

            if not created:
                logger.warning(
                    "Skipping duplicate URL. "
                    "Existing job: #%s",
                    job_id,
                )
                return

            async with semaphore:
                await self.run_job(
                    job_id,
                    url,
                    filename,
                )

        tasks = [
            asyncio.create_task(worker(url))
            for url in urls
        ]

        await asyncio.gather(*tasks)

    async def resume_jobs(self):
        jobs = await self.db.pending()

        if not jobs:
            logger.info(
                "No pending jobs."
            )
            return

        logger.info(
            "Resuming %d job(s).",
            len(jobs),
        )

        semaphore = asyncio.Semaphore(
            self.config.max_download_workers
        )

        async def worker(job):
            async with semaphore:
                await self.run_job(
                    job.id,
                    job.url,
                    job.filename,
                )

        await asyncio.gather(
            *(worker(job) for job in jobs)
        )

    async def show_jobs(
        self,
        limit: int = 50,
    ):
        jobs = await self.db.list_jobs(limit)

        if not jobs:
            print("No jobs found.")
            return

        print()
        print(
            f"{'ID':<6}"
            f"{'STATUS':<14}"
            f"{'FILE':<35}"
            f"{'PROGRESS':<12}"
        )
        print("-" * 75)

        for job in jobs:
            progress = (
                f"{job.progress:.1f}%"
                if job.progress is not None
                else "-"
            )

            filename = (
                job.filename[:32] + "..."
                if len(job.filename) > 35
                else job.filename
            )

            print(
                f"{job.id:<6}"
                f"{job.status:<14}"
                f"{filename:<35}"
                f"{progress:<12}"
            )

    async def show_statistics(self):
        stats = await self.db.get_statistics()

        if not stats:
            print(
                "No statistics available."
            )
            return

        total_jobs = stats["total_jobs"]
        completed = stats["completed_jobs"]
        failed = stats["failed_jobs"]
        cancelled = stats["cancelled_jobs"]

        finished_jobs = (
            completed
            + failed
            + cancelled
        )

        success_rate = (
            completed / finished_jobs * 100
            if finished_jobs
            else 0.0
        )

        total_downloaded = (
            stats["total_bytes_downloaded"]
        )

        total_uploaded = (
            stats["total_bytes_uploaded"]
        )

        download_time = (
            stats["total_download_time"]
        )

        upload_time = (
            stats["total_upload_time"]
        )

        average_speed = (
            total_downloaded / download_time
            if download_time > 0
            else 0
        )

        print()
        print("=" * 64)
        print(
            "DOWNLOAD MANAGER STATISTICS"
        )
        print("=" * 64)

        print(
            f"Total jobs:          {total_jobs}"
        )
        print(
            f"Completed:           {completed}"
        )
        print(
            f"Failed:              {failed}"
        )
        print(
            f"Cancelled:           {cancelled}"
        )
        print(
            f"Success rate:        "
            f"{success_rate:.2f}%"
        )

        print()

        print(
            f"Downloaded:          "
            f"{format_bytes(total_downloaded)}"
        )
        print(
            f"Uploaded:            "
            f"{format_bytes(total_uploaded)}"
        )
        print(
            f"Download time:       "
            f"{format_duration(download_time)}"
        )
        print(
            f"Upload time:         "
            f"{format_duration(upload_time)}"
        )
        print(
            f"Average speed:       "
            f"{format_bytes(average_speed)}/s"
        )

        print()

        print(
            f"Download attempts:   "
            f"{stats['total_download_attempts']}"
        )
        print(
            f"Upload attempts:     "
            f"{stats['total_upload_attempts']}"
        )
        print(
            f"Retries:             "
            f"{stats['retry_count']}"
        )

        print()
        print(
            f"Last updated:        "
            f"{stats['updated_at']}"
        )
        print("=" * 64)

    async def retry_job(
        self,
        job_id: int,
    ):
        if await self.db.retry(job_id):
            logger.info(
                "Job #%s queued for retry.",
                job_id,
            )

            job = await self.db.get(
                job_id
            )

            if job:
                await self.run_job(
                    job.id,
                    job.url,
                    job.filename,
                )
        else:
            logger.error(
                "Job #%s cannot be retried.",
                job_id,
            )

    async def cancel_job(
        self,
        job_id: int,
    ):
        if await self.db.cancel(job_id):
            logger.info(
                "Job #%s cancelled.",
                job_id,
            )
        else:
            logger.error(
                "Unable to cancel job #%s.",
                job_id,
            )

    async def cleanup(self):
        count = (
            await self.db.delete_completed()
        )

        logger.info(
            "Deleted %d completed database jobs.",
            count,
        )

        directory = (
            self.config.download_dir
        )

        removed = 0

        for pattern in (
            "*.part",
            "*.part*",
            "*.assembling",
        ):
            for path in directory.glob(
                pattern
            ):
                try:
                    if path.is_file():
                        path.unlink(
                            missing_ok=True
                        )
                        removed += 1
                except OSError:
                    logger.warning(
                        "Unable to remove %s",
                        path,
                    )

        logger.info(
            "Removed %d temporary files.",
            removed,
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Async resumable downloader "
            "with Telegram uploads."
        )
    )

    parser.add_argument(
        "urls",
        nargs="*",
        help="URLs to download.",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show persistent statistics.",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show recent jobs.",
    )

    parser.add_argument(
        "--jobs",
        type=int,
        default=50,
        help="Number of jobs to show.",
    )

    parser.add_argument(
        "--retry",
        type=int,
        metavar="JOB_ID",
        help="Retry a failed/cancelled job.",
    )

    parser.add_argument(
        "--cancel",
        type=int,
        metavar="JOB_ID",
        help="Cancel a job.",
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove completed jobs and temp files.",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume pending jobs.",
    )

    return parser


async def async_main():
    parser = build_parser()
    args = parser.parse_args()

    app = Application()

    if args.stats:
        await app.start()
        try:
            await app.show_statistics()
        finally:
            await app.close()
        return

    loop = asyncio.get_running_loop()

    for sig in (
        signal.SIGINT,
        signal.SIGTERM,
    ):
        try:
            loop.add_signal_handler(
                sig,
                app.request_shutdown,
            )
        except NotImplementedError:
            pass

    await app.start()

    try:
        if args.status:
            await app.show_jobs(args.jobs)
            return

        if args.retry is not None:
            await app.retry_job(args.retry)
            return

        if args.cancel is not None:
            await app.cancel_job(args.cancel)
            return

        if args.cleanup:
            await app.cleanup()
            return

        if args.resume:
            await app.resume_jobs()
            return

        if not args.urls:
            parser.print_help()
            return

        await app.process_urls(args.urls)

    finally:
        await app.close()


def main():
    try:
        asyncio.run(
            async_main()
        )
    except KeyboardInterrupt:
        print(
            "\nShutdown requested."
        )


if __name__ == "__main__":
    main()
