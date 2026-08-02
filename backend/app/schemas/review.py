from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

ReviewType = Literal[
    "job_extraction",
    "job_matching",
    "profile_extraction",
    "skill_mapping",
    "project_selection",
    "cv_draft",
    "cover_letter_draft",
]
ReviewStatus = Literal[
    "pending",
    "accepted",
    "corrected",
    "retry_requested",
    "manual_review_required",
    "failed",
]
ReviewDecision = Literal["accept", "correct", "retry", "manual_review"]
ReviewIssueType = Literal[
    "missing_value",
    "unsupported_value",
    "wrong_value",
    "wrong_category",
    "inconsistent_value",
    "schema_error",
    "missing_evidence",
    "weak_evidence",
    "score_inconsistency",
    "hallucination",
    "other",
]
ReviewSeverity = Literal["low", "medium", "high", "critical"]
Confidence = Annotated[float, Field(ge=0, le=1)]


class ReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1, max_length=500)
    issue_type: ReviewIssueType
    severity: ReviewSeverity
    message: str = Field(min_length=1, max_length=4_000)
    evidence: str | None = Field(default=None, max_length=20_000)
    suggested_value: JsonValue | None = None


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_type: ReviewType
    status: ReviewStatus
    decision: ReviewDecision | None = None
    overall_confidence: Confidence | None = None
    issues: list[ReviewIssue] = Field(default_factory=list, max_length=500)
    field_confidence: dict[str, Confidence] = Field(default_factory=dict)
    corrected_result: dict[str, JsonValue] = Field(default_factory=dict)
    retry_instructions: list[str] = Field(default_factory=list, max_length=100)
    reviewer_model: str | None = Field(default=None, max_length=500)
    workflow_version: str | None = Field(default=None, max_length=100)
    prompt_version: str | None = Field(default=None, max_length=100)
    duration_ms: int | None = Field(default=None, ge=0)
    attempt: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    technical_error: str | None = Field(default=None, max_length=10_000)