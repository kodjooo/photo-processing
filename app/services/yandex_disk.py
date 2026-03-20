from pathlib import Path
from urllib.parse import quote
import asyncio
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class YandexDiskService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_base_url = "https://cloud-api.yandex.net/v1/disk"
        self.control_timeout = httpx.Timeout(120.0, connect=30.0)
        self.upload_timeout = httpx.Timeout(
            self.settings.yandex_upload_timeout_seconds,
            connect=30.0,
        )

    async def get_public_resource_info(self, public_url: str) -> dict:
        async with httpx.AsyncClient(timeout=self.control_timeout) as client:
            response = await client.get(
                f"{self.api_base_url}/public/resources",
                params={"public_key": public_url},
            )
            response.raise_for_status()
            return response.json()

    async def get_public_download_url(self, public_url: str) -> str:
        async with httpx.AsyncClient(timeout=self.control_timeout) as client:
            response = await client.get(
                f"{self.api_base_url}/public/resources/download",
                params={"public_key": public_url},
            )
            response.raise_for_status()
            payload = response.json()
            href = payload.get("href")
            if not href:
                raise ValueError("Не удалось получить ссылку на скачивание архива")
            return href

    async def stream_download_to_file(self, download_url: str, target_path: Path) -> None:
        async with httpx.AsyncClient(timeout=None, follow_redirects=True) as client:
            async with client.stream("GET", download_url) as response:
                response.raise_for_status()
                with target_path.open("wb") as file:
                    async for chunk in response.aiter_bytes(chunk_size=self.settings.download_chunk_size):
                        file.write(chunk)

    async def upload_result(self, local_path: Path, remote_name: str) -> str:
        remote_path = f"{self.settings.yandex_disk_base_path.rstrip('/')}/{remote_name}"
        headers = {"Authorization": f"OAuth {self.settings.yandex_disk_oauth_token}"}
        async with httpx.AsyncClient(timeout=self.control_timeout) as client:
            await self._ensure_directory_exists(client, self.settings.yandex_disk_base_path, headers)
            await self._upload_with_retries(
                client=client,
                headers=headers,
                remote_path=remote_path,
                local_path=local_path,
            )

            await client.put(
                f"{self.api_base_url}/resources/publish",
                params={"path": remote_path},
                headers=headers,
            )

            info_response = await client.get(
                f"{self.api_base_url}/resources",
                params={"path": remote_path},
                headers=headers,
            )
            info_response.raise_for_status()
            info = info_response.json()
            public_url = info.get("public_url")
            if not public_url:
                encoded_path = quote(remote_path)
                return f"https://disk.yandex.ru/client/disk/{encoded_path}"
            return public_url

    async def _upload_with_retries(
        self,
        *,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        remote_path: str,
        local_path: Path,
    ) -> None:
        max_attempts = max(1, self.settings.yandex_upload_max_attempts)
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                upload_response = await client.get(
                    f"{self.api_base_url}/resources/upload",
                    params={"path": remote_path, "overwrite": "true"},
                    headers=headers,
                )
                upload_response.raise_for_status()
                upload_url = upload_response.json().get("href")
                if not upload_url:
                    raise ValueError("Не удалось получить URL для загрузки результата")

                async with httpx.AsyncClient(timeout=self.upload_timeout) as upload_client:
                    put_response = await upload_client.put(
                        upload_url,
                        content=self._iter_file_chunks(local_path),
                    )
                    put_response.raise_for_status()
                return
            except (
                httpx.ReadError,
                httpx.WriteError,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
            ) as error:
                last_error = error
                if attempt >= max_attempts:
                    break
                logger.warning(
                    "Сетевая ошибка при загрузке %s в Яндекс Диск, попытка %s/%s: %s (%s)",
                    remote_path,
                    attempt,
                    max_attempts,
                    type(error).__name__,
                    str(error) or "без текста",
                )
                await asyncio.sleep(self.settings.yandex_upload_retry_delay_seconds)

        if last_error is not None:
            raise last_error

    async def _iter_file_chunks(self, local_path: Path):
        with local_path.open("rb") as file:
            while True:
                chunk = await asyncio.to_thread(file.read, self.settings.yandex_upload_chunk_size)
                if not chunk:
                    break
                yield chunk

    async def _ensure_directory_exists(
        self,
        client: httpx.AsyncClient,
        remote_directory: str,
        headers: dict[str, str],
    ) -> None:
        normalized = remote_directory.strip()
        if not normalized:
            return

        parts = [part for part in normalized.strip("/").split("/") if part]
        current_path = ""
        for part in parts:
            current_path = f"{current_path}/{part}"
            response = await client.put(
                f"{self.api_base_url}/resources",
                params={"path": current_path},
                headers=headers,
            )
            if response.status_code in {201, 409}:
                continue
            response.raise_for_status()
