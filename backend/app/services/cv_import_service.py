import calendar
import re
import unicodedata
from datetime import UTC, date, datetime
from uuid import UUID

import json5
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import ApplicationError
from app.database.models import CvImportBatch, CvImportSuggestion, Profile
from app.domain.skill_taxonomy import normalize_skill_category, normalize_skill_level
from app.schemas.cv_import import (
    CvImportCreate,
    CvSuggestionInput,
    CvSuggestionReview,
    PortfolioSourceImportCreate,
    StructuredCvImportCreate,
    StructuredPortfolioImportCreate,
)
from app.schemas.profile import (
    CertificateCreate,
    CertificateUpdate,
    EducationCreate,
    EducationUpdate,
    PortfolioProjectCreate,
    PortfolioProjectUpdate,
    ProfileUpdate,
    ReferenceCreate,
    ReferenceUpdate,
    SkillCreate,
    SkillUpdate,
    WorkExperienceCreate,
    WorkExperienceUpdate,
)
from app.services.profile_service import (
    RESOURCES,
    _serialize,
    _session_factory,
    create_resource,
    update_profile,
    update_resource,
)

CREATE_SCHEMAS = {
    "skills": SkillCreate,
    "experiences": WorkExperienceCreate,
    "projects": PortfolioProjectCreate,
    "education": EducationCreate,
    "certificates": CertificateCreate,
    "references": ReferenceCreate,
}

MONTH_YEAR_PATTERN = re.compile(r"^\s*(0?[1-9]|1[0-2])[\s./-]+(\d{4})\s*$")
YEAR_MONTH_PATTERN = re.compile(r"^\s*(\d{4})-(0?[1-9]|1[0-2])\s*$")
NAMED_MONTH_YEAR_PATTERN = re.compile(
    r"^\s*([A-Za-zÄÖÜäöüß]+)\.?\s+(\d{4})\s*$"
)
MONTH_NAMES = {
    "jan": 1,
    "januar": 1,
    "january": 1,
    "feb": 2,
    "februar": 2,
    "february": 2,
    "mär": 3,
    "märz": 3,
    "mrz": 3,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "mai": 5,
    "may": 5,
    "jun": 6,
    "juni": 6,
    "june": 6,
    "jul": 7,
    "juli": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "okt": 10,
    "oktober": 10,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dez": 12,
    "dezember": 12,
    "dec": 12,
    "december": 12,
}


def _normalize_cv_date(value: object, *, end_of_month: bool = False) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        pass
    year_month_match = YEAR_MONTH_PATTERN.fullmatch(text)
    numeric_match = MONTH_YEAR_PATTERN.fullmatch(text)
    if year_month_match:
        year = int(year_month_match.group(1))
        month = int(year_month_match.group(2))
    elif numeric_match:
        month = int(numeric_match.group(1))
        year = int(numeric_match.group(2))
    else:
        named_match = NAMED_MONTH_YEAR_PATTERN.fullmatch(text)
        if not named_match:
            return None
        month = MONTH_NAMES.get(named_match.group(1).casefold())
        if month is None:
            return None
        year = int(named_match.group(2))
    day = calendar.monthrange(year, month)[1] if end_of_month else 1
    return date(year, month, day).isoformat()
UPDATE_SCHEMAS = {
    "skills": SkillUpdate,
    "experiences": WorkExperienceUpdate,
    "projects": PortfolioProjectUpdate,
    "education": EducationUpdate,
    "certificates": CertificateUpdate,
    "references": ReferenceUpdate,
}

IGNORED_COMPARISON_FIELDS = {"status", "revision", "id", "profile_id"}


def _normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    normalized = "".join(
        character if character.isalnum() else " "
        for character in text
        if not unicodedata.combining(character)
    )
    return " ".join(normalized.split())


def _localization_title(data: dict) -> str:
    localizations = data.get("localizations") or []
    return _normalized_text(localizations[0].get("title")) if localizations else ""


