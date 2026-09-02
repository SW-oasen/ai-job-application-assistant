from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.demo_mode import validate_demo_database
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    validate_demo_database(settings)
    configure_logging(settings.log_level)

    application = FastAPI(
        title="Application Assistant Backend",
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
    )
    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
