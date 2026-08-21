from __future__ import annotations

import asyncio
import math
import os
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from app.utils import (
    check_disk_space,
    filename_from_content_disposition,
    filename_from_url,
    host_resolves_to_private_ip,
    sanitize_filename,
    sha256_file,
    sleep_backoff,
    validate_url,
)


class DownloadError(Exception):
    pass


class MultiPartDownloader:
    def __init__(
        self,
        directory,
        part_size,
        part_workers,
        chunk_size,
        retries,
        timeout,
        *,
        resume=True,
        allow_private_hosts=False,
        min_free_disk_space=0,
        max_file_size=0,
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.part_size = part_size
        self.part_workers = part_workers
        self.chunk_size = chunk_size
        self.retries = retries

        self.timeout = aiohttp.ClientTimeout(
            total=timeout,
            connect=60,
            sock_connect=60,
            sock_read=timeout,
        )

        self.resume = resume
        self.allow_private_hosts = allow_private_hosts
        self.min_free_disk_space = min_free_disk_space
        self.max_file_size = max_file_size

        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        if self.session is not None:
            return

        connector = aiohttp.TCPConnector(
            limit=max(32, self.part_workers * 4),
            limit_per_host=max(8, self.part_workers),
            ttl_dns_cache=300,
            enable_cleanup_closed=True,
        )

        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector,
            headers={"User-Agent": ("AsyncDownloadManager/2.0 " "(aiohttp)")},
        )

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def _validate_target(self, url: str):
        validate_url(url)

        if self.allow_private_hosts:
            return

        hostname = urlparse(url).hostname

        if not hostname:
            raise DownloadError("URL hostname is missing.")

        if await host_resolves_to_private_ip(hostname):
            raise DownloadError(
                f"Refusing to download from private/local host: " f"{hostname}"
            )

    @staticmethod
    def filename_from_url(url: str) -> str:
        return filename_from_url(url)

    async def probe(self, url: str):
        await self._validate_target(url)

        if self.session is None:
            await self.start()

        assert self.session is not None

        try:
            async with self.session.head(
                url,
                allow_redirects=True,
            ) as response:
                if response.status < 400:
                    total = response.headers.get("Content-Length")

                    ranges = response.headers.get(
                        "Accept-Ranges",
                        "",
                    ).lower()

                    filename = filename_from_content_disposition(
                        response.headers.get("Content-Disposition")
                    )

                    return (
                        int(total) if total else None,
                        ranges == "bytes",
                        filename,
                    )

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ):
            pass

        try:
            async with self.session.get(
                url,
                headers={"Range": "bytes=0-0"},
                allow_redirects=True,
            ) as response:
                if response.status not in (200, 206):
                    raise DownloadError(f"HTTP {response.status}")

                filename = filename_from_content_disposition(
                    response.headers.get("Content-Disposition")
                )

                content_range = response.headers.get(
                    "Content-Range",
                    "",
                )

                if response.status == 206 and "/" in content_range:
                    total_raw = content_range.rsplit(
                        "/",
                        1,
                    )[1]

                    if total_raw != "*":
                        return (
                            int(total_raw),
                            True,
                            filename,
                        )

                content_length = response.headers.get("Content-Length")

                return (
                    int(content_length) if content_length else None,
                    False,
                    filename,
                )

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ) as exc:
            raise DownloadError(f"Unable to probe URL: {exc}") from exc

    async def fetch_part(
        self,
        url: str,
        start: int,
        end: int,
        path: Path,
        callback,
    ):
        if self.session is None:
            raise RuntimeError("Downloader session is not started.")

        expected = end - start + 1

        existing = path.stat().st_size if path.exists() else 0

        if not self.resume:
            existing = 0
            path.unlink(missing_ok=True)

        if existing > expected:
            path.unlink(missing_ok=True)
            existing = 0

        if existing == expected:
            return existing

        for attempt in range(
            1,
            self.retries + 1,
        ):
            position = start + existing

            try:
                headers = {"Range": f"bytes={position}-{end}"}

                async with self.session.get(
                    url,
                    headers=headers,
                    allow_redirects=True,
                ) as response:

                    if response.status == 200:
                        if position != start:
                            raise DownloadError(
                                "Server ignored Range request "
                                "during resumed part download."
                            )

                        existing = 0

                        path.unlink(missing_ok=True)

                    elif response.status != 206:
                        raise DownloadError(
                            f"Range request returned " f"HTTP {response.status}"
                        )

                    mode = "ab" if existing else "wb"

                    with path.open(mode) as file:
                        async for chunk in response.content.iter_chunked(
                            self.chunk_size
                        ):
                            file.write(chunk)

                            existing += len(chunk)

                            await callback(len(chunk))

                if existing != expected:
                    raise DownloadError(
                        f"Part incomplete: " f"{existing}/{expected} bytes"
                    )

                return existing

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
                DownloadError,
            ) as exc:
                if attempt >= self.retries:
                    raise

                await sleep_backoff(attempt)

                existing = path.stat().st_size if path.exists() else 0

        raise DownloadError("Multipart part failed.")

    async def download(
        self,
        url: str,
        filename: str,
        callback,
    ):
        total, supports_range, detected_name = await self.probe(url)

        if detected_name:
            filename = detected_name
        else:
            filename = sanitize_filename(filename)

        final = self.directory / filename

        if total and total > 0 and final.exists() and final.stat().st_size == total:
            return final, total

        if self.max_file_size and total and total > self.max_file_size:
            raise DownloadError("Remote file exceeds MAX_FILE_SIZE.")

        check_disk_space(
            self.directory,
            total or self.part_size,
            self.min_free_disk_space,
        )

        if not total or not supports_range:
            return await self.single(
                url,
                filename,
                total,
                callback,
            )

        count = math.ceil(total / self.part_size)

        parts = [self.directory / f"{filename}.part{i:05d}" for i in range(count)]

        semaphore = asyncio.Semaphore(self.part_workers)

        async def download_one(index: int):
            start = index * self.part_size

            end = min(
                total - 1,
                start + self.part_size - 1,
            )

            async with semaphore:
                return await self.fetch_part(
                    url,
                    start,
                    end,
                    parts[index],
                    callback,
                )

        try:
            await asyncio.gather(*(download_one(i) for i in range(count)))

            temp_final = Path(f"{final}.assembling")

            temp_final.unlink(missing_ok=True)

            with temp_final.open("wb") as output:
                for part in parts:
                    if not part.exists():
                        raise DownloadError(f"Missing part: {part.name}")

                    with part.open("rb") as source:
                        while True:
                            chunk = source.read(self.chunk_size)

                            if not chunk:
                                break

                            output.write(chunk)

            if temp_final.stat().st_size != total:
                raise DownloadError("Final assembled file has " "an unexpected size.")

            temp_final.replace(final)

            for part in parts:
                part.unlink(missing_ok=True)

            return final, total

        except Exception:
            temp_final = Path(f"{final}.assembling")

            temp_final.unlink(missing_ok=True)

            if not self.resume:
                for part in parts:
                    part.unlink(missing_ok=True)

            raise

    async def single(
        self,
        url: str,
        filename: str,
        total: int | None,
        callback,
    ):
        if self.session is None:
            raise RuntimeError("Downloader session is not started.")

        final = self.directory / filename

        partial = Path(f"{final}.part")

        existing = partial.stat().st_size if partial.exists() else 0

        if not self.resume:
            existing = 0
            partial.unlink(missing_ok=True)

        for attempt in range(
            1,
            self.retries + 1,
        ):
            try:
                headers = {}

                if existing:
                    headers["Range"] = f"bytes={existing}-"

                async with self.session.get(
                    url,
                    headers=headers,
                    allow_redirects=True,
                ) as response:

                    if response.status not in (
                        200,
                        206,
                    ):
                        raise DownloadError(f"HTTP {response.status}")

                    if existing and response.status == 200:
                        existing = 0
                        partial.unlink(missing_ok=True)

                    mode = "ab" if existing else "wb"

                    with partial.open(mode) as file:
                        async for chunk in response.content.iter_chunked(
                            self.chunk_size
                        ):
                            file.write(chunk)

                            existing += len(chunk)

                            await callback(len(chunk))

                if total and existing != total:
                    raise DownloadError(f"Download incomplete: " f"{existing}/{total}")

                partial.replace(final)

                return final, total or existing

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
                DownloadError,
            ):
                if attempt >= self.retries:
                    raise

                await sleep_backoff(attempt)

                existing = partial.stat().st_size if partial.exists() else 0

        raise DownloadError("Single-stream download failed.")

    async def checksum(
        self,
        path: Path,
    ) -> str:
        return await sha256_file(
            path,
            self.chunk_size,
        )
