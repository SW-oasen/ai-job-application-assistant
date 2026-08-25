from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.services import semantic_metadata_service


def test_semantic_fallback_is_triggered_for_missing_required_fields() -> None:
    assert semantic_metadata_service.metadata_needs_semantic_fallback(
        {"title": None, "company": None, "location": "Berlin"}
    )


def test_extracts_siemens_energy_stacked_location_fields() -> None:
    rules = semantic_metadata_service.extract_job_metadata(
        "# Data & AI Engineer (w/m/d)\n\n"
        "**Standort**\n\nDeutschland\n\nBerlin\n\nBerlin\n",
        source_url="https://jobs.siemens-energy.com/de_DE/jobs/FolderDetail/Data-AI-Engineer-w-m-d/301905",
    )

    assert rules["location"] == "Berlin"


def test_uses_job_opening_when_main_heading_is_generic() -> None:
    rules = semantic_metadata_service.extract_job_metadata(
        "# Einleitung\n\n"
        "Zum nächstmöglichen Zeitpunkt suchen wir dich als Zeitarbeitnehmer:in "
        "im Auftrag der DB System GmbH für einen Einsatz als Softwareentwickler:in "
        "für die Echtzeit-Optimierung des Fahrplans (w/m/d) am Standort Berlin."
    )

    assert rules["title"] == "Softwareentwickler:in für die Echtzeit-Optimierung des Fahrplans"


def test_repairs_mojibake_in_title_from_job_opening() -> None:
    rules = semantic_metadata_service.extract_job_metadata(
        "# Einleitung\n\n"
        "Wir suchen dich für einen Einsatz als Softwareentwickler:in fÃ¼r "
        "die Echtzeit-Optimierung des Fahrplans (w/m/d) am Standort Berlin."
    )

    assert rules["title"] == "Softwareentwickler:in für die Echtzeit-Optimierung des Fahrplans"
    assert not semantic_metadata_service.metadata_needs_semantic_fallback(
        {
            "title": "Data Engineer",
            "company": "Example GmbH",
            "location": "Berlin",
            "language": "en",
        }
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
                            '"evidence":"Arbeitsort Berlin"},'
                            '"language":{"value":"de","confidence":0.99,'
                            '"evidence":"wir sind flaschenpost"}}'
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
    assert result.metadata["language"] == "de"
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


def test_semantic_language_only_accepts_supported_codes() -> None:
    content = "Nous recherchons une personne"
    merged, _ = semantic_metadata_service._accepted_metadata(
        {"language": None},
        {
            "language": {
                "value": "fr",
                "confidence": 1,
                "evidence": content,
            }
        },
        content=content,
    )

    assert merged["language"] is None


def test_semantic_fallback_replaces_an_overlong_rule_based_company() -> None:
    overlong_company = "DB Zeitarbeit GmbH " + ("Einleitung " * 40)
    rules = {
        "title": "Einleitung",
        "company": overlong_company,
        "location": None,
        "language": "de",
    }

    assert semantic_metadata_service.metadata_needs_semantic_fallback(rules)

    merged, _ = semantic_metadata_service._accepted_metadata(
        rules,
        {
            "company": {
                "value": "DB Zeitarbeit GmbH",
                "confidence": 1,
                "evidence": "Wir, die DB Zeitarbeit GmbH, sind der interne Personaldienstleister.",
            }
        },
        content="Wir, die DB Zeitarbeit GmbH, sind der interne Personaldienstleister.",
    )

    assert merged["company"] == "DB Zeitarbeit GmbH"


def test_semantic_company_accepts_value_when_long_evidence_was_reformatted() -> None:
    merged, _ = semantic_metadata_service._accepted_metadata(
        {"company": None},
        {
            "company": {
                "value": "DB Zeitarbeit GmbH",
                "confidence": 1,
                "evidence": (
                    "Wir, die DB Zeitarbeit GmbH, sind der interne "
                    "Personaldienstleister der Deutschen Bahn AG."
                ),
            }
        },
        content="DB Zeitarbeit GmbH\nDein Sprungbrett in den DB-Konzern.",
    )

    assert merged["company"] == "DB Zeitarbeit GmbH"
