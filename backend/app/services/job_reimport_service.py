from uuid import UUID

from app.core.errors import ApplicationError
from app.database.repositories.jobs import (
    get_stored_job_source,
    persist_imported_job,
)
from app.parsers.job_seniority import (
    ensure_seniority_requirement,
    extract_job_seniority,
)
from app.parsers.job_structure import extract_job_structure
from app.schemas.imports import JobReimportResponse, UrlImportRequest
from app.services.job_extraction_review_integration import (
    review_job_extraction_if_configured,
    store_job_extraction_review_history,
)
from app.services.semantic_metadata_service import enrich_job_metadata
from app.services.url_import_service import import_url


async def reimport_job(job_id: UUID) -> JobReimportResponse:
    source = await get_stored_job_source(job_id)
    if source.source_type == "url":
        if not source.source_url:
            raise ApplicationError(
                "For this URL job, no source URL is stored.",
                code="job_source_unavailable",
                status_code=409,
            )
        response = await import_url(
            UrlImportRequest(url=source.source_url),
            replace_job_id=job_id,
        )
        if not response.quality_sufficient or response.job_id is None:
            raise ApplicationError(
                "The source no longer contains enough job content for reimport.",
                code="job_reimport_content_insufficient",
                status_code=422,
            )
        updated = await get_stored_job_source(job_id)
        return JobReimportResponse(
            job_id=job_id,
            source_type="url",
            retrieval_method=response.retrieval_method,
            language=updated.language,
            warnings=response.warnings,
        )

    if source.source_type not in {"pdf", "html"}:
        raise ApplicationError(
            f"Jobs from source type '{source.source_type}' cannot be reimported.",
            code="unsupported_reimport_source",
            status_code=409,
        )
    if not source.normalized_content.strip():
        raise ApplicationError(
            "No stored job content is available for reimport.",
            code="job_source_unavailable",
            status_code=409,
        )

    semantic = await enrich_job_metadata(
        source.normalized_content,
        source_filename=source.source_filename,
        source_url=source.source_url,
    )
    structure = extract_job_structure(source.normalized_content)
    seniority = extract_job_seniority(source.normalized_content)
    reviewed = await review_job_extraction_if_configured(
        content=source.normalized_content,
        metadata=semantic.metadata,
        activities=structure.activities,
        requirements=structure.requirements,
    )
    requirements = ensure_seniority_requirement(reviewed.requirements, seniority)
    warnings = [
        warning
        for warning in source.import_warnings
        if not warning.startswith("semantic_metadata_")
    ]
    warnings.extend(
        warning for warning in semantic.warnings if warning not in warnings
    )
    persisted = await persist_imported_job(
        source_type=source.source_type,
        source_url=source.source_url,
        source_filename=source.source_filename,
        title=None,
        raw_content=source.raw_content,
        normalized_content=source.normalized_content,
        content_hash=source.content_hash,
        retrieval_method=source.retrieval_method,
        warnings=warnings,
        metadata_override=reviewed.metadata,
        extracted_json={
            "semantic_metadata": semantic.details,
            "activities": reviewed.activities,
            "requirements": requirements,
            "seniority": seniority,
        },
        activities=reviewed.activities,
        requirements=requirements,
        replace_existing=True,
        replace_job_id=job_id,
    )
    if not persisted.reimported:
        raise ApplicationError(
            "The stored job could not be reimported.",
            code="job_reimport_failed",
            status_code=500,
        )
    if persisted.job_id and reviewed.review_results:
        await store_job_extraction_review_history(
            job_id=persisted.job_id,
            original_metadata=semantic.metadata,
            original_activities=structure.activities,
            original_requirements=structure.requirements,
            reviewed=reviewed,
        )
    return JobReimportResponse(
        job_id=job_id,
        source_type=source.source_type,
        retrieval_method=source.retrieval_method,
        language=semantic.metadata.get("language"),
        warnings=warnings,
    )
