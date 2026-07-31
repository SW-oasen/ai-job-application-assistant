from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ExperienceContext = Literal["professional", "project", "training", "education", "other"]
MatchLevel = Literal["strong_match", "partial_match", "transferable", "gap", "unknown"]


class JobMetadataUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=500)
    company: str | None = Field(default=None, max_length=300)
    location: str | None = Field(default=None, max_length=500)
    work_model: str | None = Field(default=None, max_length=50)
    employment_type: str | None = Field(default=None, max_length=100)
    contract_term: str | None = Field(default=None, max_length=200)
    source_portal: str | None = Field(default=None, max_length=300)
    language: Literal["de", "en"] | None = None
    published_at: date | None = None
    deadline: date | None = None


class JobArchiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=500)


class RequirementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: str = Field(min_length=3, max_length=4000)
    category: str = Field(default="other", min_length=1, max_length=100)
    priority: Literal["must", "should", "nice_to_have"] = "should"
    keywords: list[str] = Field(default_factory=list, max_length=50)


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1, max_length=500)
    source_type: Literal[
        "cv", "portfolio", "github", "certificate", "note", "manual"
    ] = "manual"
    source_content: str = Field(min_length=1, max_length=500_000)
    label: str = Field(min_length=1, max_length=500)
    evidence_text: str = Field(min_length=1, max_length=10_000)
    experience_context: ExperienceContext
    keywords: list[str] = Field(default_factory=list, max_length=100)


class MatchingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    profile_id: UUID | None = None
    requirements: list[RequirementInput] = Field(min_length=1, max_length=200)
    evidence: list[EvidenceInput] = Field(default_factory=list, max_length=1000)


class MatchingWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    profile_id: UUID


class MatchingContextResponse(BaseModel):
    job_id: str
    profile_id: str
    job_title: str | None
    job_language: str | None
    job_content: str
    evidence: list[EvidenceInput]


class MatchEvidence(BaseModel):
    evidence_id: str
    source_name: str
    label: str
    evidence_text: str
    experience_context: ExperienceContext


class RequirementMatchResponse(BaseModel):
    requirement_id: str
    requirement: str
    match_level: MatchLevel
    evidence: list[MatchEvidence]
    explanation: str
    recommended_action: str
    confidence: float


class MatchingResponse(BaseModel):
    job_id: str
    matches: list[RequirementMatchResponse]
    summary: dict[str, int]
