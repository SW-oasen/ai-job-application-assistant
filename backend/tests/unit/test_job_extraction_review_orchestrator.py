import pytest

from app.schemas.review import ReviewResult
from app.services.job_extraction_review_orchestrator import (
    JobExtractionCandidate,
    review_job_extraction_with_retry,
)


class FakeReviewService:
    def __init__(self, results: list[ReviewResult]) -> None:
        self.results = results
        self.calls: list[dict] = []

    async def review(self, **kwargs) -> ReviewResult:
        self.calls.append(kwargs)
        return self.results.pop(0)


def _candidate(requirement: str = "Python") -> JobExtractionCandidate:
    return JobExtractionCandidate(
        metadata={"title": "Data Engineer", "company": "Example GmbH"},
        activities=[{"activity": "Datenpipelines entwickeln"}],
        requirements=[{"requirement": requirement}],
    )


@pytest.mark.asyncio
async def test_retry_runs_extractor_once_with_review_feedback() -> None:
    service = FakeReviewService(
        [
            ReviewResult(
                review_type="job_extraction",
                status="retry_requested",
                decision="retry",
                retry_instructions=["Prüfe fehlende Docker-Anforderung."],
            ),
            ReviewResult(
                review_type="job_extraction",
                status="accepted",
                decision="accept",
            ),
        ]
    )
    received_instructions: list[list[str]] = []

    async def retry_extractor(instructions: list[str]) -> JobExtractionCandidate:
        received_instructions.append(instructions)
        return _candidate("Docker")

    outcome = await review_job_extraction_with_retry(
        content="Stellenanzeige",
        candidate=_candidate(),
        review_service=service,
        retry_extractor=retry_extractor,
    )

    assert received_instructions == [["Prüfe fehlende Docker-Anforderung."]]
    assert [result.attempt for result in outcome.review_results] == [1, 2]
    assert outcome.extraction.requirements == [{"requirement": "Docker"}]
    assert service.calls[1]["attempt"] == 2
    assert service.calls[1]["retry_instructions"] == ["Prüfe fehlende Docker-Anforderung."]


@pytest.mark.asyncio
async def test_second_retry_requires_manual_review() -> None:
    service = FakeReviewService(
        [
            ReviewResult(
                review_type="job_extraction",
                status="retry_requested",
                decision="retry",
                retry_instructions=["Prüfe Anforderungen erneut."],
            ),
            ReviewResult(
                review_type="job_extraction",
                status="retry_requested",
                decision="retry",
                attempt=2,
            ),
        ]
    )

    async def retry_extractor(instructions: list[str]) -> JobExtractionCandidate:
        return _candidate("Docker")

    outcome = await review_job_extraction_with_retry(
        content="Stellenanzeige",
        candidate=_candidate(),
        review_service=service,
        retry_extractor=retry_extractor,
    )

    assert outcome.extraction.requires_manual_review is True
    assert outcome.review_results[-1].status == "manual_review_required"
    assert "maximale Anzahl" in outcome.review_results[-1].technical_error


@pytest.mark.asyncio
async def test_missing_retry_extractor_requires_manual_review() -> None:
    service = FakeReviewService(
        [
            ReviewResult(
                review_type="job_extraction",
                status="retry_requested",
                decision="retry",
            )
        ]
    )

    outcome = await review_job_extraction_with_retry(
        content="Stellenanzeige",
        candidate=_candidate(),
        review_service=service,
    )

    assert outcome.extraction.requires_manual_review is True
    assert len(outcome.review_results) == 2


@pytest.mark.asyncio
async def test_retry_limit_zero_requires_manual_review_without_callback() -> None:
    service = FakeReviewService(
        [
            ReviewResult(
                review_type="job_extraction",
                status="retry_requested",
                decision="retry",
            )
        ]
    )

    outcome = await review_job_extraction_with_retry(
        content="Stellenanzeige",
        candidate=_candidate(),
        review_service=service,
        retry_extractor=lambda instructions: _candidate(),
        max_retries=0,
    )

    assert outcome.extraction.requires_manual_review is True