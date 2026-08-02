from typing import Any

from app.schemas.review import ReviewResult
from app.services.review_service import ReviewService


async def review_job_extraction(
    *,
    content: str,
    metadata: dict[str, str | None],
    activities: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    review_service: ReviewService | None = None,
    attempt: int = 1,
    retry_instructions: list[str] | None = None,
) -> ReviewResult:
    service = review_service or ReviewService()
    review_kwargs: dict[str, Any] = {
        "review_type": "job_extraction",
        "source_data": {
            "job_content": content,
        },
        "generated_result": {
            "metadata": metadata,
            "activities": activities,
            "requirements": requirements,
        },
    }
    if attempt != 1:
        review_kwargs["attempt"] = attempt
    if retry_instructions:
        review_kwargs["retry_instructions"] = retry_instructions
    return (await service.review(**review_kwargs)).model_copy(update={"attempt": attempt})