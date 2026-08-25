from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile
from fastapi.responses import RedirectResponse

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
    SkillEvidenceCreate,
    SkillEvidenceUpdate,
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
    create_skill_evidence,
    delete_resource,
    delete_skill_evidence,
    get_profile,
    list_profiles,
    list_resources,
    list_revisions,
    list_skill_evidence,
    update_profile,
    update_resource,
    update_skill_evidence,
)

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


@router.get("/{profile_id}")
async def get_profile_entry(profile_id: UUID) -> dict:
    return await get_profile(profile_id)


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


@router.get("/{profile_id}/skill-evidence")
async def get_skill_evidence(profile_id: UUID) -> list[dict]:
    return await list_skill_evidence(profile_id)


@router.post("/{profile_id}/skill-evidence")
async def create_profile_skill_evidence(profile_id: UUID, payload: SkillEvidenceCreate) -> dict:
    return await create_skill_evidence(profile_id, payload)


@router.patch("/{profile_id}/skill-evidence/{item_id}")
async def update_profile_skill_evidence(
    profile_id: UUID, item_id: UUID, payload: SkillEvidenceUpdate
) -> dict:
    return await update_skill_evidence(profile_id, item_id, payload)


@router.delete("/{profile_id}/skill-evidence/{item_id}", status_code=204)
async def delete_profile_skill_evidence(profile_id: UUID, item_id: UUID) -> Response:
    await delete_skill_evidence(profile_id, item_id)
    return Response(status_code=204)


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
