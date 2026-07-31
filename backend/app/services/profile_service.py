import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.errors import ApplicationError
from app.database.models import (
    Certificate,
    CertificateLocalization,
    EducationEntry,
    EducationLocalization,
    PortfolioProject,
    PortfolioProjectLocalization,
    Profile,
    ProfileEntityRevision,
    ProfileReference,
    ReferenceLocalization,
    Skill,
    SkillLocalization,
    WorkExperience,
    WorkExperienceLocalization,
)
from app.database.session import get_session_factory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResourceDefinition:
    model: type
    localization_model: type
    localization_parent_field: str
    fields: frozenset[str]


RESOURCES = {
    "skills": ResourceDefinition(
        Skill,
        SkillLocalization,
        "skill_id",
        frozenset(
            {
                "canonical_name",
                "category",
                "proficiency_level",
                "years_experience",
                "last_used_at",
                "aliases",
                "active",
                "status",
            }
        ),
    ),
    "experiences": ResourceDefinition(
        WorkExperience,
        WorkExperienceLocalization,
        "work_experience_id",
        frozenset(
            {
                "company",
                "employment_type",
                "start_date",
                "end_date",
                "location",
                "remote_model",
                "status",
            }
        ),
    ),
    "projects": ResourceDefinition(
        PortfolioProject,
        PortfolioProjectLocalization,
        "portfolio_project_id",
        frozenset(
            {
                "canonical_name",
                "project_type",
                "role",
                "start_date",
                "end_date",
                "source_url",
                "repository_url",
                "technologies",
                "status",
            }
        ),
    ),
    "education": ResourceDefinition(
        EducationEntry,
        EducationLocalization,
        "education_entry_id",
        frozenset({"institution", "start_date", "end_date", "location", "status"}),
    ),
    "certificates": ResourceDefinition(
        Certificate,
        CertificateLocalization,
        "certificate_id",
        frozenset(
            {
                "official_name",
                "issuer",
                "issued_at",
                "expires_at",
                "credential_id",
                "verification_url",
                "status",
            }
        ),
    ),
    "references": ResourceDefinition(
        ProfileReference,
        ReferenceLocalization,
        "profile_reference_id",
        frozenset(
            {
                "full_name",
                "organization",
                "email",
                "phone",
                "preferred_language",
                "usage_consent",
                "status",
            }
        ),
    ),
}


