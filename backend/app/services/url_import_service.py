import hashlib
from uuid import UUID

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.database.repositories.jobs import persist_imported_job
from app.importers.http_importer import HttpImporter
from app.importers.playwright_importer import PlaywrightImporter
from app.parsers.html_to_markdown import html_to_document
from app.parsers.job_seniority import (
    ensure_seniority_requirement,
    extract_job_seniority,
)
from app.parsers.job_role import extract_job_role
from app.parsers.job_structure import extract_job_structure
from app.parsers.text_quality import assess_text_quality
from app.schemas.imports import UrlImportRequest, UrlImportResponse
from app.services.job_extraction_review_integration import (
    review_job_extraction_if_configured,
    store_job_extraction_review_history,
)
from app.services.semantic_metadata_service import enrich_job_metadata

NON_FALLBACK_ERROR_CODES = {
    "invalid_url",
    "invalid_url_scheme",
    "url_credentials_forbidden",
    "url_resolution_failed",
    "private_network_forbidden",
    "source_too_large",
    "unsupported_content_type",
}


async def import_url(
    payload: UrlImportRequest,
    *,
    replace_job_id: UUID | None = None,
) -> UrlImportResponse:
    settings = get_settings()
    if payload.force_browser and not settings.playwright_enabled:
        raise ApplicationError(
            "Browser-based imports are disabled.",
            code="browser_import_disabled",
            status_code=503,
        )

    importer = HttpImporter(
        timeout_seconds=settings.url_import_timeout_seconds,
        max_bytes=settings.url_import_max_bytes,
        max_redirects=settings.url_import_max_redirects,
        user_agent=settings.url_import_user_agent,
    )
    if payload.force_browser:
        response = await _import_with_browser(payload.url, fallback_used=False)
        return await _persist_response(response, replace_job_id=replace_job_id)

    try:
        imported = await importer.fetch(payload.url)
    except ApplicationError as exception:
        if not settings.playwright_enabled or exception.code in NON_FALLBACK_ERROR_CODES:
            raise
        response = await _import_with_browser(payload.url, fallback_used=True)
        return await _persist_response(response, replace_job_id=replace_job_id)

    response = _build_response(
        source_url=imported.final_url,
        raw_html=imported.content,
        retrieval_method="http",
    )
    if response.quality_sufficient or not settings.playwright_enabled:
        return await _persist_response(response, replace_job_id=replace_job_id)
    response = await _import_with_browser(payload.url, fallback_used=True)
    return await _persist_response(response, replace_job_id=replace_job_id)


async def _import_with_browser(url: str, *, fallback_used: bool) -> UrlImportResponse:
    settings = get_settings()
    importer = PlaywrightImporter(
        timeout_seconds=settings.playwright_timeout_seconds,
        max_bytes=settings.url_import_max_bytes,
        user_agent=settings.url_import_user_agent,
    )
    imported = await importer.fetch(url)
    warnings = ["browser_fallback_used"] if fallback_used else []
    return _build_response(
        source_url=imported.final_url,
        raw_html=imported.content,
        retrieval_method="browser",
        extra_warnings=warnings,
    )


def _build_response(
    *,
    source_url: str,
    raw_html: str,
    retrieval_method: str,
    extra_warnings: list[str] | None = None,
) -> UrlImportResponse:
    settings = get_settings()
    document = html_to_document(raw_html)
    quality = assess_text_quality(
        document.plain_text,
        title=document.title,
        minimum_length=settings.url_import_min_text_length,
    )
    quality_warnings = list(quality.warnings)
    if document.related_jobs_removed and not quality.sufficient:
        quality_warnings.append("job_description_not_found")
    warnings = [*(extra_warnings or []), *quality_warnings]
    return UrlImportResponse(
        success=True,
        source_url=source_url,
        retrieval_method=retrieval_method,
        title=document.title,
        raw_html=raw_html,
        markdown=document.markdown,
        content_hash=hashlib.sha256(document.markdown.encode("utf-8")).hexdigest(),
        text_length=quality.text_length,
        quality_sufficient=quality.sufficient,
        browser_fallback_recommended=False,
        warnings=warnings,
    )


async def _persist_response(
    response: UrlImportResponse,
    *,
    replace_job_id: UUID | None = None,
) -> UrlImportResponse:
    if not response.quality_sufficient:
        response.job_id = None
        response.duplicate = False
        return response

    semantic = await enrich_job_metadata(
        response.markdown,
        source_url=response.source_url,
    )
    structure = extract_job_structure(response.markdown)
    seniority = extract_job_seniority(response.markdown)
    job_role = extract_job_role(semantic.metadata.get("title") or response.title, response.markdown)
    reviewed = await review_job_extraction_if_configured(
        content=response.markdown,
        metadata=semantic.metadata,
        activities=structure.activities,
        requirements=structure.requirements,
    )
    requirements = ensure_seniority_requirement(reviewed.requirements, seniority)
    response.warnings.extend(
        warning for warning in semantic.warnings if warning not in response.warnings
    )
    persisted = await persist_imported_job(
        source_type="url",
        source_url=response.source_url,
        source_filename=None,
        title=reviewed.metadata.get("title") or response.title,
        raw_content=response.raw_html,
        normalized_content=response.markdown,
        content_hash=response.content_hash,
        retrieval_method=response.retrieval_method,
        warnings=response.warnings,
        metadata_override=reviewed.metadata,
        extracted_json={
            "semantic_metadata": semantic.details,
            "activities": reviewed.activities,
            "requirements": requirements,
            "seniority": seniority,
            "role": job_role,
        },
        activities=reviewed.activities,
        requirements=requirements,
        replace_existing=replace_job_id is not None,
        replace_job_id=replace_job_id,
    )
    response.job_id = persisted.job_id
    response.duplicate = persisted.duplicate
    if persisted.job_id and reviewed.review_results:
        await store_job_extraction_review_history(
            job_id=persisted.job_id,
            original_metadata=semantic.metadata,
            original_activities=structure.activities,
            original_requirements=structure.requirements,
            reviewed=reviewed,
        )
    return response