def _identity_key(resource_type: str, data: dict) -> tuple[str, ...] | None:
    if resource_type == "profile":
        return ("profile",)
    if resource_type == "skills":
        name = _normalized_text(data.get("canonical_name"))
        return (name,) if name else None
    if resource_type == "experiences":
        company = _normalized_text(data.get("company"))
        title = _localization_title(data)
        return (company, title) if company and title else None
    if resource_type == "projects":
        name = _normalized_text(data.get("canonical_name"))
        return (name,) if name else None
    if resource_type == "education":
        institution = _normalized_text(data.get("institution"))
        title = _localization_title(data)
        return (institution, title) if institution and title else None
    if resource_type == "certificates":
        name = _normalized_text(data.get("official_name"))
        issuer = _normalized_text(data.get("issuer"))
        return (name, issuer) if name and issuer else None
    if resource_type == "references":
        email = _normalized_text(data.get("email"))
        if email:
            return ("email", email)
        name = _normalized_text(data.get("full_name"))
        organization = _normalized_text(data.get("organization"))
        return ("name", name, organization) if name else None
    return None


def _comparable_value(value):
    if isinstance(value, str):
        return _normalized_text(value)
    if isinstance(value, list):
        return [_comparable_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _comparable_value(item)
            for key, item in value.items()
            if key not in IGNORED_COMPARISON_FIELDS and item is not None
        }
    return value


def _differences(proposed: dict, existing: dict) -> list[dict]:
    differences = []
    for field, proposed_value in proposed.items():
        if field in IGNORED_COMPARISON_FIELDS or proposed_value is None:
            continue
        existing_value = existing.get(field)
        if _comparable_value(proposed_value) != _comparable_value(existing_value):
            differences.append(
                {
                    "field": field,
                    "existing": existing_value,
                    "proposed": proposed_value,
                }
            )
    return differences


def _conflict_details(proposed: dict, matched: dict | None) -> dict:
    if matched is None:
        return {
            "conflict_status": "none",
            "matched_entity": None,
            "differences": [],
        }
    differences = _differences(proposed, matched)
    return {
        "conflict_status": "conflict" if differences else "duplicate",
        "matched_entity": matched,
        "differences": differences,
    }


async def _load_match_candidates(session, profile_id: UUID) -> dict[str, list[dict]]:
    profile = await session.get(Profile, profile_id)
    candidates: dict[str, list[dict]] = {"profile": [_serialize(profile)] if profile else []}
    for resource_type, definition in RESOURCES.items():
        rows = (
            await session.scalars(
                select(definition.model)
                .where(definition.model.profile_id == profile_id)
                .options(selectinload(definition.model.localizations))
            )
        ).all()
        candidates[resource_type] = [_serialize(row) for row in rows]
    return candidates


def _find_matching_entity(
    resource_type: str,
    proposed: dict,
    candidates: dict[str, list[dict]],
) -> dict | None:
    proposed_key = _identity_key(resource_type, proposed)
    if proposed_key is None:
        return None
    return next(
        (
            candidate
            for candidate in candidates.get(resource_type, [])
            if _identity_key(resource_type, candidate) == proposed_key
        ),
        None,
    )


def _candidate_by_id(
    resource_type: str,
    entity_id: object,
    candidates: dict[str, list[dict]],
) -> dict | None:
    if not entity_id:
        return None
    return next(
        (
            candidate
            for candidate in candidates.get(resource_type, [])
            if str(candidate.get("id")) == str(entity_id)
        ),
        None,
    )


