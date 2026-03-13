from urllib.parse import urlparse


YANDEX_HOSTS = {
    "disk.yandex.ru",
    "yadi.sk",
    "yandex.ru",
    "disk.yandex.com",
}


def validate_yandex_public_url(source_url: str) -> None:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Ссылка должна начинаться с http или https")
    if parsed.netloc.lower() not in YANDEX_HOSTS:
        raise ValueError("Поддерживаются только публичные ссылки Яндекс Диска")

