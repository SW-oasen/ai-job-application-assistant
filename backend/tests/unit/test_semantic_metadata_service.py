from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.services import semantic_metadata_service


def test_semantic_fallback_is_triggered_for_missing_required_fields() -> None:
    assert semantic_metadata_service.metadata_needs_semantic_fallback(
        {"title": None, "company": None, "location": "Berlin"}
    )
    assert not semantic_metadata_service.metadata_needs_semantic_fallback(
        {"title": "Data Engineer", "company": "Example GmbH", "location": "Berlin"}
    )


@pytest.mark.asyncio
async def test_semantic_fallback_uses_full_text_and_accepts_evidenced_values(
    monkeypatch,
) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "data": {
                    "status": "succeeded",
                    "outputs": {
                        "metadata_json": (
                            '{"title":{"value":"Machine Learning Engineer",'
                            '"confidence":0.98,"evidence":"Machine Learning Engineer"},'
                            '"company":{"value":"flaschenpost","confidence":0.9,'
                            '"evidence":"wir sind flaschenpost"},'
                            '"location":{"value":"Berlin","confidence":0.99,'
                            '"evidence":"Arbeitsort Berlin"}}'
                        )
                    },
                }
            }

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, **kwargs):
            captured.update(kwargs["json"]["inputs"])
            return FakeResponse()

    monkeypatch.setattr(semantic_metadata_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(
        semantic_metadata_service,
        "get_settings",
        lambda: SimpleNamespace(
            dify_base_url="http://api:5001",
            dify_metadata_workflow_api_key=SecretStr("app-test"),
            dify_metadata_workflow_timeout_seconds=120,
            semantic_metadata_max_characters=15_000,
        ),
    )
    content = (
        "de.indeed.com\nMachine Learning Engineer\nArbeitsort Berlin\n"
        "Spannend und schnell – wir sind flaschenpost!"
    )

    result = await semantic_metadata_service.enrich_job_metadata(
        content,
        source_filename="job_Indeed.com.pdf",
    )

    assert captured["job_content"] == content
    assert result.metadata["title"] == "Machine Learning Engineer"
    assert result.metadata["company"] == "flaschenpost"
    assert result.metadata["location"] == "Berlin"
    assert result.warnings == ["semantic_metadata_fallback_used"]


@pytest.mark.asyncio
async def test_semantic_fallback_does_not_invent_without_evidence(monkeypatch) -> None:
    rules = {
        "title": None,
        "company": None,
        "location": "Berlin",
        "work_model": None,
        "employment_type": None,
        "contract_term": None,
        "published_text": None,
    }
    merged, _ = semantic_metadata_service._accepted_metadata(
        rules,
        {
            "company": {
                "value": "Guessed GmbH",
                "confidence": 0.99,
                "evidence": "",
            }
        },
    )

    assert merged["company"] is None


def test_semantic_work_model_is_not_accepted_from_benefits() -> None:
    rules = {
        "title": "Engineer",
        "company": "Example GmbH",
        "location": "Berlin",
        "work_model": None,
    }
    evidence = "Work-Life Balance – genieße die Freiheit des mobilen Arbeitens"
    merged, _ = semantic_metadata_service._accepted_metadata(
        rules,
        {
            "work_model": {
                "value": "Mobiles Arbeiten",
                "confidence": 1,
                "evidence": evidence,
            }
        },
        content=evidence,
    )

    assert merged["work_model"] is None


def test_semantic_evidence_accepts_pdf_line_breaks() -> None:
    merged, _ = semantic_metadata_service._accepted_metadata(
        {"title": None},
        {
            "title": {
                "value": "Junior Pricing Analyst - Data & Operations",
                "confidence": 0.9,
                "evidence": "Junior Pricing Analyst - Data & Operations",
            }
        },
        content="Junior Pricing Analyst - Data &\nOperations",
    )

    assert merged["title"] == "Junior Pricing Analyst - Data & Operations"