async def create_cv_import(profile_id: UUID, payload: CvImportCreate) -> dict:
    factory = _session_factory()
    async with factory() as session:
        if await session.get(Profile, profile_id) is None:
            raise ApplicationError("Profile not found.", code="profile_not_found", status_code=404)
        candidates = await _load_match_candidates(session, profile_id)
        batch = CvImportBatch(
            profile_id=profile_id,
            source_filename=payload.source_filename,
            content_hash=payload.content_hash,
            source_language=payload.source_language,
            source_metadata=payload.source_metadata,
        )
        session.add(batch)
        await session.flush()
        suggestions = []
        for item in payload.suggestions:
            matched_entity_id = item.matched_entity_id
            if matched_entity_id is None:
                match = _find_matching_entity(
                    item.resource_type,
                    item.proposed_data,
                    candidates,
                )
                matched_entity_id = str(match["id"]) if match else None
            suggestion = CvImportSuggestion(
                batch_id=batch.id,
                profile_id=profile_id,
                resource_type=item.resource_type,
                proposed_data=item.proposed_data,
                source_excerpt=item.source_excerpt,
                confidence=item.confidence,
                matched_entity_id=matched_entity_id,
            )
            session.add(suggestion)
            suggestions.append(suggestion)
        await session.commit()
        return {
            **_serialize(batch),
            "suggestions": [_serialize(item) for item in suggestions],
        }


async def create_structured_cv_import(
    profile_id: UUID,
    payload: StructuredCvImportCreate,
) -> dict:
    suggestions = _structured_cv_to_suggestions(
        payload.structured_cv,
        payload.source_language,
    )
    if not suggestions:
        raise ApplicationError(
            "The structured CV contains no supported profile facts.",
            code="cv_contains_no_profile_facts",
            status_code=422,
        )
    return await create_cv_import(
        profile_id,
        CvImportCreate(
            source_filename=payload.source_filename,
            content_hash=payload.content_hash,
            source_language=payload.source_language,
            source_metadata={
                "profile_summary_ignored": True,
                "adapter": "dify-import-cv-v2",
            },
            suggestions=suggestions,
        ),
    )


async def create_structured_portfolio_import(
    profile_id: UUID,
    payload: StructuredPortfolioImportCreate,
) -> dict:
    suggestions = _structured_portfolio_to_suggestions(
        payload.projects,
        payload.source_language,
    )
    if not suggestions:
        raise ApplicationError(
            "Der Portfolio-Import enthält keine Projekte mit einem Namen.",
            code="portfolio_contains_no_projects",
            status_code=422,
        )
    return await create_cv_import(
        profile_id,
        CvImportCreate(
            source_filename=payload.source_name,
            source_language=payload.source_language,
            source_metadata={
                "adapter": "structured-portfolio-v1",
                "source_kind": "portfolio",
            },
            suggestions=suggestions,
        ),
    )


async def create_portfolio_source_import(
    profile_id: UUID,
    payload: PortfolioSourceImportCreate,
) -> dict:
    projects = _parse_projects_javascript(payload.source_content, payload.export_name)
    suggestions = _portfolio_projects_to_suggestions(projects)
    if not suggestions:
        raise ApplicationError(
            "PROJECTS enthält keine importierbaren Projekte.",
            code="portfolio_contains_no_projects",
            status_code=422,
        )
    return await create_cv_import(
        profile_id,
        CvImportCreate(
            source_filename=payload.source_name,
            source_language=None,
            source_metadata={
                "adapter": "portfolio-projects-js-v1",
                "source_kind": "portfolio",
                "export_name": payload.export_name,
            },
            suggestions=suggestions,
        ),
    )


async def list_cv_imports(profile_id: UUID) -> list[dict]:
    factory = _session_factory()
    async with factory() as session:
        candidates = await _load_match_candidates(session, profile_id)
        batches = (
            await session.scalars(
                select(CvImportBatch)
                .where(CvImportBatch.profile_id == profile_id)
                .order_by(CvImportBatch.created_at.desc())
            )
        ).all()
        suggestions = (
            await session.scalars(
                select(CvImportSuggestion)
                .where(CvImportSuggestion.profile_id == profile_id)
                .order_by(CvImportSuggestion.created_at)
            )
        ).all()
        by_batch: dict[UUID, list[dict]] = {}
        for item in suggestions:
            serialized = _serialize(item)
            matched = _candidate_by_id(
                serialized["resource_type"],
                serialized.get("matched_entity_id"),
                candidates,
            )
            if matched is None:
                matched = _find_matching_entity(
                    serialized["resource_type"],
                    serialized["proposed_data"],
                    candidates,
                )
                if matched:
                    serialized["matched_entity_id"] = matched["id"]
            serialized.update(_conflict_details(serialized["proposed_data"], matched))
            by_batch.setdefault(item.batch_id, []).append(serialized)
        return [
            {**_serialize(batch), "suggestions": by_batch.get(batch.id, [])}
            for batch in batches
        ]


