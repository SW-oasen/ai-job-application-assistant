from uuid import UUID

from fastapi import APIRouter

from app.schemas.applications import (
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationEventUpdate,
    ApplicationUpdate,
)
from app.services.application_service import (
    add_application_event,
    create_application,
    get_application,
    get_application_for_job,
    list_applications,
    update_application,
    update_application_event,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
async def applications(profile_id: UUID | None = None) -> list[dict]:
    return await list_applications(profile_id)


@router.post("", status_code=201)
async def create_application_entry(payload: ApplicationCreate) -> dict:
    return await create_application(payload)


@router.get("/by-job/{job_id}")
async def application_for_job(job_id: UUID, profile_id: UUID) -> dict:
    return await get_application_for_job(job_id, profile_id)


@router.get("/{application_id}")
async def application(application_id: UUID) -> dict:
    return await get_application(application_id)


@router.patch("/{application_id}")
async def update_application_entry(
    application_id: UUID,
    payload: ApplicationUpdate,
) -> dict:
    return await update_application(application_id, payload)


@router.post("/{application_id}/events", status_code=201)
async def create_application_event(
    application_id: UUID,
    payload: ApplicationEventCreate,
) -> dict:
    return await add_application_event(application_id, payload)


@router.patch("/{application_id}/events/{event_id}")
async def update_application_event_entry(
    application_id: UUID,
    event_id: UUID,
    payload: ApplicationEventUpdate,
) -> dict:
    return await update_application_event(application_id, event_id, payload)
