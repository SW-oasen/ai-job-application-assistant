from types import SimpleNamespace
from uuid import UUID

import pytest

from app.database.repositories.jobs import PersistedImport, StoredJobSource
from app.services import job_reimport_service

JOB_ID = UUID("91e5c97c-9102-422d-be19-9c14c82ea81d")


def stored_source(**overrides) -> StoredJobSource:
    values = {
        "job_id": JOB_ID,
        "source_type": "pdf",
        "source_url": None,
        "source_filename": "job.pdf",
        "title": "Data Engineer",
        "raw_content": None,
        "normalized_content": "Wir suchen einen Data Engineer für unser Team.",
        "content_hash": "a" * 64,
        "retrieval_method": "native_pdf",
        "language": None,
        "import_warnings": ["native_pdf_text_insufficient"],
    }
    values.update(overrides)
    return StoredJobSource(**values)


@pytest.mark.asyncio
async def test_reimports_pdf_from_stored_content(monkeypatch) -> None:
    captured = {}

    async def fake_source(job_id):
        assert job_id == JOB_ID
        return stored_source()

    async def fake_enrich(content, **kwargs):
        assert content.startswith("Wir suchen")
        return SimpleNamespace(
            metadata={"language": "de"},
            details={"language": {"value": "de"}},
            warnings=["semantic_metadata_fallback_used"],
        )

    async def fake_persist(**kwargs):
        captured.update(kwargs)
        return PersistedImport(job_id=str(JOB_ID), duplicate=False, reimported=True)

    monkeypatch.setattr(job_reimport_service, "get_stored_job_source", fake_source)
    monkeypatch.setattr(job_reimport_service, "enrich_job_metadata", fake_enrich)
    monkeypatch.setattr(job_reimport_service, "persist_imported_job", fake_persist)

    result = await job_reimport_service.reimport_job(JOB_ID)

    assert result.language == "de"
    assert captured["replace_job_id"] == JOB_ID
    assert captured["replace_existing"] is True
    assert captured["normalized_content"].startswith("Wir suchen")


@pytest.mark.asyncio
async def test_reimports_url_from_stored_source_url(monkeypatch) -> None:
    calls = 0

    async def fake_source(job_id):
        nonlocal calls
        calls += 1
        return stored_source(
            source_type="url",
            source_url="https://example.com/job",
            source_filename=None,
            retrieval_method="http",
            language="en" if calls > 1 else None,
        )

    async def fake_import(payload, **kwargs):
        assert payload.url == "https://example.com/job"
        assert kwargs["replace_job_id"] == JOB_ID
        return SimpleNamespace(
            quality_sufficient=True,
            job_id=str(JOB_ID),
            retrieval_method="http",
            warnings=[],
        )

    monkeypatch.setattr(job_reimport_service, "get_stored_job_source", fake_source)
    monkeypatch.setattr(job_reimport_service, "import_url", fake_import)

    result = await job_reimport_service.reimport_job(JOB_ID)

    assert result.language == "en"
    assert calls == 2