async def apply_cv_suggestion(
    profile_id: UUID,
    suggestion_id: UUID,
    review: CvSuggestionReview,
) -> dict:
    suggestion = await _get_pending_suggestion(profile_id, suggestion_id)
    proposed_data = review.proposed_data or suggestion["proposed_data"]
    resource_type = suggestion["resource_type"]
    matched_entity_id = suggestion["matched_entity_id"]
    match = await _current_match(
        profile_id,
        resource_type,
        matched_entity_id,
        proposed_data,
    )
    if match and not matched_entity_id:
        matched_entity_id = match["id"]
    conflict = _conflict_details(proposed_data, match)
    if match and review.resolution is None:
        raise ApplicationError(
            "Für ein Duplikat oder einen Konflikt muss eine Auflösung gewählt werden.",
            code="cv_conflict_resolution_required",
            status_code=409,
        )
    if review.resolution == "create_new" and resource_type in {"profile", "skills"}:
        raise ApplicationError(
            "Dieser Eintragstyp kann nicht als weiteres Exemplar angelegt werden.",
            code="cv_create_new_not_allowed",
            status_code=409,
        )
    if review.resolution == "keep_existing":
        return await _complete_without_profile_change(
            suggestion_id,
            match,
            review,
            conflict["conflict_status"],
        )
    if resource_type == "profile":
        payload = ProfileUpdate.model_validate(proposed_data)
        applied = await update_profile(profile_id, payload)
    elif matched_entity_id and review.resolution != "create_new":
        payload = UPDATE_SCHEMAS[resource_type].model_validate(proposed_data)
        applied = await update_resource(
            profile_id,
            resource_type,
            UUID(str(matched_entity_id)),
            payload,
        )
    else:
        payload = CREATE_SCHEMAS[resource_type].model_validate(proposed_data)
        applied = await create_resource(profile_id, resource_type, payload)

    factory = _session_factory()
    async with factory() as session:
        row = await session.get(CvImportSuggestion, suggestion_id)
        row.proposed_data = proposed_data
        row.status = "applied"
        row.applied_entity_id = UUID(str(applied["id"]))
        row.review_note = review.review_note
        row.reviewed_at = datetime.now(UTC)
        await session.commit()
        return {**_serialize(row), "applied_entry": applied}


async def _current_match(
    profile_id: UUID,
    resource_type: str,
    matched_entity_id: object,
    proposed_data: dict,
) -> dict | None:
    factory = _session_factory()
    async with factory() as session:
        candidates = await _load_match_candidates(session, profile_id)
        return _candidate_by_id(
            resource_type,
            matched_entity_id,
            candidates,
        ) or _find_matching_entity(resource_type, proposed_data, candidates)


async def _complete_without_profile_change(
    suggestion_id: UUID,
    matched: dict | None,
    review: CvSuggestionReview,
    conflict_status: str,
) -> dict:
    if matched is None:
        raise ApplicationError(
            "Der zuvor erkannte Profileintrag existiert nicht mehr.",
            code="cv_matched_entry_not_found",
            status_code=409,
        )
    factory = _session_factory()
    async with factory() as session:
        row = await session.get(CvImportSuggestion, suggestion_id)
        row.status = "applied"
        row.applied_entity_id = UUID(str(matched["id"]))
        row.review_note = review.review_note or "Bestehenden Profileintrag beibehalten"
        row.reviewed_at = datetime.now(UTC)
        await session.commit()
        return {
            **_serialize(row),
            "applied_entry": matched,
            "resolution": "keep_existing",
            "conflict_status": conflict_status,
        }


async def reject_cv_suggestion(
    profile_id: UUID,
    suggestion_id: UUID,
    review: CvSuggestionReview,
) -> dict:
    await _get_pending_suggestion(profile_id, suggestion_id)
    factory = _session_factory()
    async with factory() as session:
        row = await session.get(CvImportSuggestion, suggestion_id)
        row.status = "rejected"
        row.review_note = review.review_note
        row.reviewed_at = datetime.now(UTC)
        await session.commit()
        return _serialize(row)


