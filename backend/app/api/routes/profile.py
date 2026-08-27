import asyncio
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.domain.skill_taxonomy import SKILL_CATEGORIES, SKILL_LEVELS
from app.schemas.cv_import import (
    CvImportCreate,
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
    ProfileCreate,
    ProfileUpdate,
    ReferenceCreate,
    ReferenceUpdate,
    SkillCreate,
    SkillUpdate,
    WorkExperienceCreate,
    WorkExperienceUpdate,
)
from app.services.cv_import_service import (
    apply_cv_suggestion,
    create_cv_import,
    create_portfolio_source_import,
    create_structured_cv_import,
    create_structured_portfolio_import,
    list_cv_imports,
    reject_cv_suggestion,
)
from app.services.dify_cv_service import import_cv_pdf_with_dify
from app.services.master_profile_service import (
    get_current_master_profile,
    import_master_profile,
    list_master_profile_versions,
    list_master_profiles,
)
from app.services.profile_service import (
    create_profile,
    create_resource,
    delete_profile,
    delete_resource,
    get_profile,
    import_profile_snapshot,
    list_profiles,
    list_resources,
    list_revisions,
    update_profile,
    update_resource,
)
from app.parsers.profile_snapshot import parse_profile_snapshot, parse_profile_snapshot_with_resources, render_profile_snapshot

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/admin", include_in_schema=False)
async def profile_admin() -> RedirectResponse:
    """Retire the former standalone editor in favour of /manage."""
    return RedirectResponse(url="/manage", status_code=308)


@router.get("")
async def get_profiles() -> list[dict]:
    return await list_profiles()


@router.get("/taxonomy/skills")
async def get_skill_taxonomy() -> dict:
    return {
        "categories": SKILL_CATEGORIES,
        "levels": SKILL_LEVELS,
    }


@router.post("")
async def create_profile_entry(payload: ProfileCreate) -> dict:
    return await create_profile(payload)


