from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import get_settings


class YandexDiskService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.api_base_url = "https://cloud-api.yandex.net/v1/disk"

    async def get_public_resource_info(self, public_url: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{self.api_base_url}/public/resources",
                params={"public_key": public_url},
            )
            response.raise_for_status()
            return response.json()

    async def get_public_download_url(self, public_url: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
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
        async with httpx.AsyncClient(timeout=120) as client:
            upload_response = await client.get(
                f"{self.api_base_url}/resources/upload",
                params={"path": remote_path, "overwrite": "true"},
                headers=headers,
            )
            upload_response.raise_for_status()
            upload_url = upload_response.json().get("href")
            if not upload_url:
                raise ValueError("Не удалось получить URL для загрузки результата")

            with local_path.open("rb") as file:
                put_response = await client.put(upload_url, content=file)
                put_response.raise_for_status()

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