def _session_factory():
    factory = get_session_factory()
    if factory is None:
        raise ApplicationError(
            "Profile management requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    return factory


def _columns(row) -> dict[str, Any]:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _serialize(row) -> dict[str, Any]:
    data = _columns(row)
    if hasattr(row, "localizations"):
        data["localizations"] = [
            _columns(item) for item in sorted(row.localizations, key=lambda item: item.language)
        ]
    return jsonable_encoder(data)


def _clean_values(payload: BaseModel, allowed_fields: frozenset[str]) -> tuple[dict, Any, Any]:
    values = payload.model_dump(mode="python", exclude_unset=True)
    localizations = values.pop("localizations", None)
    change_reason = values.pop("change_reason", None)
    values = {key: value for key, value in values.items() if key in allowed_fields}
    if values.get("verification_url") is not None:
        values["verification_url"] = str(values["verification_url"])
    return values, localizations, change_reason


async def _record_revision(
    session,
    *,
    profile_id: UUID,
    entity_type: str,
    row,
    action: str,
    change_reason: str | None,
) -> None:
    session.add(
        ProfileEntityRevision(
            profile_id=profile_id,
            entity_type=entity_type,
            entity_id=row.id,
            revision=row.revision,
            action=action,
            snapshot=_serialize(row),
            change_reason=change_reason,
        )
    )


async def create_profile(payload: BaseModel) -> dict:
    values = payload.model_dump(mode="python")
    change_reason = values.pop("change_reason", None)
    profile = Profile(**values)
    factory = _session_factory()
    async with factory() as session:
        session.add(profile)
        await session.flush()
        await _record_revision(
            session,
            profile_id=profile.id,
            entity_type="profile",
            row=profile,
            action="created",
            change_reason=change_reason,
        )
        await session.commit()
        return _serialize(profile)


async def get_profile(profile_id: UUID) -> dict:
    factory = _session_factory()
    async with factory() as session:
        profile = await session.get(Profile, profile_id)
        if profile is None:
            raise ApplicationError("Profile not found.", code="profile_not_found", status_code=404)
        return _serialize(profile)


async def list_profiles() -> list[dict]:
    factory = _session_factory()
    async with factory() as session:
        profiles = (
            await session.scalars(select(Profile).order_by(Profile.created_at))
        ).all()
        return [_serialize(profile) for profile in profiles]


async def update_profile(profile_id: UUID, payload: BaseModel) -> dict:
    values = payload.model_dump(mode="python", exclude_unset=True)
    change_reason = values.pop("change_reason", None)
    factory = _session_factory()
    async with factory() as session:
        profile = await session.get(Profile, profile_id)
        if profile is None:
            raise ApplicationError("Profile not found.", code="profile_not_found", status_code=404)
        for key, value in values.items():
            setattr(profile, key, value)
        profile.revision += 1
        await session.flush()
        await session.refresh(profile)
        await _record_revision(
            session,
            profile_id=profile.id,
            entity_type="profile",
            row=profile,
            action="updated",
            change_reason=change_reason,
        )
        await session.commit()
        return _serialize(profile)


async def list_resources(profile_id: UUID, resource_type: str) -> list[dict]:
    definition = RESOURCES[resource_type]
    factory = _session_factory()
    async with factory() as session:
        rows = (
            await session.scalars(
                select(definition.model)
                .where(definition.model.profile_id == profile_id)
                .options(selectinload(definition.model.localizations))
                .order_by(definition.model.created_at)
            )
        ).all()
        return [_serialize(row) for row in rows]


async def create_resource(profile_id: UUID, resource_type: str, payload: BaseModel) -> dict:
    definition = RESOURCES[resource_type]
    values, localizations, change_reason = _clean_values(payload, definition.fields)
    row = definition.model(profile_id=profile_id, **values)
    factory = _session_factory()
    try:
        async with factory() as session:
            profile = await session.get(Profile, profile_id)
            if profile is None:
                raise ApplicationError(
                    "Profile not found.", code="profile_not_found", status_code=404
                )
            session.add(row)
            await session.flush()
            for localization in localizations or []:
                session.add(
                    definition.localization_model(
                        **{definition.localization_parent_field: row.id},
                        **localization,
                    )
                )
            profile.revision += 1
            await session.flush()
            await session.refresh(row, ["localizations"])
            await _record_revision(
                session,
                profile_id=profile_id,
                entity_type=resource_type,
                row=row,
                action="created",
                change_reason=change_reason,
            )
            await session.commit()
            return _serialize(row)
    except IntegrityError as exception:
        raise ApplicationError(
            "The profile entry conflicts with an existing entry.",
            code="profile_entry_conflict",
            status_code=409,
        ) from exception


async def update_resource(
    profile_id: UUID,
    resource_type: str,
    item_id: UUID,
    payload: BaseModel,
) -> dict:
    definition = RESOURCES[resource_type]
    values, localizations, change_reason = _clean_values(payload, definition.fields)
    factory = _session_factory()
    try:
        async with factory() as session:
            row = await session.scalar(
                select(definition.model)
                .where(
                    definition.model.id == item_id,
                    definition.model.profile_id == profile_id,
                )
                .options(selectinload(definition.model.localizations))
            )
            if row is None:
                raise ApplicationError(
                    "Profile entry not found.",
                    code="profile_entry_not_found",
                    status_code=404,
                )
            for key, value in values.items():
                setattr(row, key, value)
            if localizations is not None:
                existing = {item.language: item for item in row.localizations}
                for localization in localizations:
                    current = existing.get(localization["language"])
                    if current is None:
                        current = definition.localization_model(
                            **{definition.localization_parent_field: row.id}
                        )
                        session.add(current)
                        row.localizations.append(current)
                    for key, value in localization.items():
                        setattr(current, key, value)
            row.revision += 1
            profile = await session.get(Profile, profile_id)
            profile.revision += 1
            await session.flush()
            await session.refresh(row)
            await session.refresh(row, ["localizations"])
            await _record_revision(
                session,
                profile_id=profile_id,
                entity_type=resource_type,
                row=row,
                action="updated",
                change_reason=change_reason,
            )
            await session.commit()
            return _serialize(row)
    except IntegrityError as exception:
        raise ApplicationError(
            "The profile entry conflicts with an existing entry.",
            code="profile_entry_conflict",
            status_code=409,
        ) from exception
    except SQLAlchemyError as exception:
        logger.exception(
            "profile_entry_update_failed",
            extra={"profile_id": str(profile_id), "resource_type": resource_type},
        )
        raise ApplicationError(
            "The profile entry could not be saved.",
            code="database_unavailable",
            status_code=503,
        ) from exception


async def delete_resource(
    profile_id: UUID,
    resource_type: str,
    item_id: UUID,
) -> None:
    definition = RESOURCES.get(resource_type)
    if definition is None:
        raise ApplicationError(
            "Unsupported profile resource.",
            code="unsupported_profile_resource",
            status_code=404,
        )
    factory = _session_factory()
    try:
        async with factory() as session:
            row = await session.scalar(
                select(definition.model)
                .where(
                    definition.model.id == item_id,
                    definition.model.profile_id == profile_id,
                )
                .options(selectinload(definition.model.localizations))
            )
            if row is None:
                raise ApplicationError(
                    "Profile entry not found.",
                    code="profile_entry_not_found",
                    status_code=404,
                )
            profile = await session.get(Profile, profile_id)
            deleted_revision = row.revision + 1
            snapshot = _serialize(row)
            snapshot["revision"] = deleted_revision
            row.revision = deleted_revision
            profile.revision += 1
            session.add(
                ProfileEntityRevision(
                    profile_id=profile_id,
                    entity_type=resource_type,
                    entity_id=row.id,
                    revision=deleted_revision,
                    action="deleted",
                    snapshot=snapshot,
                    change_reason="In der Profilverwaltung gelöscht.",
                )
            )
            await session.delete(row)
            await session.commit()
    except SQLAlchemyError as exception:
        logger.exception(
            "profile_entry_delete_failed",
            extra={"profile_id": str(profile_id), "resource_type": resource_type},
        )
        raise ApplicationError(
            "The profile entry could not be deleted.",
            code="database_unavailable",
            status_code=503,
        ) from exception


async def list_revisions(profile_id: UUID, entity_type: str, entity_id: UUID) -> list[dict]:
    factory = _session_factory()
    async with factory() as session:
        rows = (
            await session.scalars(
                select(ProfileEntityRevision)
                .where(
                    ProfileEntityRevision.profile_id == profile_id,
                    ProfileEntityRevision.entity_type == entity_type,
                    ProfileEntityRevision.entity_id == entity_id,
                )
                .order_by(ProfileEntityRevision.revision)
            )
        ).all()
        return [_serialize(row) for row in rows]
