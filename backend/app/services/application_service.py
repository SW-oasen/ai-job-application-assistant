from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.errors import ApplicationError
from app.database.models import (
    Application,
    ApplicationEvent,
    Company,
    Job,
    Profile,
)
from app.database.session import get_session_factory
from app.schemas.applications import (
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationEventUpdate,
    ApplicationUpdate,
)
from app.services.matching_service import _job_metadata


def _session_factory():
    factory = get_session_factory()
    if factory is None:
        raise ApplicationError(
            "Application tracking requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    return factory


def _event_dict(event: ApplicationEvent) -> dict:
    return {
        "id": str(event.id),
        "application_id": str(event.application_id),
        "event_type": event.event_type,
        "status": event.status,
        "occurred_at": event.occurred_at,
        "channel": event.channel,
        "portal_name": event.portal_name,
        "contact_person": event.contact_person,
        "note": event.note,
        "created_at": event.created_at,
    }


def _application_dict(
    application: Application,
    job: Job,
    company: Company | None,
    profile: Profile,
) -> dict:
    metadata = _job_metadata(job, company)
    return {
        "id": str(application.id),
        "job_id": str(job.id),
        "profile_id": str(profile.id),
        "status": application.status,
        "applied_at": application.applied_at,
        "application_channel": application.application_channel,
        "application_portal_name": application.application_portal_name,
        "response_channel": application.response_channel,
        "response_portal_name": application.response_portal_name,
        "status_changed_at": application.status_changed_at,
        "next_action": application.next_action,
        "next_action_at": application.next_action_at,
        "notes": application.notes,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "job": {
            "id": str(job.id),
            "title": job.title or "Unbenannte Stelle",
            **metadata,
            "source_url": job.source_url,
            "source_filename": job.source_filename,
            "published_at": job.published_at,
            "imported_at": job.imported_at,
        },
        "profile": {
            "id": str(profile.id),
            "display_name": profile.display_name,
        },
    }


def _apply_status(
    application: Application,
    *,
    status: str,
    occurred_at: datetime,
    channel: str | None,
    portal_name: str | None,
) -> None:
    application.status = status
    application.status_changed_at = occurred_at
    if status == "applied":
        application.applied_at = application.applied_at or occurred_at
        application.application_channel = channel or application.application_channel
        application.application_portal_name = (
            portal_name if channel == "job_portal" else None
        )
    elif status == "followed_up":
        application.applied_at = application.applied_at or occurred_at
        application.response_channel = channel or application.response_channel
        application.response_portal_name = (
            portal_name if channel == "job_portal" else None
        )
    elif channel:
        application.response_channel = channel
        application.response_portal_name = (
            portal_name if channel == "job_portal" else None
        )


async def _rebuild_application_state(session, application: Application) -> None:
    events = (
        await session.scalars(
            select(ApplicationEvent)
            .where(ApplicationEvent.application_id == application.id)
            .order_by(ApplicationEvent.occurred_at, ApplicationEvent.created_at)
        )
    ).all()
    state_events = [
        event
        for event in events
        if event.event_type in {"created", "status_change"} and event.status
    ]
    if not state_events:
        application.status = "draft"
        application.status_changed_at = application.created_at
        application.applied_at = None
        application.application_channel = None
        application.application_portal_name = None
        application.response_channel = None
        application.response_portal_name = None
        application.notes = next(
            (event.note for event in reversed(events) if event.note),
            None,
        )
        return
    latest = state_events[-1]
    application.status = latest.status
    application.status_changed_at = latest.occurred_at
    applied_events = [event for event in state_events if event.status == "applied"]
    application.applied_at = (
        applied_events[0].occurred_at
        if applied_events
        else next(
            (
                event.occurred_at
                for event in state_events
                if event.status == "followed_up"
            ),
            None,
        )
    )
    application.application_channel = next(
        (event.channel for event in applied_events if event.channel),
        None,
    )
    application.application_portal_name = next(
        (
            event.portal_name
            for event in applied_events
            if event.channel == "job_portal" and event.portal_name
        ),
        None,
    )
    application.response_channel = next(
        (
            event.channel
            for event in reversed(events)
            if event.channel and event.status != "applied"
        ),
        None,
    )
    application.response_portal_name = next(
        (
            event.portal_name
            for event in reversed(events)
            if event.channel == "job_portal" and event.status != "applied"
        ),
        None,
    )
    application.notes = next(
        (event.note for event in reversed(events) if event.note),
        None,
    )


async def create_application(payload: ApplicationCreate) -> dict:
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    async with _session_factory()() as session:
        if await session.get(Job, payload.job_id) is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        if await session.get(Profile, payload.profile_id) is None:
            raise ApplicationError(
                "Profile not found.", code="profile_not_found", status_code=404
            )
        application = Application(
            job_id=payload.job_id,
            profile_id=payload.profile_id,
            status=payload.status,
            next_action=payload.next_action,
            next_action_at=payload.next_action_at,
            notes=payload.note,
        )
        _apply_status(
            application,
            status=payload.status,
            occurred_at=occurred_at,
            channel=payload.channel,
            portal_name=payload.portal_name,
        )
        session.add(application)
        try:
            await session.flush()
        except IntegrityError as exception:
            raise ApplicationError(
                "For this job and profile an application already exists.",
                code="application_already_exists",
                status_code=409,
            ) from exception
        session.add(
            ApplicationEvent(
                application_id=application.id,
                event_type="created",
                status=payload.status,
                occurred_at=occurred_at,
                channel=payload.channel,
                portal_name=payload.portal_name,
                contact_person=payload.contact_person,
                note=payload.note,
            )
        )
        await session.commit()
        return await get_application(application.id)


async def update_application(application_id, payload: ApplicationUpdate) -> dict:
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    async with _session_factory()() as session:
        application = await session.get(Application, application_id)
        if application is None:
            raise ApplicationError(
                "Application not found.", code="application_not_found", status_code=404
            )
        if payload.event_type in {"created", "status_change"} and payload.status is not None:
            _apply_status(
                application,
                status=payload.status,
                occurred_at=occurred_at,
                channel=payload.channel,
                portal_name=payload.portal_name,
            )
            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    event_type="status_change",
                    status=payload.status,
                    occurred_at=occurred_at,
                    channel=payload.channel,
                    portal_name=payload.portal_name,
                    note=payload.note,
                )
            )
        elif payload.note or payload.channel:
            session.add(
                ApplicationEvent(
                    application_id=application.id,
                    event_type="communication",
                    status=application.status,
                    occurred_at=occurred_at,
                    channel=payload.channel,
                    portal_name=payload.portal_name,
                    note=payload.note,
                )
            )
        if "next_action" in payload.model_fields_set:
            application.next_action = payload.next_action
        if "next_action_at" in payload.model_fields_set:
            application.next_action_at = payload.next_action_at
        if payload.note:
            application.notes = payload.note
        await session.commit()
    return await get_application(application_id)


