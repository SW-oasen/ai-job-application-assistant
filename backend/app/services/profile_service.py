import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import delete, select
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
    AppliedSkillLink,
    SkillLocalization,
    WorkExperience,
    WorkExperienceLocalization,
)
from app.database.session import get_session_factory


def _derive_target_role_level(role: str) -> str | None:
    value = role.casefold()
    if "principal" in value: return "Principal"
    if "staff" in value: return "Staff"
    if "lead" in value or "leiter" in value or "head" in value: return "Lead"
    if "senior" in value: return "Senior"
    if "junior" in value: return "Junior"
    if "manager" in value: return "Manager"
    return None


def _ensure_target_role_preferences(values: dict) -> dict:
    if "target_role_preferences" not in values and "target_roles" in values:
        values["target_role_preferences"] = [
            {"role": role, "level": _derive_target_role_level(role), "priority": index + 1}
            for index, role in enumerate(values["target_roles"])
        ]
    return values

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResourceDefinition:
    model: type
    localization_model: type
    localization_parent_field: str
    fields: frozenset[str]
    applied_skill_source_type: str | None = None


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
        ), "experience",
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
        ), "project",
    ),
    "education": ResourceDefinition(
        EducationEntry,
        EducationLocalization,
        "education_entry_id",
        frozenset({"institution", "start_date", "end_date", "location", "status"}), "education",
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
        ), "certificate",
    ),
    "references": ResourceDefinition(
        ProfileReference,
        ReferenceLocalization,
        "profile_reference_id",
        frozenset(
            {
                "full_name",
                "organization",
                "job_title",
                "email",
                "phone",
                "linkedin_url",
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


def _clean_values(payload: BaseModel, allowed_fields: frozenset[str]) -> tuple[dict, Any, list[UUID] | None]:
    values = payload.model_dump(mode="python", exclude_unset=True)
    localizations = values.pop("localizations", None)
    applied_skill_ids = values.pop("applied_skill_ids", None)
    values = {key: value for key, value in values.items() if key in allowed_fields}
    for url_field in ("verification_url", "linkedin_url"):
        if values.get(url_field) is not None:
            values[url_field] = str(values[url_field])
    return values, localizations, applied_skill_ids


async def _record_revision(
    session,
    *,
    profile_id: UUID,
    entity_type: str,
    row,
    action: str,
) -> None:
    session.add(
        ProfileEntityRevision(
            profile_id=profile_id,
            entity_type=entity_type,
            entity_id=row.id,
            revision=row.revision,
            action=action,
            snapshot=_serialize(row),
        )
    )


async def create_profile(payload: BaseModel) -> dict:
    values = _ensure_target_role_preferences(payload.model_dump(mode="python"))
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
        )
        await session.commit()
        return _serialize(profile)


async def delete_profile(profile_id: UUID) -> None:
    factory = _session_factory()
    async with factory() as session:
        profile = await session.get(Profile, profile_id)
        if profile is None:
            raise ApplicationError("Profil nicht gefunden.", code="profile_not_found", status_code=404)
        await session.delete(profile)
        await session.commit()


async def import_profile_snapshot(payload: BaseModel, resources: dict[str, list[dict[str, Any]]]) -> dict:
    """Create a fully independent profile from an exported snapshot."""
    values = _ensure_target_role_preferences(payload.model_dump(mode="python"))
    factory = _session_factory()
    resource_names = ("experiences", "education", "certificates", "skills", "projects", "references")
    source_to_new: dict[str, UUID] = {}
    skill_ids: dict[str, UUID] = {}
    pending_applied_skills: list[tuple[object, str, list[object]]] = []
    async with factory() as session:
        try:
            profile = Profile(**values)
            session.add(profile)
            await session.flush()
            for name in resource_names:
                definition = RESOURCES[name]
                allowed = {column.name for column in definition.model.__table__.columns} - {"id", "profile_id", "created_at", "updated_at", "revision"}
                localization_allowed = {column.name for column in definition.localization_model.__table__.columns} - {"id", definition.localization_parent_field}
                for raw in resources.get(name, []):
                    if not isinstance(raw, dict):
                        continue
                    old_id = str(raw.get("id", ""))
                    row = definition.model(profile_id=profile.id, **{key: raw[key] for key in allowed if key in raw})
                    session.add(row)
                    await session.flush()
                    if old_id:
                        source_to_new[old_id] = row.id
                        if name == "skills":
                            skill_ids[old_id] = row.id
                    if definition.applied_skill_source_type:
                        pending_applied_skills.append((row, definition.applied_skill_source_type, raw.get("applied_skill_ids", [])))
                    for localization in raw.get("localizations", []):
                        if isinstance(localization, dict):
                            session.add(definition.localization_model(**{definition.localization_parent_field: row.id}, **{key: localization[key] for key in localization_allowed if key in localization}))
            for row, source_type, raw_skill_ids in pending_applied_skills:
                mapped_skill_ids = [skill_ids[str(item)] for item in raw_skill_ids if str(item) in skill_ids]
                await _sync_applied_skills(session, profile.id, row, source_type, mapped_skill_ids)
            await _record_revision(session, profile_id=profile.id, entity_type="profile", row=profile, action="created")
            await session.commit()
            return _serialize(profile)
        except Exception:
            await session.rollback()
            raise


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
    values = _ensure_target_role_preferences(payload.model_dump(mode="python", exclude_unset=True))
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
        result = [_serialize(row) for row in rows]
        if definition.applied_skill_source_type and result:
            links = (await session.scalars(
                select(AppliedSkillLink).where(
                    AppliedSkillLink.source_resource_type == definition.applied_skill_source_type,
                    AppliedSkillLink.source_resource_id.in_([row.id for row in rows]),
                )
            )).all()
            skill_ids_by_resource: dict[UUID, list[UUID]] = {}
            for link in links:
                skill_ids_by_resource.setdefault(link.source_resource_id, []).append(link.skill_id)
            for item in result:
                item["applied_skill_ids"] = skill_ids_by_resource.get(UUID(item["id"]), [])
        return result


async def _sync_applied_skills(session, profile_id: UUID, row, source_type: str, skill_ids: list[UUID]) -> None:
    unique_ids = list(dict.fromkeys(skill_ids))
    if unique_ids:
        found_ids = set((await session.scalars(
            select(Skill.id).where(Skill.profile_id == profile_id, Skill.id.in_(unique_ids))
        )).all())
        if found_ids != set(unique_ids):
            raise ApplicationError("Applied skills must belong to the selected profile.", code="profile_entry_not_found", status_code=404)
    await session.execute(delete(AppliedSkillLink).where(
        AppliedSkillLink.source_resource_type == source_type,
        AppliedSkillLink.source_resource_id == row.id,
    ))
    session.add_all(AppliedSkillLink(skill_id=skill_id, source_resource_type=source_type, source_resource_id=row.id) for skill_id in unique_ids)


async def create_resource(profile_id: UUID, resource_type: str, payload: BaseModel) -> dict:
    definition = RESOURCES[resource_type]
    values, localizations, applied_skill_ids = _clean_values(payload, definition.fields)
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
            if definition.applied_skill_source_type:
                await _sync_applied_skills(session, profile_id, row, definition.applied_skill_source_type, applied_skill_ids or [])
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
    values, localizations, applied_skill_ids = _clean_values(payload, definition.fields)
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
            if definition.applied_skill_source_type and applied_skill_ids is not None:
                await _sync_applied_skills(session, profile_id, row, definition.applied_skill_source_type, applied_skill_ids)
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
            if definition.applied_skill_source_type:
                await session.execute(delete(AppliedSkillLink).where(
                    AppliedSkillLink.source_resource_type == definition.applied_skill_source_type,
                    AppliedSkillLink.source_resource_id == row.id,
                ))
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
