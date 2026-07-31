from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ResourceType = Literal[
    "profile",
    "skills",
    "experiences",
    "projects",
    "education",
    "certificates",
    "references",
]


class CvSuggestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: ResourceType
    proposed_data: dict[str, Any]
    source_excerpt: str | None = Field(default=None, max_length=20_000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    matched_entity_id: str | None = None


class CvImportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_filename: str = Field(min_length=1, max_length=500)
    content_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_language: Literal["de", "en"] | None = None
    source_metadata: dict[str, Any] | None = None
    suggestions: list[CvSuggestionInput] = Field(min_length=1, max_length=500)


class StructuredCvImportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_filename: str = Field(min_length=1, max_length=500)
    content_hash: str | None = Field(default=None, min_length=64, max_length=64)
    source_language: Literal["de", "en"] = "de"
    structured_cv: dict[str, Any]


class StructuredPortfolioImportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1, max_length=500)
    source_language: Literal["de", "en"] = "de"
    projects: list[dict[str, Any]] = Field(min_length=1, max_length=200)


class PortfolioSourceImportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1, max_length=500)
    source_content: str = Field(min_length=1, max_length=2_000_000)
    export_name: Literal["PROJECTS"] = "PROJECTS"


class CvSuggestionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposed_data: dict[str, Any] | None = None
    review_note: str | None = Field(default=None, max_length=2000)
    resolution: Literal["keep_existing", "merge", "create_new"] | None = None
