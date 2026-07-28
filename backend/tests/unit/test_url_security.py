import pytest

from app.core.errors import ApplicationError
from app.importers.url_security import validate_public_url


async def public_resolver(hostname: str, port: int) -> list[str]:
    assert hostname
    assert port
    return ["93.184.216.34"]


async def private_resolver(hostname: str, port: int) -> list[str]:
    return ["127.0.0.1"]


@pytest.mark.asyncio
async def test_accepts_public_http_url() -> None:
    result = await validate_public_url(
        "https://example.com/jobs?id=42#details",
        resolver=public_resolver,
    )

    assert result == "https://example.com/jobs?id=42"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://user:secret@example.com/",
    ],
)
async def test_rejects_unsupported_or_credentialed_urls(url: str) -> None:
    with pytest.raises(ApplicationError):
        await validate_public_url(url, resolver=public_resolver)


@pytest.mark.asyncio
async def test_blocks_private_network_targets() -> None:
    with pytest.raises(ApplicationError) as error:
        await validate_public_url("http://localhost/", resolver=private_resolver)

    assert error.value.code == "private_network_forbidden"