async def _get_pending_suggestion(profile_id: UUID, suggestion_id: UUID) -> dict:
    factory = _session_factory()
    async with factory() as session:
        row = await session.scalar(
            select(CvImportSuggestion).where(
                CvImportSuggestion.id == suggestion_id,
                CvImportSuggestion.profile_id == profile_id,
            )
        )
        if row is None:
            raise ApplicationError(
                "CV import suggestion not found.",
                code="cv_suggestion_not_found",
                status_code=404,
            )
        if row.status != "pending":
            raise ApplicationError(
                "The CV import suggestion was already reviewed.",
                code="cv_suggestion_already_reviewed",
                status_code=409,
            )
        return _serialize(row)


def _structured_cv_to_suggestions(
    document: dict,
    language: str,
) -> list[CvSuggestionInput]:
    suggestions: list[CvSuggestionInput] = []
    profile = document.get("profile") or {}
    profile_data = {
        "full_name": str(profile.get("name") or "").strip() or None,
        "nationality": str(profile.get("nationality") or "").strip() or None,
        "phone": str(profile.get("phone") or "").strip() or None,
        "email": str(profile.get("email") or "").strip() or None,
        "linkedin_url": str(profile.get("linkedin") or "").strip() or None,
        "github_url": str(profile.get("github") or "").strip() or None,
        "portfolio_url": str(profile.get("portfolio") or "").strip() or None,
    }
    profile_data = {key: value for key, value in profile_data.items() if value}
    if profile_data:
        suggestions.append(
            CvSuggestionInput(
                resource_type="profile",
                proposed_data=profile_data,
                source_excerpt="Stabile Kontakt- und Profillinks aus dem CV",
            )
        )
    skills = document.get("skills") or {}
    for category in skills.get("categories") or []:
        source_category = category.get("category") or "Uncategorized"
        category_name = normalize_skill_category(source_category)
        for name in category.get("skills") or []:
            if str(name).strip():
                suggestions.append(
                    CvSuggestionInput(
                        resource_type="skills",
                        proposed_data={
                            "canonical_name": str(name).strip(),
                            "category": category_name,
                            "status": "draft",
                            "localizations": [
                                {
                                    "language": language,
                                    "title": str(name).strip(),
                                    "status": "draft",
                                }
                            ],
                        },
                        source_excerpt=f"{source_category}: {name}",
                    )
                )
    for item in skills.get("languages") or []:
        name = str(item.get("language") or "").strip()
        if name:
            suggestions.append(
                CvSuggestionInput(
                    resource_type="skills",
                    proposed_data={
                        "canonical_name": name,
                        "category": "natural_languages",
                        "proficiency_level": normalize_skill_level(item.get("level")),
                        "status": "draft",
                        "localizations": [
                            {
                                "language": language,
                                "title": name,
                                "status": "draft",
                            }
                        ],
                    },
                    source_excerpt=f"{name}: {item.get('level') or ''}".strip(": "),
                )
            )
    for item in document.get("work_experience") or []:
        company = str(item.get("company") or "").strip()
        title = str(item.get("job_title") or "").strip()
        if company and title:
            source_start = str(item.get("start_date") or "").strip()
            source_end = str(item.get("end_date") or "").strip()
            suggestions.append(
                CvSuggestionInput(
                    resource_type="experiences",
                    proposed_data={
                        "company": company,
                        "start_date": _normalize_cv_date(source_start),
                        "end_date": _normalize_cv_date(source_end, end_of_month=True),
                        "status": "draft",
                        "localizations": [
                            {
                                "language": language,
                                "title": title,
                                "bullets": item.get("activities") or [],
                                "status": "draft",
                            }
                        ],
                    },
                    source_excerpt=(
                        f"{title} · {company} · {source_start}–{source_end}"
                    ).strip(" ·–"),
                )
            )
    for item in document.get("education") or []:
        institution = str(item.get("institution") or "").strip()
        title = str(item.get("qualification") or "").strip()
        if institution and title:
            field = str(item.get("field") or "").strip()
            source_end = str(item.get("date") or "").strip()
            suggestions.append(
                CvSuggestionInput(
                    resource_type="education",
                    proposed_data={
                        "institution": institution,
                        "start_date": None,
                        "end_date": _normalize_cv_date(source_end, end_of_month=True),
                        "status": "draft",
                        "localizations": [
                            {
                                "language": language,
                                "title": title,
                                "summary": field or None,
                                "status": "draft",
                            }
                        ],
                    },
                    source_excerpt=f"{title} · {institution} · {source_end}".strip(" ·"),
                )
            )
    for item in document.get("certificates") or []:
        name = str(item.get("name") or "").strip()
        issuer = str(item.get("institution") or "").strip()
        if name and issuer:
            source_date = str(item.get("date") or "").strip()
            suggestions.append(
                CvSuggestionInput(
                    resource_type="certificates",
                    proposed_data={
                        "official_name": name,
                        "issuer": issuer,
                        "issued_at": _normalize_cv_date(source_date),
                        "status": "draft",
                        "localizations": [
                            {
                                "language": language,
                                "title": name,
                                "status": "draft",
                            }
                        ],
                    },
                    source_excerpt=f"{name} · {issuer} · {source_date}".strip(" ·"),
                )
            )
    for item in document.get("references") or []:
        name = str(item.get("name") or "").strip()
        if name:
            title = str(item.get("job_title") or "").strip()
            linkedin = str(item.get("linkedin") or "").strip()
            suggestions.append(
                CvSuggestionInput(
                    resource_type="references",
                    proposed_data={
                        "full_name": name,
                        "organization": item.get("company") or None,
                        "usage_consent": False,
                        "status": "draft",
                        "localizations": [
                                {
                                    "language": language,
                                    "title": title or name,
                                    "summary": linkedin or None,
                                    "status": "draft",
                                }
                        ],
                    },
                    source_excerpt=f"{name} · {item.get('company') or ''}".strip(" ·"),
                )
            )
    return suggestions


