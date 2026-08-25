from uuid import UUID

from fastapi import APIRouter

from app.schemas.cv_recommender import CvMarkdownCreate, CvMarkdownEdit, CvRecommendationCreate, CvRecommendationUpdate
from app.services.cv_recommender_service import (
    create_cv_markdown,
    create_cv_recommendation,
    get_cv_recommendation,
    list_cv_documents,
    save_cv_markdown_version,
    update_cv_recommendation,
)

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/recommendations", status_code=201)
async def recommend_cv(payload: CvRecommendationCreate) -> dict:
    return await create_cv_recommendation(job_id=payload.job_id, profile_id=payload.profile_id, language=payload.language)


@router.get("/applications/{application_id}/recommendation")
async def current_recommendation(application_id: UUID, language: str | None = None) -> dict | None:
    return await get_cv_recommendation(application_id, language)


@router.put("/recommendations/{recommendation_id}")
async def save_recommendation(recommendation_id: UUID, payload: CvRecommendationUpdate) -> dict:
    return await update_cv_recommendation(recommendation_id, payload.model_dump())


@router.post("/documents", status_code=201)
async def generate_cv(payload: CvMarkdownCreate) -> dict:
    return await create_cv_markdown(payload.recommendation_id)


@router.get("/applications/{application_id}/documents")
async def cv_documents(application_id: UUID, language: str | None = None) -> list[dict]:
    return await list_cv_documents(application_id, language)


@router.post("/applications/{application_id}/documents", status_code=201)
async def save_cv(application_id: UUID, language: str, payload: CvMarkdownEdit) -> dict:
    return await save_cv_markdown_version(application_id, language, payload.content)
