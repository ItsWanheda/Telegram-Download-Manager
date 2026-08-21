from __future__ import annotations

import asyncio
import os
from pathlib import Path

import aiohttp


class TelegramUploadError(Exception):
    pass


class TelegramUploader:
    def __init__(
        self,
        token: str,
        chat_id: str,
        retries: int = 5,
        timeout: int = 3600,
    ):
        self.base_url = f"https://api.telegram.org/bot{token}"

        self.chat_id = chat_id
        self.retries = retries

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

        for attempt in range(
            1,
            self.retries + 1,
        ):
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
                        content_type=("application/octet-stream"),
                    )

                    async with self.session.post(
                        f"{self.base_url}/sendDocument",
                        data=data,
                    ) as response:

                        payload = await response.json(content_type=None)

                        if response.status == 200 and payload.get("ok"):
                            return payload

                        retry_after = payload.get("parameters", {}).get("retry_after")

                        if retry_after:
                            await asyncio.sleep(
                                min(
                                    300,
                                    int(retry_after),
                                )
                            )

                            continue

                        raise TelegramUploadError(f"Telegram API error: " f"{payload}")

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                OSError,
                TelegramUploadError,
            ) as exc:

                if attempt >= self.retries:
                    raise

                delay = min(
                    60,
                    2 ** (attempt - 1),
                )

                await asyncio.sleep(delay)

        raise TelegramUploadError("Upload failed.")
