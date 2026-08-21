from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import os
import re
import socket
from pathlib import Path
from urllib.parse import unquote, urlparse

from email.message import Message

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_filename(
    filename: str | None,
    fallback: str = "download.bin",
) -> str:
    if not filename:
        return fallback

    filename = unquote(filename).strip()

    filename = INVALID_FILENAME_CHARS.sub("_", filename)

    filename = filename.strip(". ")

    if not filename:
        return fallback

    # Avoid Windows reserved device names.
    stem = filename.split(".", 1)[0].upper()

    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    if stem in reserved:
        filename = f"_{filename}"

    return filename[:255]


def filename_from_content_disposition(
    value: str | None,
) -> str | None:
    if not value:
        return None

    message = Message()

    message["Content-Disposition"] = value

    filename = message.get_filename()

    if filename:
        return sanitize_filename(filename)

    return None


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)

    name = os.path.basename(parsed.path)

    return sanitize_filename(name)


def validate_url(url: str) -> None:
    parsed = urlparse(url)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported.")

    if not parsed.hostname:
        raise ValueError("URL does not contain a hostname.")


def is_private_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False

    return any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


async def host_resolves_to_private_ip(hostname: str) -> bool:
    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        return False

    for info in infos:
        address = info[4][0]

        if is_private_ip(address):
            return True

    return False


def check_disk_space(
    directory: Path,
    required_bytes: int,
    minimum_free_bytes: int,
) -> None:
    usage = os.statvfs(directory)

    available = usage.f_bavail * usage.f_frsize

    required = required_bytes + minimum_free_bytes

    if available < required:
        raise OSError(
            "Insufficient disk space. "
            f"Required approximately {required:,} bytes, "
            f"available {available:,} bytes."
        )


async def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = await asyncio.to_thread(
                file.read,
                chunk_size,
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def format_bytes(value: int | float) -> str:
    value = float(value)

    units = (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
        "PB",
    )

    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} EB"


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))

    if seconds < 60:
        return f"{seconds}s"

    minutes, seconds = divmod(seconds, 60)

    if minutes < 60:
        return f"{minutes}m {seconds}s"

    hours, minutes = divmod(minutes, 60)

    if hours < 24:
        return f"{hours}h {minutes}m"

    days, hours = divmod(hours, 24)

    return f"{days}d {hours}h"


def backoff_delay(
    attempt: int,
    maximum: float = 60.0,
) -> float:
    import random

    base = min(
        maximum,
        2 ** max(0, attempt - 1),
    )

    return base + random.uniform(0, 1)


async def sleep_backoff(attempt: int) -> None:
    await asyncio.sleep(backoff_delay(attempt))
