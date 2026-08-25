from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Language = Literal["de", "en"]


class CvRecommendationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    profile_id: UUID
    language: Language | None = None


class CvRecommendationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_job_title: str = Field(min_length=1, max_length=500)
    recommended_profile_text: str = Field(min_length=40, max_length=5_000)
    selected_skill_categories: list[str] = Field(default_factory=list, max_length=30)
    selected_skills: list[str] = Field(default_factory=list, max_length=200)
    selected_experience_entries: list[str] = Field(default_factory=list, max_length=50)
    selected_experience_bullets: dict[str, list[str]] = Field(default_factory=dict)
    selected_projects: list[str] = Field(default_factory=list, max_length=30)
    selected_education: list[str] = Field(default_factory=list, max_length=30)
    selected_certificates: list[str] = Field(default_factory=list, max_length=30)
    selected_references: list[str] = Field(default_factory=list, max_length=30)
    include_references: bool = False


class CvMarkdownCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: UUID


class CvMarkdownEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=500_000)
