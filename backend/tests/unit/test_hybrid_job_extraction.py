import pytest

from app.parsers.job_structure import ExtractedJobStructure
from app.services import hybrid_job_extraction


class FakeProvider:
    model = "test"
    dimension = 2

    def embed_batch(self, texts):
        return [[1.0, 0.0] if "responsibility" in text or "develop" in text else [0.0, 1.0] for text in texts]


@pytest.mark.asyncio
async def test_semantic_fallback_adds_unclassified_requirement(monkeypatch) -> None:
    monkeypatch.setattr(hybrid_job_extraction, "create_embedding_provider", lambda settings: FakeProvider())
    monkeypatch.setattr(hybrid_job_extraction, "extract_job_structure", lambda content: ExtractedJobStructure([], [], []))
    result = await hybrid_job_extraction.extract_job_structure_hybrid("- Python skills and experience")
    assert result.requirements[0]["requirement"] == "Python skills and experience"


@pytest.mark.asyncio
async def test_semantic_fallback_reclassifies_items_when_requirements_are_missing(monkeypatch) -> None:
    class Provider:
        def embed_batch(self, texts):
            return [[1.0, 0.0] if "qualification" in text.lower() else [0.0, 1.0] for text in texts]

    monkeypatch.setattr(hybrid_job_extraction, "create_embedding_provider", lambda settings: Provider())
    monkeypatch.setattr(
        hybrid_job_extraction,
        "extract_job_structure",
        lambda content: ExtractedJobStructure(
            [{"activity": "Test software"}], [], []
        ),
    )
    result = await hybrid_job_extraction.extract_job_structure_hybrid(
        "- Test software\n- IT qualification required"
    )
    assert any(item["requirement"] == "IT qualification required" for item in result.requirements)
