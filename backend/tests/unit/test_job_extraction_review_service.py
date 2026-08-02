import pytest

from app.schemas.review import ReviewResult
from app.services.job_extraction_review_service import review_job_extraction


class FakeReviewService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def review(self, **kwargs) -> ReviewResult:
        self.calls.append(kwargs)
        return ReviewResult(
            review_type="job_extraction",
            status="accepted",
            decision="accept",
            overall_confidence=0.91,
        )


@pytest.mark.asyncio
async def test_job_extraction_review_delegates_combined_extraction_to_review_service() -> None:
    service = FakeReviewService()
    result = await review_job_extraction(
        content="## Anforderungen\n- Erfahrung mit Python",
        metadata={"title": "Data Engineer", "company": "Example GmbH"},
        activities=[{"activity": "Datenpipelines entwickeln"}],
        requirements=[{"requirement": "Erfahrung mit Python"}],
        review_service=service,
    )

    assert result.review_type == "job_extraction"
    assert result.status == "accepted"
    assert result.decision == "accept"
    assert result.overall_confidence == 0.91
    assert service.calls == [
        {
            "review_type": "job_extraction",
            "source_data": {"job_content": "## Anforderungen\n- Erfahrung mit Python"},
            "generated_result": {
                "metadata": {"title": "Data Engineer", "company": "Example GmbH"},
                "activities": [{"activity": "Datenpipelines entwickeln"}],
                "requirements": [{"requirement": "Erfahrung mit Python"}],
            },
        }
    ]