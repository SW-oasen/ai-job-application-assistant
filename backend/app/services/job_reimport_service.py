from uuid import UUID

from app.core.errors import ApplicationError
from app.database.repositories.jobs import (
    get_stored_job_source,
    persist_imported_job,
)
from app.parsers.html_to_markdown import html_to_document
from app.parsers.job_metadata import extract_job_metadata
from app.parsers.job_portals import normalize_job_document
from app.parsers.job_seniority import (
    ensure_seniority_requirement,
    extract_job_seniority,
)
from app.schemas.imports import JobReimportResponse, UrlImportRequest
from app.services.hybrid_job_extraction import extract_job_structure_hybrid
from app.services.job_extraction_review_integration import (
    review_job_extraction_if_configured,
    store_job_extraction_review_history,
)
from app.services.job_extraction_service import enrich_job_extraction
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
    if not source.normalized_content.strip() and not source.raw_content:
        raise ApplicationError(
            "No stored job content is available for reimport.",
            code="job_source_unavailable",
            status_code=409,
        )

    # Rebuild HTML captures so newly added portal profiles also improve jobs
    # that were imported before the profile existed.
    normalized_content = source.normalized_content
    if source.source_type == "html" and source.raw_content:
        document = html_to_document(source.raw_content)
        normalized_content = normalize_job_document(
            document.markdown, title=document.title, source_url=source.source_url, raw_html=source.raw_content
        ).markdown

    structure = await extract_job_structure_hybrid(normalized_content)
    extraction = await enrich_job_extraction(
        content=normalized_content,
        metadata=extract_job_metadata(
            normalized_content, source_filename=source.source_filename, source_url=source.source_url
        ),
        activities=structure.activities,
        requirements=structure.requirements,
        source_filename=source.source_filename,
        source_url=source.source_url,
    )
    seniority = extract_job_seniority(normalized_content)
    reviewed = await review_job_extraction_if_configured(
        content=normalized_content,
        metadata=extraction.metadata,
        activities=extraction.activities,
        requirements=extraction.requirements,
    )
    requirements = ensure_seniority_requirement(reviewed.requirements, seniority)
    warnings = [
        warning
        for warning in source.import_warnings
        if not warning.startswith("semantic_metadata_")
        and not warning.startswith("job_extraction_llm_")
    ]
    warnings.extend(warning for warning in extraction.warnings if warning not in warnings)
    persisted = await persist_imported_job(
        source_type=source.source_type,
        source_url=source.source_url,
        source_filename=source.source_filename,
        title=None,
        raw_content=source.raw_content,
        normalized_content=normalized_content,
        content_hash=source.content_hash,
        retrieval_method=source.retrieval_method,
        warnings=warnings,
        metadata_override=reviewed.metadata,
        extracted_json={
            "semantic_metadata": extraction.metadata_details,
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
            original_metadata=extraction.metadata,
            original_activities=structure.activities,
            original_requirements=structure.requirements,
            reviewed=reviewed,
        )
    return JobReimportResponse(
        job_id=job_id,
        source_type=source.source_type,
        retrieval_method=source.retrieval_method,
        language=extraction.metadata.get("language"),
        warnings=warnings,
    )
