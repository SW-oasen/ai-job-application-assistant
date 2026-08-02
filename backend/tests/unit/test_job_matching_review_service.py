import pytest

from app.schemas.review import ReviewResult
from app.services.job_matching_review_service import review_job_matching


class FakeReviewService:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def review(self, **kwargs) -> ReviewResult:
        self.calls.append(kwargs)
        return ReviewResult(
            review_type="job_matching",
            status="accepted",
            decision="accept",
            overall_confidence=0.88,
        )


@pytest.mark.asyncio
async def test_job_matching_review_delegates_full_matching_contract() -> None:
    service = FakeReviewService()
    job = {"id": "job-1", "title": "Data Engineer"}
    profile = {"id": "profile-1", "display_name": "Ada Example"}
    matches = [{"requirement": "Kubernetes", "match_level": "partial_match"}]
    qualification_fit = {"score": 65}
    target_fit = {"score": 80}
    recommendation = {"headline": "Bewerbung erwägen"}

    result = await review_job_matching(
        job=job,
        profile=profile,
        matches=matches,
        qualification_fit=qualification_fit,
        target_fit=target_fit,
        recommendation=recommendation,
        review_service=service,
    )

    assert result.review_type == "job_matching"
    assert result.status == "accepted"
    assert result.overall_confidence == 0.88
    assert service.calls == [
        {
            "review_type": "job_matching",
            "source_data": {"job": job, "profile": profile},
            "generated_result": {
                "matches": matches,
                "qualification_fit": qualification_fit,
                "target_fit": target_fit,
                "recommendation": recommendation,
            },
        }
    ]