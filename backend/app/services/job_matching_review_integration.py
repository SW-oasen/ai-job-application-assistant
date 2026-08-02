from uuid import UUID

from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult
from app.services.job_matching_review_service import review_job_matching
from app.services.matching_service import get_stored_matching
from app.services.review_history_service import store_review_result
from app.services.review_service import ReviewService


async def review_stored_job_matching_if_configured(
    *,
    job_id: UUID,
    profile_id: UUID,
    review_service: ReviewService | None = None,
) -> None:
    service = review_service or ReviewService()
    if not service.is_configured("job_matching"):
        return
    matching = await get_stored_matching(job_id, profile_id)
    generated_result = {
        "matches": matching["matches"],
        "qualification_fit": matching["qualification_fit"],
        "target_fit": matching["target_fit"],
        "recommendation": matching["recommendation"],
    }
    try:
        review_result = await review_job_matching(
            job=matching["job"],
            profile=matching["profile"],
            matches=matching["matches"],
            qualification_fit=matching["qualification_fit"],
            target_fit=matching["target_fit"],
            recommendation=matching["recommendation"],
            review_service=service,
        )
    except ApplicationError as error:
        review_result = ReviewResult(
            review_type="job_matching",
            status="failed",
            technical_error=f"{error.code}: {error.message}",
        )
    final_result = review_result.corrected_result or generated_result
    await store_review_result(
        subject_type="job",
        subject_id=job_id,
        source_result=generated_result,
        review_result=review_result,
        final_result=final_result,
        context={"profile_id": str(profile_id)},
    )