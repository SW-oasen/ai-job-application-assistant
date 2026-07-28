import pytest

from app.database.repositories.jobs import PersistedImport
from app.importers.http_importer import HttpImportResult
from app.importers.playwright_importer import BrowserImportResult
from app.schemas.imports import UrlImportRequest, UrlImportResponse
from app.services import url_import_service

LONG_STATIC_HTML = "<html><body><h1>Data Engineer</h1><p>" + ("work " * 120) + "</p></body></html>"
SHORT_HTML = "<html><body><h1>Loading</h1></body></html>"


class FakeHttpImporter:
    def __init__(self, **kwargs) -> None:
        pass

    async def fetch(self, url: str) -> HttpImportResult:
        return HttpImportResult(
            final_url=url,
            content=LONG_STATIC_HTML,
            content_type="text/html",
        )


class ShortHttpImporter(FakeHttpImporter):
    async def fetch(self, url: str) -> HttpImportResult:
        return HttpImportResult(
            final_url=url,
            content=SHORT_HTML,
            content_type="text/html",
        )


class FakePlaywrightImporter:
    calls = 0

    def __init__(self, **kwargs) -> None:
        pass

    async def fetch(self, url: str) -> BrowserImportResult:
        type(self).calls += 1
        return BrowserImportResult(final_url=url, content=LONG_STATIC_HTML)


@pytest.mark.asyncio
async def test_keeps_sufficient_static_http_result(monkeypatch) -> None:
    FakePlaywrightImporter.calls = 0
    monkeypatch.setattr(url_import_service, "HttpImporter", FakeHttpImporter)
    monkeypatch.setattr(
        url_import_service,
        "PlaywrightImporter",
        FakePlaywrightImporter,
    )

    result = await url_import_service.import_url(
        UrlImportRequest(url="https://example.com/job")
    )

    assert result.retrieval_method == "http"
    assert result.quality_sufficient is True
    assert FakePlaywrightImporter.calls == 0


@pytest.mark.asyncio
async def test_uses_browser_when_static_content_is_insufficient(monkeypatch) -> None:
    FakePlaywrightImporter.calls = 0
    monkeypatch.setattr(url_import_service, "HttpImporter", ShortHttpImporter)
    monkeypatch.setattr(
        url_import_service,
        "PlaywrightImporter",
        FakePlaywrightImporter,
    )

    result = await url_import_service.import_url(
        UrlImportRequest(url="https://example.com/job")
    )

    assert result.retrieval_method == "browser"
    assert result.quality_sufficient is True
    assert result.warnings == [
        "browser_fallback_used",
        "semantic_metadata_fallback_not_configured",
    ]
    assert FakePlaywrightImporter.calls == 1


@pytest.mark.asyncio
async def test_force_browser_skips_http(monkeypatch) -> None:
    FakePlaywrightImporter.calls = 0
    monkeypatch.setattr(
        url_import_service,
        "PlaywrightImporter",
        FakePlaywrightImporter,
    )

    result = await url_import_service.import_url(
        UrlImportRequest(url="https://example.com/job", force_browser=True)
    )

    assert result.retrieval_method == "browser"
    assert "browser_fallback_used" not in result.warnings
    assert FakePlaywrightImporter.calls == 1


@pytest.mark.asyncio
async def test_does_not_persist_insufficient_import(monkeypatch) -> None:
    async def fail_if_called(**kwargs) -> PersistedImport:
        raise AssertionError("Insufficient content must not be persisted as a job")

    monkeypatch.setattr(url_import_service, "persist_imported_job", fail_if_called)
    response = UrlImportResponse(
        success=True,
        source_url="https://example.com/blocked",
        retrieval_method="browser",
        title=None,
        raw_html="<html></html>",
        markdown="Blocked",
        content_hash="hash",
        text_length=7,
        quality_sufficient=False,
        browser_fallback_recommended=False,
        warnings=["content_quality_insufficient"],
    )

    result = await url_import_service._persist_response(response)

    assert result.job_id is None
    assert result.duplicate is False


@pytest.mark.asyncio
async def test_persists_sufficient_import(monkeypatch) -> None:
    async def fake_persist(**kwargs) -> PersistedImport:
        return PersistedImport(job_id="9c32f71f-b40a-43e5-a2f4-a423fb164dc8", duplicate=False)

    monkeypatch.setattr(url_import_service, "persist_imported_job", fake_persist)
    response = UrlImportResponse(
        success=True,
        source_url="https://example.com/job",
        retrieval_method="http",
        title="Data Engineer",
        raw_html=LONG_STATIC_HTML,
        markdown="Data Engineer " + ("work " * 120),
        content_hash="hash",
        text_length=620,
        quality_sufficient=True,
        browser_fallback_recommended=False,
        warnings=[],
    )

    result = await url_import_service._persist_response(response)

    assert result.job_id == "9c32f71f-b40a-43e5-a2f4-a423fb164dc8"
