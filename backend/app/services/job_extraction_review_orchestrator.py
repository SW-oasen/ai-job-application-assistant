from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult
from app.services.job_extraction_review_decision_service import (
    ReviewedJobExtraction,
    apply_job_extraction_review,
)
from app.services.job_extraction_review_service import review_job_extraction
from app.services.review_service import ReviewService


@dataclass(frozen=True)
class JobExtractionCandidate:
    metadata: dict[str, str | None]
    activities: list[dict[str, Any]]
    requirements: list[dict[str, Any]]


@dataclass(frozen=True)
class JobExtractionReviewOutcome:
    extraction: ReviewedJobExtraction
    review_results: tuple[ReviewResult, ...]


RetryExtractor = Callable[[list[str]], Awaitable[JobExtractionCandidate]]


async def review_job_extraction_with_retry(
    *,
    content: str,
    candidate: JobExtractionCandidate,
    review_service: ReviewService | None = None,
    retry_extractor: RetryExtractor | None = None,
    max_retries: int = 1,
) -> JobExtractionReviewOutcome:
    if max_retries not in {0, 1}:
        raise ValueError("max_retries must be 0 or 1.")
    initial_review = await _review_candidate(
        content=content,
        candidate=candidate,
        review_service=review_service,
    )
    if initial_review.decision != "retry":
        return JobExtractionReviewOutcome(
            extraction=_apply(candidate, initial_review),
            review_results=(initial_review,),
        )
    if max_retries == 0 or retry_extractor is None:
        manual_review = _manual_review_result(
            initial_review,
            "Für die Extraktion ist kein weiterer Retry verfügbar.",
        )
        return JobExtractionReviewOutcome(
            extraction=_apply(candidate, manual_review),
            review_results=(initial_review, manual_review),
        )
    try:
        retried_candidate = await retry_extractor(initial_review.retry_instructions)
    except ApplicationError as exception:
        manual_review = _manual_review_result(initial_review, exception.message)
        return JobExtractionReviewOutcome(
            extraction=_apply(candidate, manual_review),
            review_results=(initial_review, manual_review),
        )
    if _is_less_complete(retried_candidate, candidate):
        manual_review = _manual_review_result(
            initial_review,
            "Der Extraktions-Retry lieferte weniger quellenbasierte Tätigkeiten oder "
            "Anforderungen als der ursprüngliche Kandidat.",
        )
        return JobExtractionReviewOutcome(
            extraction=_apply(candidate, manual_review),
            review_results=(initial_review, manual_review),
        )
    retried_review = await _review_candidate(
        content=content,
        candidate=retried_candidate,
        review_service=review_service,
        attempt=2,
        retry_instructions=initial_review.retry_instructions,
    )
    if retried_review.decision == "retry":
        retried_review = _manual_review_result(
            retried_review,
            "Die maximale Anzahl von einem Extraktions-Retry wurde erreicht.",
        )
    return JobExtractionReviewOutcome(
        extraction=_apply(retried_candidate, retried_review),
        review_results=(initial_review, retried_review),
    )


async def _review_candidate(
    *,
    content: str,
    candidate: JobExtractionCandidate,
    review_service: ReviewService | None,
    attempt: int = 1,
    retry_instructions: list[str] | None = None,
) -> ReviewResult:
    return await review_job_extraction(
        content=content,
        metadata=candidate.metadata,
        activities=candidate.activities,
        requirements=candidate.requirements,
        review_service=review_service,
        attempt=attempt,
        retry_instructions=retry_instructions,
    )


def _apply(candidate: JobExtractionCandidate, review_result: ReviewResult) -> ReviewedJobExtraction:
    return apply_job_extraction_review(
        metadata=candidate.metadata,
        activities=candidate.activities,
        requirements=candidate.requirements,
        review_result=review_result,
    )


def _manual_review_result(review_result: ReviewResult, technical_error: str) -> ReviewResult:
    return review_result.model_copy(
        update={
            "status": "manual_review_required",
            "decision": "manual_review",
            "technical_error": technical_error,
        }
    )


def _is_less_complete(
    candidate: JobExtractionCandidate,
    baseline: JobExtractionCandidate,
) -> bool:
    """A review retry may refine items but must never silently shrink the extraction."""
    return (
        len(candidate.activities) < len(baseline.activities)
        or len(candidate.requirements) < len(baseline.requirements)
    )