async def add_application_event(application_id, payload: ApplicationEventCreate) -> dict:
    occurred_at = payload.occurred_at or datetime.now(timezone.utc)
    async with _session_factory()() as session:
        application = await session.get(Application, application_id)
        if application is None:
            raise ApplicationError(
                "Application not found.", code="application_not_found", status_code=404
            )
        if payload.status is not None:
            _apply_status(
                application,
                status=payload.status,
                occurred_at=occurred_at,
                channel=payload.channel,
                portal_name=payload.portal_name,
            )
        event = ApplicationEvent(
            application_id=application.id,
            event_type=payload.event_type,
            status=payload.status,
            occurred_at=occurred_at,
            channel=payload.channel,
            portal_name=payload.portal_name,
            contact_person=payload.contact_person,
            note=payload.note,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return _event_dict(event)


async def update_application_event(
    application_id,
    event_id,
    payload: ApplicationEventUpdate,
) -> dict:
    async with _session_factory()() as session:
        application = await session.get(Application, application_id)
        if application is None:
            raise ApplicationError(
                "Application not found.", code="application_not_found", status_code=404
            )
        event = await session.get(ApplicationEvent, event_id)
        if event is None or event.application_id != application.id:
            raise ApplicationError(
                "Application event not found.",
                code="application_event_not_found",
                status_code=404,
            )
        if payload.event_type is not None:
            event.event_type = payload.event_type
        event.status = payload.status
        event.occurred_at = payload.occurred_at
        event.channel = payload.channel
        event.portal_name = (
            payload.portal_name if payload.channel == "job_portal" else None
        )
        event.contact_person = payload.contact_person
        event.note = payload.note
        await _rebuild_application_state(session, application)
        await session.commit()
    return await get_application(application_id)


async def delete_application_event(application_id, event_id) -> None:
    async with _session_factory()() as session:
        application = await session.get(Application, application_id)
        if application is None:
            raise ApplicationError(
                "Application not found.", code="application_not_found", status_code=404
            )
        event = await session.get(ApplicationEvent, event_id)
        if event is None or event.application_id != application.id:
            raise ApplicationError(
                "Application event not found.",
                code="application_event_not_found",
                status_code=404,
            )
        await session.delete(event)
        await session.flush()
        await _rebuild_application_state(session, application)
        await session.commit()


async def get_application(application_id) -> dict:
    async with _session_factory()() as session:
        row = (
            await session.execute(
                select(Application, Job, Company, Profile)
                .join(Job, Job.id == Application.job_id)
                .outerjoin(Company, Company.id == Job.company_id)
                .join(Profile, Profile.id == Application.profile_id)
                .where(Application.id == application_id)
            )
        ).one_or_none()
        if row is None:
            raise ApplicationError(
                "Application not found.", code="application_not_found", status_code=404
            )
        application, job, company, profile = row
        events = (
            await session.scalars(
                select(ApplicationEvent)
                .where(ApplicationEvent.application_id == application.id)
                .order_by(ApplicationEvent.occurred_at.desc())
            )
        ).all()
        return {
            "application": _application_dict(application, job, company, profile),
            "events": [_event_dict(event) for event in events],
        }


async def get_application_for_job(job_id, profile_id) -> dict:
    async with _session_factory()() as session:
        application_id = await session.scalar(
            select(Application.id).where(
                Application.job_id == job_id,
                Application.profile_id == profile_id,
            )
        )
    if application_id is None:
        return {"application": None, "events": []}
    return await get_application(application_id)


async def list_applications(profile_id=None) -> list[dict]:
    async with _session_factory()() as session:
        statement = (
            select(Application, Job, Company, Profile)
            .join(Job, Job.id == Application.job_id)
            .outerjoin(Company, Company.id == Job.company_id)
            .join(Profile, Profile.id == Application.profile_id)
            .order_by(Application.updated_at.desc())
        )
        if profile_id is not None:
            statement = statement.where(Application.profile_id == profile_id)
        rows = (await session.execute(statement)).all()
        return [
            _application_dict(application, job, company, profile)
            for application, job, company, profile in rows
        ]
