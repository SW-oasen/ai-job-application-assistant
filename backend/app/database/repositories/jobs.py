from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import ApplicationError
from app.database.models import Company, Job, JobRequirement
from app.database.session import get_session_factory
from app.parsers.job_metadata import extract_job_metadata


@dataclass(frozen=True)
class PersistedImport:
    job_id: str | None
    duplicate: bool
    reimported: bool = False


@dataclass(frozen=True)
class StoredJobSource:
    job_id: UUID
    source_type: str
    source_url: str | None
    source_filename: str | None
    title: str | None
    raw_content: str | None
    normalized_content: str
    content_hash: str
    retrieval_method: str
    language: str | None
    import_warnings: list[str]


async def get_stored_job_source(job_id: UUID) -> StoredJobSource:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "The job database is not configured.",
            code="database_unavailable",
            status_code=503,
        )
    try:
        async with session_factory() as session:
            job = await session.get(Job, job_id)
            if job is None:
                raise ApplicationError(
                    "The requested job was not found.",
                    code="job_not_found",
                    status_code=404,
                )
            return StoredJobSource(
                job_id=job.id,
                source_type=job.source_type,
                source_url=job.source_url,
                source_filename=job.source_filename,
                title=job.title,
                raw_content=job.raw_content,
                normalized_content=job.normalized_content,
                content_hash=job.content_hash,
                retrieval_method=job.retrieval_method,
                language=job.language,
                import_warnings=job.import_warnings or [],
            )
    except SQLAlchemyError as exception:
        raise ApplicationError(
            "The job source could not be loaded.",
            code="database_unavailable",
            status_code=503,
        ) from exception


async def persist_imported_job(
    *,
    source_type: str,
    source_url: str | None,
    source_filename: str | None,
    title: str | None,
    raw_content: str | None,
    normalized_content: str,
    content_hash: str,
    retrieval_method: str,
    warnings: list[str],
    extracted_json: dict[str, Any] | None = None,
    replace_existing: bool = False,
    replace_job_id: UUID | None = None,
    metadata_override: dict[str, str | None] | None = None,
) -> PersistedImport:
    session_factory = get_session_factory()
    if session_factory is None:
        return PersistedImport(job_id=None, duplicate=False)

    try:
        async with session_factory() as session:
            metadata = extract_job_metadata(
                normalized_content,
                source_filename=source_filename,
                source_url=source_url,
            )
            if metadata_override:
                metadata.update(
                    {
                        key: value
                        for key, value in metadata_override.items()
                        if key in metadata and value
                    }
                )
            company = None
            company_name = (metadata.get("company") or "").strip()
            if company_name:
                company = await session.scalar(
                    select(Company).where(
                        func.lower(Company.name) == company_name.lower()
                    )
                )
                if company is None:
                    company = Company(name=company_name)
                    session.add(company)
                    await session.flush()
            duplicate_conditions = [Job.content_hash == content_hash]
            if source_url:
                duplicate_conditions.append(Job.source_url == source_url)
            existing = (
                await session.get(Job, replace_job_id)
                if replace_job_id is not None
                else await session.scalar(
                    select(Job).where(or_(*duplicate_conditions)).limit(1)
                )
            )
            if existing:
                if (
                    replace_existing
                    or (
                        source_type == "pdf"
                        and retrieval_method == "mineru"
                        and existing.retrieval_method != "mineru"
                    )
                ):
                    await session.execute(
                        delete(JobRequirement).where(
                            JobRequirement.job_id == existing.id
                        )
                    )
                    existing.title = title or metadata["title"]
                    existing.company_id = company.id if company else None
                    existing.source_type = source_type
                    existing.source_url = source_url
                    existing.source_filename = source_filename
                    existing.source_portal = metadata["source_portal"]
                    existing.raw_content = raw_content
                    existing.normalized_content = normalized_content
                    existing.extracted_json = extracted_json
                    existing.content_hash = content_hash
                    existing.retrieval_method = retrieval_method
                    existing.import_warnings = warnings
                    existing.location = metadata["location"]
                    existing.work_model = metadata["work_model"]
                    existing.employment_type = metadata["employment_type"]
                    existing.contract_term = metadata["contract_term"]
                    existing.language = metadata["language"]
                    existing.status = "analyzing"
                    existing.imported_at = func.now()
                    await session.commit()
                    return PersistedImport(
                        job_id=str(existing.id),
                        duplicate=False,
                        reimported=replace_existing,
                    )
                return PersistedImport(job_id=str(existing.id), duplicate=True)

            statement = (
                insert(Job)
                .values(
                    source_type=source_type,
                    company_id=company.id if company else None,
                    source_url=source_url,
                    source_filename=source_filename,
                    source_portal=metadata["source_portal"],
                    title=title or metadata["title"],
                    raw_content=raw_content,
                    normalized_content=normalized_content,
                    extracted_json=extracted_json,
                    content_hash=content_hash,
                    retrieval_method=retrieval_method,
                    import_warnings=warnings,
                    status="analyzing",
                    location=metadata["location"],
                    work_model=metadata["work_model"],
                    employment_type=metadata["employment_type"],
                    contract_term=metadata["contract_term"],
                    language=metadata["language"],
                )
                .returning(Job.id)
            )
            job_id = await session.scalar(statement)
            await session.commit()
            return PersistedImport(job_id=str(job_id), duplicate=False)
    except SQLAlchemyError as exception:
        raise ApplicationError(
            "The imported job could not be persisted.",
            code="database_unavailable",
            status_code=503,
        ) from exception
