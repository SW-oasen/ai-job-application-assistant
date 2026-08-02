from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult
from app.services.job_extraction_review_orchestrator import (
    JobExtractionCandidate,
    review_job_extraction_with_retry,
)
from app.services.review_service import ReviewService
from app.services.review_history_service import store_review_result


@dataclass(frozen=True)
class JobExtractionReviewIntegrationResult:
    metadata: dict[str, str | None]
    activities: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    review_results: tuple[ReviewResult, ...]


async def review_job_extraction_if_configured(
    *,
    content: str,
    metadata: dict[str, str | None],
    activities: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    review_service: ReviewService | None = None,
) -> JobExtractionReviewIntegrationResult:
    service = review_service or ReviewService()
    if not service.is_configured("job_extraction"):
        return JobExtractionReviewIntegrationResult(metadata, activities, requirements, ())
    try:
        outcome = await review_job_extraction_with_retry(
            content=content,
            candidate=JobExtractionCandidate(metadata, activities, requirements),
            review_service=service,
        )
    except ApplicationError as error:
        failed_review = ReviewResult(
            review_type="job_extraction",
            status="failed",
            technical_error=f"{error.code}: {error.message}",
        )
        return JobExtractionReviewIntegrationResult(
            metadata, activities, requirements, (failed_review,)
        )
    return JobExtractionReviewIntegrationResult(
        metadata=outcome.extraction.metadata,
        activities=outcome.extraction.activities,
        requirements=outcome.extraction.requirements,
        review_results=outcome.review_results,
    )


async def store_job_extraction_review_history(
    *,
    job_id: str,
    original_metadata: dict[str, str | None],
    original_activities: list[dict[str, Any]],
    original_requirements: list[dict[str, Any]],
    reviewed: JobExtractionReviewIntegrationResult,
) -> None:
    source_result = {
        "metadata": original_metadata,
        "activities": original_activities,
        "requirements": original_requirements,
    }
    final_result = {
        "metadata": reviewed.metadata,
        "activities": reviewed.activities,
        "requirements": reviewed.requirements,
    }
    for review_result in reviewed.review_results:
        await store_review_result(
            subject_type="job",
            subject_id=UUID(job_id),
            source_result=source_result,
            review_result=review_result,
            final_result=final_result,
        )