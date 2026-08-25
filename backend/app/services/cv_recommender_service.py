from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.errors import ApplicationError
from app.database.models import Application, CvRecommendation, GeneratedDocument, Job, JobActivity, JobRequirement, MasterProfile, Profile
from app.database.session import get_session_factory
from app.services.dify_cv_recommender_service import run_cv_recommender_workflow
from app.services.master_profile_cv import parse_master_profile, render_cv_markdown, validate_recommendation


def _factory():
    factory = get_session_factory()
    if factory is None:
        raise ApplicationError("CV-Recommender benötigt eine konfigurierte Datenbank.", code="database_not_configured", status_code=503)
    return factory


async def _application(session, job_id: UUID, profile_id: UUID) -> Application:
    row = await session.scalar(select(Application).where(Application.job_id == job_id, Application.profile_id == profile_id))
    if row is None:
        row = Application(job_id=job_id, profile_id=profile_id, status="draft")
        session.add(row)
        await session.flush()
    return row


def _serialize_recommendation(row: CvRecommendation) -> dict:
    return {"id": str(row.id), "application_id": str(row.application_id), "language": row.language, "master_profile_id": str(row.master_profile_id), "master_profile_version": row.master_profile_version, "recommendation": row.recommendation, "validation_warnings": row.validation_warnings or [], "is_current": row.is_current, "workflow_run_id": row.workflow_run_id, "created_at": row.created_at, "updated_at": row.updated_at}


async def create_cv_recommendation(*, job_id: UUID, profile_id: UUID, language: str | None) -> dict:
    async with _factory()() as session:
        job = await session.get(Job, job_id)
        if job is None or await session.get(Profile, profile_id) is None:
            raise ApplicationError("Stelle oder Profil wurde nicht gefunden.", code="cv_recommendation_source_not_found", status_code=404)
        language = language or ("en" if job.language == "en" else "de")
        master = await session.scalar(select(MasterProfile).where(MasterProfile.profile_id == profile_id, MasterProfile.language == language, MasterProfile.is_current.is_(True)))
        if master is None:
            raise ApplicationError("Für die Sprache der Stelle ist kein Master-Profil vorhanden.", code="master_profile_not_found", status_code=409)
        application = await _application(session, job_id, profile_id)
        inventory = parse_master_profile(master.content)
        if not inventory["profile_name"]:
            raise ApplicationError("Das Master-Profil enthält keinen Profilnamen.", code="master_profile_invalid_structure", status_code=422)
        requirements = (await session.scalars(select(JobRequirement).where(JobRequirement.job_id == job.id))).all()
        activities = (await session.scalars(select(JobActivity).where(JobActivity.job_id == job.id).order_by(JobActivity.position))).all()
        job_context = {"title": job.title, "language": job.language, "requirements": [{"text": item.requirement_text, "priority": item.priority, "keywords": item.keywords} for item in requirements], "activities": [item.activity_text for item in activities]}
        recommendation, workflow_run_id = await run_cv_recommender_workflow(job=job_context, master_profile=master.content, inventory=inventory, language=language, user=f"cv-{profile_id}")
        recommendation, warnings = validate_recommendation(recommendation, inventory)
        await session.execute(update(CvRecommendation).where(CvRecommendation.application_id == application.id, CvRecommendation.language == language, CvRecommendation.is_current.is_(True)).values(is_current=False))
        row = CvRecommendation(application_id=application.id, master_profile_id=master.id, master_profile_version=master.version, language=language, recommendation=recommendation, validation_warnings=warnings, workflow_run_id=workflow_run_id)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        result = _serialize_recommendation(row)
        result["inventory"] = inventory
        return result


async def get_cv_recommendation(application_id: UUID, language: str | None = None) -> dict | None:
    async with _factory()() as session:
        statement = select(CvRecommendation).where(CvRecommendation.application_id == application_id, CvRecommendation.is_current.is_(True))
        if language:
            statement = statement.where(CvRecommendation.language == language)
        row = await session.scalar(statement.order_by(CvRecommendation.created_at.desc()))
        if row is None:
            return None
        master = await session.get(MasterProfile, row.master_profile_id)
        result = _serialize_recommendation(row)
        result["inventory"] = parse_master_profile(master.content)
        return result