@router.get("/{profile_id}/export.md")
async def export_profile_snapshot(profile_id: UUID) -> Response:
    profile = await get_profile(profile_id)
    resources = await asyncio.gather(
        list_resources(profile_id, "experiences"),
        list_resources(profile_id, "education"),
        list_resources(profile_id, "certificates"),
        list_resources(profile_id, "skills"),
        list_resources(profile_id, "projects"),
        list_resources(profile_id, "references"),
    )
    profile["resources"] = dict(zip(
        ("experiences", "education", "certificates", "skills", "projects", "references"),
        resources,
    ))
    content = render_profile_snapshot(profile)
    safe_name = "".join(char if char.isalnum() or char in "-_ ." else "_" for char in (profile.get("display_name") or "profil")).strip() or "profil"
    filename = f"profile-export-{safe_name}.md"
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/snapshot-preview")
async def preview_profile_snapshot(file: UploadFile = File(...)) -> dict:
    try:
        profile = parse_profile_snapshot((await file.read()).decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ApplicationError("Die Profilsicherung ist keine gültige UTF-8-Datei.", code="invalid_profile_snapshot", status_code=422) from exc
    except ValueError as exc:
        raise ApplicationError(str(exc), code="invalid_profile_snapshot", status_code=422) from exc
    return {"valid": True, "profile": jsonable_encoder(profile.model_dump())}


@router.post("/import")
async def import_profile_snapshot_entry(file: UploadFile = File(...), display_name: str | None = Form(None)) -> dict:
    try:
        profile, resources = parse_profile_snapshot_with_resources((await file.read()).decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ApplicationError("Die Profilsicherung ist keine gültige UTF-8-Datei.", code="invalid_profile_snapshot", status_code=422) from exc
    except ValueError as exc:
        raise ApplicationError(str(exc), code="invalid_profile_snapshot", status_code=422) from exc
    if display_name:
        profile = profile.model_copy(update={"display_name": display_name.strip()})
    existing = await list_profiles()
    if any(item["display_name"].casefold() == profile.display_name.casefold() for item in existing):
        if not display_name:
            suffix = 1
            suggestion = f"{profile.display_name} (Import)"
            names = {item["display_name"].casefold() for item in existing}
            while suggestion.casefold() in names:
                suffix += 1
                suggestion = f"{profile.display_name} (Import {suffix})"
            return {"requires_name_confirmation": True, "suggested_display_name": suggestion}
        raise ApplicationError("Der gewählte Profilname ist bereits vorhanden.", code="duplicate_profile_name", status_code=409)
    return await import_profile_snapshot(profile, resources)


@router.get("/{profile_id}")
async def get_profile_entry(profile_id: UUID) -> dict:
    return await get_profile(profile_id)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile_entry(profile_id: UUID) -> Response:
    await delete_profile(profile_id)
    return Response(status_code=204)


@router.patch("/{profile_id}")
async def update_profile_entry(profile_id: UUID, payload: ProfileUpdate) -> dict:
    return await update_profile(profile_id, payload)


@router.get("/{profile_id}/cv-imports")
async def get_cv_imports(profile_id: UUID) -> list[dict]:
    return await list_cv_imports(profile_id)


@router.get("/{profile_id}/master-profiles")
async def get_master_profiles(profile_id: UUID) -> list[dict]:
    return await list_master_profiles(profile_id)


@router.get("/{profile_id}/master-profiles/{language}")
async def get_current_master_profile_entry(profile_id: UUID, language: str) -> dict:
    return await get_current_master_profile(profile_id, language)


@router.get("/{profile_id}/master-profiles/{language}/versions")
async def get_master_profile_versions(profile_id: UUID, language: str) -> list[dict]:
    return await list_master_profile_versions(profile_id, language)


@router.post("/{profile_id}/master-profiles")
async def import_master_profile_entry(
    profile_id: UUID,
    language: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> dict:
    return await import_master_profile(
        profile_id=profile_id,
        language=language,
        filename=Path(file.filename or "master_profile.md").name,
        content=await file.read(),
    )


@router.post("/{profile_id}/cv-imports")
async def create_cv_import_entry(profile_id: UUID, payload: CvImportCreate) -> dict:
    return await create_cv_import(profile_id, payload)


@router.post("/{profile_id}/cv-imports/structured")
async def create_structured_cv_import_entry(
    profile_id: UUID,
    payload: StructuredCvImportCreate,
) -> dict:
    return await create_structured_cv_import(profile_id, payload)


@router.post("/{profile_id}/portfolio-imports/structured")
async def create_structured_portfolio_import_entry(
    profile_id: UUID,
    payload: StructuredPortfolioImportCreate,
) -> dict:
    return await create_structured_portfolio_import(profile_id, payload)


@router.post("/{profile_id}/portfolio-imports/source")
async def create_portfolio_source_import_entry(
    profile_id: UUID,
    payload: PortfolioSourceImportCreate,
) -> dict:
    return await create_portfolio_source_import(profile_id, payload)


@router.post("/{profile_id}/cv-imports/pdf")
async def create_cv_pdf_import_entry(
    profile_id: UUID,
    file: Annotated[UploadFile, File()],
    source_language: Annotated[str, Form()] = "de",
) -> dict:
    if source_language not in {"de", "en"}:
        raise ApplicationError(
            "source_language must be de or en.",
            code="invalid_source_language",
            status_code=422,
        )
    filename = Path(file.filename or "lebenslauf.pdf").name
    if file.content_type != "application/pdf" or not filename.lower().endswith(".pdf"):
        raise ApplicationError(
            "Bitte genau eine PDF-Datei auswählen.",
            code="unsupported_cv_file",
            status_code=415,
        )
    content = await file.read()
    if not content:
        raise ApplicationError(
            "Die ausgewählte PDF-Datei ist leer.",
            code="empty_cv_file",
            status_code=422,
        )
    if len(content) > get_settings().pdf_import_max_bytes:
        raise ApplicationError(
            "Die CV-PDF überschreitet die erlaubte Dateigröße.",
            code="cv_file_too_large",
            status_code=413,
        )
    return await import_cv_pdf_with_dify(
        profile_id=profile_id,
        filename=filename,
        content=content,
        source_language=source_language,
    )


@router.post("/{profile_id}/cv-suggestions/{suggestion_id}/apply")
async def apply_cv_import_suggestion(
    profile_id: UUID,
    suggestion_id: UUID,
    payload: CvSuggestionReview,
) -> dict:
    return await apply_cv_suggestion(profile_id, suggestion_id, payload)


@router.post("/{profile_id}/cv-suggestions/{suggestion_id}/reject")
async def reject_cv_import_suggestion(
    profile_id: UUID,
    suggestion_id: UUID,
    payload: CvSuggestionReview,
) -> dict:
    return await reject_cv_suggestion(profile_id, suggestion_id, payload)


@router.get("/{profile_id}/skills")
async def get_skills(profile_id: UUID) -> list[dict]:
    return await list_resources(profile_id, "skills")


@router.post("/{profile_id}/skills")
async def create_skill(profile_id: UUID, payload: SkillCreate) -> dict:
    return await create_resource(profile_id, "skills", payload)


@router.patch("/{profile_id}/skills/{item_id}")
async def update_skill(profile_id: UUID, item_id: UUID, payload: SkillUpdate) -> dict:
    return await update_resource(profile_id, "skills", item_id, payload)


@router.get("/{profile_id}/experiences")
async def get_experiences(profile_id: UUID) -> list[dict]:
    return await list_resources(profile_id, "experiences")


@router.post("/{profile_id}/experiences")
async def create_experience(profile_id: UUID, payload: WorkExperienceCreate) -> dict:
    return await create_resource(profile_id, "experiences", payload)


@router.patch("/{profile_id}/experiences/{item_id}")
async def update_experience(profile_id: UUID, item_id: UUID, payload: WorkExperienceUpdate) -> dict:
    return await update_resource(profile_id, "experiences", item_id, payload)


@router.get("/{profile_id}/projects")
async def get_projects(profile_id: UUID) -> list[dict]:
    return await list_resources(profile_id, "projects")


@router.post("/{profile_id}/projects")
async def create_project(profile_id: UUID, payload: PortfolioProjectCreate) -> dict:
    return await create_resource(profile_id, "projects", payload)


@router.patch("/{profile_id}/projects/{item_id}")
async def update_project(
    profile_id: UUID,
    item_id: UUID,
    payload: PortfolioProjectUpdate,
) -> dict:
    return await update_resource(profile_id, "projects", item_id, payload)


@router.get("/{profile_id}/education")
async def get_education(profile_id: UUID) -> list[dict]:
    return await list_resources(profile_id, "education")


@router.post("/{profile_id}/education")
async def create_education(profile_id: UUID, payload: EducationCreate) -> dict:
    return await create_resource(profile_id, "education", payload)


@router.patch("/{profile_id}/education/{item_id}")
async def update_education(profile_id: UUID, item_id: UUID, payload: EducationUpdate) -> dict:
    return await update_resource(profile_id, "education", item_id, payload)


@router.get("/{profile_id}/certificates")
async def get_certificates(profile_id: UUID) -> list[dict]:
    return await list_resources(profile_id, "certificates")


@router.post("/{profile_id}/certificates")
async def create_certificate(profile_id: UUID, payload: CertificateCreate) -> dict:
    return await create_resource(profile_id, "certificates", payload)


@router.patch("/{profile_id}/certificates/{item_id}")
async def update_certificate(profile_id: UUID, item_id: UUID, payload: CertificateUpdate) -> dict:
    return await update_resource(profile_id, "certificates", item_id, payload)


@router.get("/{profile_id}/references")
async def get_references(profile_id: UUID) -> list[dict]:
    return await list_resources(profile_id, "references")


@router.post("/{profile_id}/references")
async def create_reference(profile_id: UUID, payload: ReferenceCreate) -> dict:
    return await create_resource(profile_id, "references", payload)


@router.patch("/{profile_id}/references/{item_id}")
async def update_reference(profile_id: UUID, item_id: UUID, payload: ReferenceUpdate) -> dict:
    return await update_resource(profile_id, "references", item_id, payload)


@router.delete("/{profile_id}/{resource_type}/{item_id}", status_code=204)
async def delete_profile_resource(
    profile_id: UUID,
    resource_type: str,
    item_id: UUID,
) -> Response:
    await delete_resource(profile_id, resource_type, item_id)
    return Response(status_code=204)


@router.get("/{profile_id}/revisions/{entity_type}/{entity_id}")
async def get_revisions(profile_id: UUID, entity_type: str, entity_id: UUID) -> list[dict]:
    return await list_revisions(profile_id, entity_type, entity_id)
