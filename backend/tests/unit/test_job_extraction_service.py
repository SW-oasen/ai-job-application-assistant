from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.services import job_extraction_service


def test_merge_source_backed_items_keeps_requirements_omitted_by_llm() -> None:
    merged = job_extraction_service._merge_source_backed_items(
        [{"requirement": "Python", "evidence": "Python"}],
        [
            {"requirement": "Python programming", "evidence": "Python"},
            {"requirement": "German fluency", "evidence": "Fluency in German"},
        ],
        "requirement",
    )

    assert [item["requirement"] for item in merged] == ["Python", "German fluency"]


@pytest.mark.asyncio
async def test_llm_fallback_enriches_all_job_extraction_sections(monkeypatch) -> None:
    captured = {}

    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"data": {"status": "succeeded", "outputs": {"extraction_json": {
                "metadata": {"title": {"value": "Data Engineer", "confidence": .99, "evidence": "Data Engineer"}, "company": {"value": "Example", "confidence": .99, "evidence": "Example"}, "location": {"value": "Berlin", "confidence": .99, "evidence": "Berlin"}, "language": {"value": "en", "confidence": .99, "evidence": "Data Engineer"}},
                "activities": [{"activity": "Build data pipelines", "evidence": "Build data pipelines"}],
                "requirements": [{"requirement": "Python skills", "evidence": "Python skills", "priority": "must"}],
            }}}}
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs): captured.update(kwargs["json"]["inputs"]); return Response()

    monkeypatch.setattr(job_extraction_service.httpx, "AsyncClient", Client)
    monkeypatch.setattr(job_extraction_service, "get_settings", lambda: SimpleNamespace(dify_base_url="http://api:5001", dify_job_extraction_workflow_api_key=SecretStr("app-test"), dify_job_extraction_workflow_timeout_seconds=180, job_extraction_max_characters=30_000))
    content = "Example Data Engineer Berlin\n- Build data pipelines\n- Python skills"
    result = await job_extraction_service.enrich_job_extraction(content=content, metadata={"title": None, "company": None, "location": None, "language": None}, activities=[], requirements=[], retry_instructions=["Find all lists"])

    assert result.metadata["title"] == "Data Engineer"
    assert result.activities[0]["activity"] == "Build data pipelines"
    assert result.requirements[0]["requirement"] == "Python skills"
    assert captured["retry_instructions_json"] == '["Find all lists"]'


@pytest.mark.asyncio
async def test_uses_legacy_metadata_fallback_until_new_workflow_is_configured(monkeypatch) -> None:
    monkeypatch.setattr(job_extraction_service, "get_settings", lambda: SimpleNamespace(dify_job_extraction_workflow_api_key=None))
    monkeypatch.setattr(job_extraction_service, "enrich_job_metadata", lambda *args, **kwargs: __import__("asyncio").sleep(0, result=SimpleNamespace(metadata={"title": "Legacy title"}, details={}, warnings=["semantic_metadata_fallback_used"])))

    result = await job_extraction_service.enrich_job_extraction(content="Job", metadata={"title": None}, activities=[], requirements=[])

    assert result.metadata["title"] == "Legacy title"
    assert "semantic_metadata_fallback_used" in result.warnings
