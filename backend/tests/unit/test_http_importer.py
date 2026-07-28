import httpx
import pytest

from app.core.errors import ApplicationError
from app.importers.http_importer import HttpImporter


async def trust_test_url(url: str) -> str:
    return url


@pytest.mark.asyncio
async def test_downloads_html_within_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.importers.http_importer.validate_public_url",
        trust_test_url,
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html; charset=utf-8"},
            text="<h1>Job</h1>",
        )
    )
    importer = HttpImporter(
        timeout_seconds=1,
        max_bytes=1_000,
        max_redirects=2,
        user_agent="test",
        transport=transport,
    )

    result = await importer.fetch("https://example.com/job")

    assert result.content == "<h1>Job</h1>"
    assert result.content_type == "text/html"


@pytest.mark.asyncio
async def test_rejects_oversized_download(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.importers.http_importer.validate_public_url",
        trust_test_url,
    )
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"x" * 11,
        )
    )
    importer = HttpImporter(
        timeout_seconds=1,
        max_bytes=10,
        max_redirects=2,
        user_agent="test",
        transport=transport,
    )

    with pytest.raises(ApplicationError) as error:
        await importer.fetch("https://example.com/job")

    assert error.value.code == "source_too_large"

