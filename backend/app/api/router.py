from fastapi import APIRouter

from app.api.routes.application_files import router as application_files_router
from app.api.routes.applications import router as applications_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router
from app.api.routes.home import router as home_router
from app.api.routes.imports import router as imports_router
from app.api.routes.matching import router as matching_router
from app.api.routes.profile import router as profile_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(home_router)
api_router.include_router(documents_router)
api_router.include_router(application_files_router)
api_router.include_router(applications_router)
api_router.include_router(imports_router)
api_router.include_router(matching_router)
api_router.include_router(profile_router)
