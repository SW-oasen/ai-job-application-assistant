from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from app.schemas.matching import (
    JobMetadataUpdate,
    MatchingContextResponse,
    MatchingRequest,
    MatchingResponse,
    MatchingWorkflowRequest,
)
from app.services.dify_matching_service import run_matching_workflow
from app.services.matching_service import (
    delete_matching_job,
    evaluate_matching,
    get_matching_context,
    get_matching_job,
    get_stored_matching,
    get_target_fit,
    list_matching_jobs,
    update_job_metadata,
)

router = APIRouter(prefix="/matching", tags=["matching"])
ADMIN_PAGE = Path(__file__).resolve().parents[2] / "static" / "matching-admin.html"


@router.get("/admin", include_in_schema=False)
async def matching_admin() -> FileResponse:
    return FileResponse(ADMIN_PAGE)


@router.get("/jobs")
async def matching_jobs(profile_id: UUID | None = None) -> list[dict]:
    return await list_matching_jobs(profile_id)


@router.get("/jobs/{job_id}")
async def matching_job(job_id: UUID) -> dict:
    return await get_matching_job(job_id)


@router.patch("/jobs/{job_id}/metadata")
async def edit_job_metadata(job_id: UUID, payload: JobMetadataUpdate) -> dict:
    return await update_job_metadata(job_id, payload)


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: UUID) -> Response:
    await delete_matching_job(job_id)
    return Response(status_code=204)


@router.get("/results")
async def matching_results(job_id: UUID, profile_id: UUID) -> dict:
    return await get_stored_matching(job_id, profile_id)


@router.get("/target-fit")
async def target_fit(job_id: UUID, profile_id: UUID) -> dict:
    return await get_target_fit(job_id, profile_id)


@router.get("/context", response_model=MatchingContextResponse)
async def matching_context(job_id: UUID, profile_id: UUID) -> MatchingContextResponse:
    return await get_matching_context(job_id, profile_id)


@router.post("/evaluate", response_model=MatchingResponse)
async def match_job_to_profile(payload: MatchingRequest) -> MatchingResponse:
    return await evaluate_matching(payload)


@router.post("/run")
async def run_matching(payload: MatchingWorkflowRequest) -> dict:
    return await run_matching_workflow(payload)