def _structured_portfolio_to_suggestions(
    projects: list[dict],
    language: str,
) -> list[CvSuggestionInput]:
    suggestions: list[CvSuggestionInput] = []
    for item in projects:
        name = str(item.get("name") or item.get("canonical_name") or "").strip()
        if not name:
            continue
        title = str(item.get("title") or name).strip()
        summary = str(item.get("summary") or item.get("description") or "").strip()
        raw_bullets = item.get("bullets") or item.get("highlights") or []
        if isinstance(raw_bullets, str):
            raw_bullets = raw_bullets.splitlines()
        bullets = [
            str(value).strip()
            for value in raw_bullets
            if str(value).strip()
        ]
        raw_technologies = item.get("technologies") or item.get("tech_stack") or []
        if isinstance(raw_technologies, str):
            raw_technologies = raw_technologies.split(",")
        technologies = [
            str(value).strip()
            for value in raw_technologies
            if str(value).strip()
        ]
        proposed_data = {
            "canonical_name": name,
            "project_type": str(item.get("project_type") or "").strip() or None,
            "role": str(item.get("role") or "").strip() or None,
            "start_date": _normalize_cv_date(item.get("start_date")),
            "end_date": _normalize_cv_date(item.get("end_date"), end_of_month=True),
            "source_url": str(item.get("source_url") or item.get("url") or "").strip()
            or None,
            "repository_url": str(
                item.get("repository_url") or item.get("repository") or ""
            ).strip()
            or None,
            "technologies": technologies,
            "status": "draft",
            "localizations": [
                {
                    "language": language,
                    "title": title,
                    "summary": summary or None,
                    "bullets": bullets,
                    "status": "draft",
                }
            ],
        }
        suggestions.append(
            CvSuggestionInput(
                resource_type="projects",
                proposed_data=proposed_data,
                source_excerpt=" · ".join(
                    value for value in (name, ", ".join(technologies)) if value
                ),
            )
        )
    return suggestions


