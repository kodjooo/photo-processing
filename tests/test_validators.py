import pytest

from app.services.validators import validate_yandex_public_url


def test_validate_yandex_public_url_accepts_supported_domain() -> None:
    validate_yandex_public_url("https://disk.yandex.ru/d/example")


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("ftp://disk.yandex.ru/d/example", "Ссылка должна начинаться"),
        ("https://example.com/archive.zip", "Поддерживаются только публичные ссылки"),
    ],
)
def test_validate_yandex_public_url_rejects_invalid_links(url: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_yandex_public_url(url)