async def update_cv_recommendation(recommendation_id: UUID, payload: dict) -> dict:
    async with _factory()() as session:
        row = await session.get(CvRecommendation, recommendation_id)
        if row is None:
            raise ApplicationError("CV-Empfehlung wurde nicht gefunden.", code="cv_recommendation_not_found", status_code=404)
        master = await session.get(MasterProfile, row.master_profile_id)
        inventory = parse_master_profile(master.content)
        recommendation, warnings = validate_recommendation(payload, inventory)
        row.recommendation = recommendation
        row.validation_warnings = warnings
        row.updated_at = datetime.now().astimezone()
        await session.commit()
        await session.refresh(row)
        result = _serialize_recommendation(row)
        result["inventory"] = inventory
        return result


async def create_cv_markdown(recommendation_id: UUID) -> dict:
    async with _factory()() as session:
        recommendation = await session.get(CvRecommendation, recommendation_id)
        if recommendation is None:
            raise ApplicationError("CV-Empfehlung wurde nicht gefunden.", code="cv_recommendation_not_found", status_code=404)
        master = await session.get(MasterProfile, recommendation.master_profile_id)
        inventory = parse_master_profile(master.content)
        validated, warnings = validate_recommendation(recommendation.recommendation, inventory)
        if warnings:
            recommendation.validation_warnings = warnings
        content = render_cv_markdown(inventory, validated, recommendation.language)
        await session.execute(update(GeneratedDocument).where(GeneratedDocument.application_id == recommendation.application_id, GeneratedDocument.document_type == "cv", GeneratedDocument.language == recommendation.language, GeneratedDocument.is_current.is_(True)).values(is_current=False))
        latest = await session.scalar(select(func.max(GeneratedDocument.version)).where(GeneratedDocument.application_id == recommendation.application_id, GeneratedDocument.document_type == "cv", GeneratedDocument.language == recommendation.language))
        document = GeneratedDocument(application_id=recommendation.application_id, document_type="cv", language=recommendation.language, version=(latest or 0) + 1, content=content, prompt_version="cv-recommender-v1", source_master_profile_id=master.id, source_master_profile_version=master.version, source_recommendation_id=recommendation.id, generation_metadata={"workflow_run_id": recommendation.workflow_run_id}, is_current=True)
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return _serialize_document(document)


def _serialize_document(row: GeneratedDocument) -> dict:
    return {"document_id": str(row.id), "application_id": str(row.application_id), "document_type": row.document_type, "language": row.language, "version": row.version, "content": row.content, "is_current": row.is_current, "created_at": row.created_at, "source_master_profile_id": str(row.source_master_profile_id) if row.source_master_profile_id else None, "source_master_profile_version": row.source_master_profile_version, "source_recommendation_id": str(row.source_recommendation_id) if row.source_recommendation_id else None, "generation_metadata": row.generation_metadata}


async def save_cv_markdown_version(application_id: UUID, language: str, content: str) -> dict:
    async with _factory()() as session:
        if await session.get(Application, application_id) is None:
            raise ApplicationError("Bewerbung wurde nicht gefunden.", code="application_not_found", status_code=404)
        latest = await session.scalar(select(func.max(GeneratedDocument.version)).where(GeneratedDocument.application_id == application_id, GeneratedDocument.document_type == "cv", GeneratedDocument.language == language))
        await session.execute(update(GeneratedDocument).where(GeneratedDocument.application_id == application_id, GeneratedDocument.document_type == "cv", GeneratedDocument.language == language, GeneratedDocument.is_current.is_(True)).values(is_current=False))
        row = GeneratedDocument(application_id=application_id, document_type="cv", language=language, version=(latest or 0) + 1, content=content, prompt_version="manual-cv-edit-v1", generation_metadata={"source": "manual_edit"}, is_current=True)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _serialize_document(row)


async def list_cv_documents(application_id: UUID, language: str | None = None) -> list[dict]:
    async with _factory()() as session:
        statement = select(GeneratedDocument).where(GeneratedDocument.application_id == application_id, GeneratedDocument.document_type == "cv")
        if language:
            statement = statement.where(GeneratedDocument.language == language)
        rows = (await session.scalars(statement.order_by(GeneratedDocument.version.desc()))).all()
        return [_serialize_document(row) for row in rows]
