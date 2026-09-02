from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class ReviewWorkflowSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    api_key: SecretStr | None = None
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    max_retries: int = Field(default=1, ge=0, le=1)
    reviewer_model: str | None = Field(default=None, max_length=500)
    workflow_version: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=100)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "application-assistant-backend"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8080
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    dify_base_url: AnyHttpUrl = "http://api:5001"
    dify_cv_workflow_api_key: SecretStr | None = None
    dify_cv_workflow_timeout_seconds: int = 300
    dify_cv_recommender_workflow_api_key: SecretStr | None = None
    dify_cv_recommender_workflow_timeout_seconds: int = 300
    dify_matching_workflow_api_key: SecretStr | None = None
    dify_matching_workflow_timeout_seconds: int = 300
    dify_metadata_workflow_api_key: SecretStr | None = None
    dify_metadata_workflow_timeout_seconds: int = 120
    semantic_metadata_max_characters: int = 15_000
    dify_job_extraction_workflow_api_key: SecretStr | None = None
    dify_job_extraction_workflow_timeout_seconds: int = 180
    job_extraction_max_characters: int = 30_000
    review_workflows: dict[str, ReviewWorkflowSettings] = Field(default_factory=dict)
    mineru_base_url: AnyHttpUrl = "http://mineru-api:8000"
    mineru_timeout_seconds: int = 300
    mineru_backend: Literal["pipeline", "hybrid-engine"] = "pipeline"

    database_url: str | None = None
    demo_mode: bool = False
    demo_database_name: str = "application_assistant_demo"
    embedding_provider: str = "disabled"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = Field(default=1536, ge=1, le=8192)
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: SecretStr | None = None
    chroma_host: str = "chromadb"
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_collection: str = "profile-evidence"
    redis_url: RedisDsn | None = None

    url_import_timeout_seconds: float = 30
    url_import_max_bytes: int = 10_000_000
    url_import_min_text_length: int = 500
    url_import_max_redirects: int = 5
    url_import_user_agent: str = "ApplicationAssistant/0.1 (+local)"
    playwright_enabled: bool = True
    playwright_timeout_seconds: float = 45
    pdf_import_max_bytes: int = 20_000_000
    pdf_import_min_text_length: int = 500
    pdf_raster_image_format: Literal["png", "jpeg"] = "png"
    pdf_raster_colorspace: Literal["grayscale", "rgb"] = "grayscale"
    pdf_raster_dpi: int = 200
    pdf_raster_jpeg_quality: int = 85
    pdf_raster_max_pages: int = 50
    html_import_max_bytes: int = 30_000_000
    application_documents_path: Path = Path("/app/data/application-documents")
    application_document_max_bytes: int = 20_000_000

    @property
    def log_level(self) -> str:
        return self.app_log_level

    @property
    def docs_enabled(self) -> bool:
        return self.app_env != "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
