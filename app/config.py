from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


TRUE_VALUES = {"1", "true", "yes", "on", "y"}
FALSE_VALUES = {"0", "false", "no", "off", "n"}


def env_str(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip()

    return value if value else default


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    value = value.strip().lower()

    if value in TRUE_VALUES:
        return True

    if value in FALSE_VALUES:
        return False

    raise ValueError(
        f"{name} must be one of: " f"{', '.join(sorted(TRUE_VALUES | FALSE_VALUES))}"
    )


def env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer") from exc

    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")

    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")

    return value


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str

    download_dir: Path
    db_path: Path
    log_file: Path

    max_download_workers: int
    part_workers: int
    upload_workers: int

    part_size: int
    chunk_size: int

    max_retries: int
    request_timeout: int
    upload_timeout: int

    delete_after_upload: bool
    resume_downloads: bool
    verify_checksum: bool
    cleanup_failed_parts: bool
    recover_stale_jobs: bool

    allow_private_hosts: bool

    min_free_disk_space: int
    max_file_size: int

    log_level: str


def load_config() -> Config:
    token = env_str("TELEGRAM_BOT_TOKEN")
    chat_id = env_str("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing. Set it in your .env file.")

    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is missing. Set it in your .env file.")

    download_dir = Path(
        env_str("DOWNLOAD_DIR", "downloads") or "downloads"
    ).expanduser()

    db_path = Path(env_str("DB_PATH", "jobs.db") or "jobs.db").expanduser()

    log_file = Path(env_str("LOG_FILE", "logs/app.log") or "logs/app.log").expanduser()

    config = Config(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        download_dir=download_dir,
        db_path=db_path,
        log_file=log_file,
        max_download_workers=env_int(
            "MAX_DOWNLOAD_WORKERS",
            3,
            minimum=1,
            maximum=64,
        ),
        part_workers=env_int(
            "PART_WORKERS",
            4,
            minimum=1,
            maximum=64,
        ),
        upload_workers=env_int(
            "UPLOAD_WORKERS",
            2,
            minimum=1,
            maximum=16,
        ),
        part_size=env_int(
            "PART_SIZE",
            8 * 1024 * 1024,
            minimum=256 * 1024,
        ),
        chunk_size=env_int(
            "CHUNK_SIZE",
            1024 * 1024,
            minimum=16 * 1024,
        ),
        max_retries=env_int(
            "MAX_RETRIES",
            5,
            minimum=1,
            maximum=50,
        ),
        request_timeout=env_int(
            "REQUEST_TIMEOUT",
            3600,
            minimum=10,
        ),
        upload_timeout=env_int(
            "UPLOAD_TIMEOUT",
            3600,
            minimum=10,
        ),
        delete_after_upload=env_bool(
            "DELETE_AFTER_UPLOAD",
            True,
        ),
        resume_downloads=env_bool(
            "RESUME_DOWNLOADS",
            True,
        ),
        verify_checksum=env_bool(
            "VERIFY_CHECKSUM",
            True,
        ),
        cleanup_failed_parts=env_bool(
            "CLEANUP_FAILED_PARTS",
            False,
        ),
        recover_stale_jobs=env_bool(
            "RECOVER_STALE_JOBS",
            True,
        ),
        allow_private_hosts=env_bool(
            "ALLOW_PRIVATE_HOSTS",
            False,
        ),
        min_free_disk_space=env_int(
            "MIN_FREE_DISK_SPACE",
            512 * 1024 * 1024,
            minimum=0,
        ),
        max_file_size=env_int(
            "MAX_FILE_SIZE",
            0,
            minimum=0,
        ),
        log_level=(env_str("LOG_LEVEL", "INFO") or "INFO").upper(),
    )

    config.download_dir.mkdir(parents=True, exist_ok=True)

    config.db_path.parent.mkdir(parents=True, exist_ok=True)

    config.log_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return config
