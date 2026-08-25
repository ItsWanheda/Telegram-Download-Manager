from __future__ import annotations

import asyncio
from pathlib import Path

import aiohttp

from app.utils import smart_sleep


class TelegramUploadError(Exception):
    pass


class TelegramUploader:
    def __init__(
        self,
        token: str,
        chat_id: str,
        retries: int = 5,
        timeout: int = 3600,
        retry_callback=None,
    ):
        self.base_url = (
            f"https://api.telegram.org/bot{token}"
        )
        self.chat_id = chat_id
        self.retries = retries
        self.retry_callback = retry_callback

        self.timeout = aiohttp.ClientTimeout(
            total=timeout,
            connect=60,
            sock_connect=60,
            sock_read=timeout,
        )

        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        if self.session:
            return

        connector = aiohttp.TCPConnector(
            limit=8,
            ttl_dns_cache=300,
        )

        self.session = aiohttp.ClientSession(
            timeout=self.timeout,
            connector=connector,
        )

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def _notify_retry(self):
        if self.retry_callback is not None:
            await self.retry_callback()

    async def upload(
        self,
        path: str | Path,
        caption: str | None = None,
        progress=None,
    ):
        if self.session is None:
            await self.start()

        assert self.session is not None

        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(str(path))

        last_error = None

        for attempt in range(
            1,
            self.retries + 1,
        ):
            retry_after = None

            try:
                data = aiohttp.FormData()

                data.add_field(
                    "chat_id",
                    self.chat_id,
                )

                if caption:
                    data.add_field(
                        "caption",
                        caption,
                    )

                with path.open("rb") as file:
                    data.add_field(
                        "document",
                        file,
                        filename=path.name,
                        content_type="application/octet-stream",
                    )

                    async with self.session.post(
                        f"{self.base_url}/sendDocument",
                        data=data,
                    ) as response:
                        payload = await response.json(
                            content_type=None
                        )

                        if (
                            response.status == 200
                            and payload.get("ok")
                        ):
                            return payload

                        retry_after = (
                            payload
                            .get("parameters", {})
                            .get("retry_after")
                        )

                        # Telegram 429 / temporary server errors.
                        if response.status in {
                            408,
                            425,
                            429,
                            500,
                            502,
                            503,
                            504,
                        }:
                            raise TelegramUploadError(
                                f"Retryable Telegram API error: "
                                f"HTTP {response.status}: {payload}"
                            )

                        raise TelegramUploadError(
                            f"Telegram API error: {payload}"
                        )

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
                TelegramUploadError,
            ) as exc:
                last_error = exc

                # Do not retry permanent API errors.
                if (
                    isinstance(exc, TelegramUploadError)
                    and "Retryable Telegram API error"
                    not in str(exc)
                ):
                    raise

                if attempt >= self.retries:
                    raise

            await self._notify_retry()

            delay = await smart_sleep(
                attempt,
                retry_after=(
                    str(retry_after)
                    if retry_after is not None
                    else None
                ),
            )

            continue

        raise TelegramUploadError(
            f"Upload failed after {self.retries} attempts: "
            f"{last_error}"
        )
