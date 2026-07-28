from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    profile_id: UUID
    language: Literal["de", "en"]


class GeneratedDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Literal[
        "profile_summary",
        "cv_suggestions",
        "project_selection",
        "cover_letter",
        "application_questions",
        "interview_preparation",
    ]
    language: Literal["de", "en"]
    content: str = Field(min_length=1, max_length=500_000)
    prompt_version: str | None = Field(default=None, max_length=100)
