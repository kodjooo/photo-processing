from pathlib import Path

import httpx
import pytest

from app.services.yandex_disk import YandexDiskService


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.request = httpx.Request("GET", "https://example.com")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=self.request, response=self)

    def json(self) -> dict:
        return self._payload


class FakeAsyncClient:
    upload_put_calls = 0
    uploaded_payloads: list[bytes] = []

    def __init__(self, *args, timeout=None, **kwargs) -> None:
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, headers=None):
        if url.endswith("/resources/upload"):
            return FakeResponse(payload={"href": "https://upload.example.com"})
        if url.endswith("/resources"):
            return FakeResponse(payload={"public_url": "https://disk.yandex.ru/public"})
        raise AssertionError(f"Unexpected GET url: {url}")

    async def put(self, url, params=None, headers=None, content=None):
        if url == "https://upload.example.com":
            type(self).upload_put_calls += 1
            if content is not None and hasattr(content, "__aiter__"):
                payload = b""
                async for chunk in content:
                    payload += chunk
                type(self).uploaded_payloads.append(payload)
            if type(self).upload_put_calls == 1:
                raise httpx.ReadError("boom", request=httpx.Request("PUT", url))
            return FakeResponse(status_code=201)
        if url.endswith("/resources"):
            return FakeResponse(status_code=409)
        if url.endswith("/resources/publish"):
            return FakeResponse(status_code=200)
        raise AssertionError(f"Unexpected PUT url: {url}")


@pytest.mark.asyncio
async def test_upload_result_retries_on_read_error(monkeypatch, tmp_path: Path) -> None:
    file_path = tmp_path / "result.zip"
    file_path.write_bytes(b"data")

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    
    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("app.services.yandex_disk.asyncio.sleep", fake_sleep)
    FakeAsyncClient.upload_put_calls = 0
    FakeAsyncClient.uploaded_payloads = []

    service = YandexDiskService()
    result = await service.upload_result(file_path, "job.zip")

    assert result == "https://disk.yandex.ru/public"
    assert FakeAsyncClient.upload_put_calls == 2
    assert FakeAsyncClient.uploaded_payloads == [b"data", b"data"]