def _extract_javascript_literal(source: str, export_name: str) -> str:
    declaration = re.search(
        rf"(?:export\s+)?const\s+{re.escape(export_name)}\s*=",
        source,
    )
    if declaration is None:
        raise ApplicationError(
            f"Die JavaScript-Konstante {export_name} wurde nicht gefunden.",
            code="portfolio_export_not_found",
            status_code=422,
        )
    start = next(
        (
            index
            for index in range(declaration.end(), len(source))
            if source[index] in "[{"
        ),
        None,
    )
    if start is None:
        raise ApplicationError(
            f"{export_name} enthält kein Objekt oder Array.",
            code="portfolio_literal_not_found",
            status_code=422,
        )

    pairs = {"[": "]", "{": "}"}
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = start
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if line_comment:
            if char in "\r\n":
                line_comment = False
        elif block_comment:
            if char == "*" and following == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == "/" and following == "/":
            line_comment = True
            index += 1
        elif char == "/" and following == "*":
            block_comment = True
            index += 1
        elif char in pairs:
            stack.append(pairs[char])
        elif char in "]}":
            if not stack or char != stack.pop():
                raise ApplicationError(
                    f"Ungültige Klammerung in {export_name}.",
                    code="invalid_portfolio_javascript",
                    status_code=422,
                )
            if not stack:
                return source[start : index + 1]
        index += 1
    raise ApplicationError(
        f"{export_name} ist nicht vollständig geschlossen.",
        code="incomplete_portfolio_javascript",
        status_code=422,
    )


def _parse_projects_javascript(source: str, export_name: str = "PROJECTS") -> list[dict]:
    literal = _extract_javascript_literal(source, export_name)
    try:
        parsed = json5.loads(literal)
    except ValueError as exc:
        raise ApplicationError(
            f"{export_name} konnte nicht als JavaScript-Objektliteral gelesen werden: {exc}",
            code="invalid_portfolio_javascript",
            status_code=422,
        ) from exc
    if not isinstance(parsed, list):
        raise ApplicationError(
            f"{export_name} muss ein Array sein.",
            code="portfolio_export_must_be_array",
            status_code=422,
        )
    return [item for item in parsed if isinstance(item, dict)]


def _portfolio_projects_to_suggestions(
    projects: list[dict],
) -> list[CvSuggestionInput]:
    suggestions: list[CvSuggestionInput] = []
    for item in projects:
        translations = item.get("translations") or {}
        localizations = []
        for language in ("de", "en"):
            translation = translations.get(language) or {}
            title = str(translation.get("title") or "").strip()
            if not title:
                continue
            localizations.append(
                {
                    "language": language,
                    "title": title,
                    "summary": str(translation.get("summary") or "").strip() or None,
                    "bullets": [
                        str(value).strip()
                        for value in translation.get("highlights") or []
                        if str(value).strip()
                    ],
                    "status": "draft",
                }
            )
        name = str(item.get("id") or "").strip()
        if not name or not localizations:
            continue
        resources = item.get("resources") or {}
        date_value = str(item.get("date") or "").strip()
        proposed_data = {
            "canonical_name": name,
            "project_type": ", ".join(
                str(value).strip()
                for value in item.get("tags") or []
                if str(value).strip()
            )
            or None,
            "role": None,
            "start_date": None,
            "end_date": _normalize_cv_date(date_value, end_of_month=True),
            "source_url": str(resources.get("live") or "").strip() or None,
            "repository_url": str(resources.get("repo") or "").strip() or None,
            "technologies": [
                str(value).strip()
                for value in item.get("stack") or []
                if str(value).strip()
            ],
            "status": "draft",
            "localizations": localizations,
        }
        suggestions.append(
            CvSuggestionInput(
                resource_type="projects",
                proposed_data=proposed_data,
                source_excerpt=" · ".join(
                    value
                    for value in (
                        localizations[0]["title"],
                        ", ".join(proposed_data["technologies"]),
                    )
                    if value
                ),
            )
        )
    return suggestions
