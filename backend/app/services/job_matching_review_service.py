from typing import Any

from app.schemas.review import ReviewResult
from app.services.review_service import ReviewService


async def review_job_matching(
    *,
    job: dict[str, Any],
    profile: dict[str, Any],
    matches: list[dict[str, Any]],
    qualification_fit: dict[str, Any],
    target_fit: dict[str, Any],
    recommendation: dict[str, Any],
    review_service: ReviewService | None = None,
    attempt: int = 1,
    retry_instructions: list[str] | None = None,
) -> ReviewResult:
    service = review_service or ReviewService()
    review_kwargs: dict[str, Any] = {
        "review_type": "job_matching",
        "source_data": {
            "job": job,
            "profile": profile,
        },
        "generated_result": {
            "matches": matches,
            "qualification_fit": qualification_fit,
            "target_fit": target_fit,
            "recommendation": recommendation,
        },
    }
    if attempt != 1:
        review_kwargs["attempt"] = attempt
    if retry_instructions:
        review_kwargs["retry_instructions"] = retry_instructions
    return (await service.review(**review_kwargs)).model_copy(update={"attempt": attempt})