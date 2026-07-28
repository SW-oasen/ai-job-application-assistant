from sqlalchemy import func, select

from app.core.errors import ApplicationError
from app.database.models import Application, GeneratedDocument
from app.database.session import get_session_factory
from app.schemas.documents import DocumentContextRequest, GeneratedDocumentCreate
from app.services.matching_service import get_matching_context, get_stored_matching


def _session_factory():
    factory = get_session_factory()
    if factory is None:
        raise ApplicationError(
            "Document generation requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    return factory


async def prepare_document_context(payload: DocumentContextRequest) -> dict:
    context = await get_matching_context(payload.job_id, payload.profile_id)
    matching = await get_stored_matching(payload.job_id, payload.profile_id)
    if not matching["matches"]:
        raise ApplicationError(
            "No stored matching exists for this job and profile.",
            code="matching_required",
            status_code=409,
        )

    async with _session_factory()() as session:
        application = await session.scalar(
            select(Application).where(
                Application.job_id == payload.job_id,
                Application.profile_id == payload.profile_id,
            )
        )
        if application is None:
            application = Application(
                job_id=payload.job_id,
                profile_id=payload.profile_id,
                status="draft",
            )
            session.add(application)
            await session.commit()
            await session.refresh(application)

    return {
        "application_id": str(application.id),
        "language": payload.language,
        "job": matching["job"],
        "profile": {
            "id": context.profile_id,
            "display_name": matching["profile"]["display_name"],
        },
        # These are canonical, editable profile resources. Contact data and
        # references are intentionally excluded from the LLM context.
        "profile_evidence": [
            item.model_dump() for item in context.evidence
        ],
        "matching": matching["matches"],
        "generation_rules": [
            "Use only facts contained in profile_evidence and matching evidence.",
            "Never present project, training, or education evidence as professional experience.",
            "Do not invent missing facts; mark unsupported requirements as gaps.",
            f"Write the output in language '{payload.language}'.",
        ],
    }


async def store_generated_document(
    application_id,
    payload: GeneratedDocumentCreate,
) -> dict:
    async with _session_factory()() as session:
        application = await session.get(Application, application_id)
        if application is None:
            raise ApplicationError(
                "Application not found.",
                code="application_not_found",
                status_code=404,
            )
        latest_version = await session.scalar(
            select(func.max(GeneratedDocument.version)).where(
                GeneratedDocument.application_id == application_id,
                GeneratedDocument.document_type == payload.document_type,
                GeneratedDocument.language == payload.language,
            )
        )
        document = GeneratedDocument(
            application_id=application_id,
            document_type=payload.document_type,
            language=payload.language,
            version=(latest_version or 0) + 1,
            content=payload.content,
            prompt_version=payload.prompt_version,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return {
            "document_id": str(document.id),
            "application_id": str(application_id),
            "document_type": document.document_type,
            "language": document.language,
            "version": document.version,
            "content": document.content,
            "prompt_version": document.prompt_version,
            "created_at": document.created_at,
        }


async def list_generated_documents(application_id) -> list[dict]:
    async with _session_factory()() as session:
        if await session.get(Application, application_id) is None:
            raise ApplicationError(
                "Application not found.",
                code="application_not_found",
                status_code=404,
            )
        documents = (
            await session.scalars(
                select(GeneratedDocument)
                .where(GeneratedDocument.application_id == application_id)
                .order_by(
                    GeneratedDocument.document_type,
                    GeneratedDocument.language,
                    GeneratedDocument.version.desc(),
                )
            )
        ).all()
        return [
            {
                "document_id": str(item.id),
                "application_id": str(application_id),
                "document_type": item.document_type,
                "language": item.language,
                "version": item.version,
                "content": item.content,
                "prompt_version": item.prompt_version,
                "created_at": item.created_at,
            }
            for item in documents
        ]
