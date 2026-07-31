from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.domain.skill_taxonomy import SkillCategory, SkillLevel

Language = Literal["de", "en"]
ContentStatus = Literal["draft", "approved", "inactive"]
WorkModel = Literal["remote", "hybrid", "onsite"]
EmploymentType = Literal["permanent", "temporary", "freelance", "internship", "working_student"]

PROFILE_LIST_FIELDS = (
    "target_roles",
    "target_industries",
    "target_locations",
    "preferred_work_models",
    "preferred_employment_types",
    "deal_breakers",
)


def _normalize_profile_lists(model):
    for field_name in PROFILE_LIST_FIELDS:
        values = getattr(model, field_name, None)
        if values is None:
            continue
        cleaned = []
        seen = set()
        for value in values:
            value = value.strip()
            key = value.casefold()
            if not value or key in seen:
                continue
            if len(value) > 500:
                raise ValueError(f"{field_name} entries may not exceed 500 characters.")
            seen.add(key)
            cleaned.append(value)
        setattr(model, field_name, cleaned)
    return model


class LocalizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: Language
    title: str = Field(min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=20_000)
    bullets: list[str] = Field(default_factory=list, max_length=100)
    status: ContentStatus = "draft"


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=300)
    full_name: str | None = Field(default=None, max_length=500)
    nationality: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    github_url: str | None = Field(default=None, max_length=2048)
    portfolio_url: str | None = Field(default=None, max_length=2048)
    career_goal: str | None = Field(default=None, max_length=10_000)
    target_roles: list[str] = Field(default_factory=list, max_length=50)
    target_industries: list[str] = Field(default_factory=list, max_length=50)
    target_locations: list[str] = Field(default_factory=list, max_length=50)
    preferred_work_models: list[WorkModel] = Field(default_factory=list, max_length=3)
    preferred_employment_types: list[EmploymentType] = Field(default_factory=list, max_length=5)
    deal_breakers: list[str] = Field(default_factory=list, max_length=50)
    default_language: Language = "de"
    change_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def normalize_goal_lists(self):
        return _normalize_profile_lists(self)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=300)
    full_name: str | None = Field(default=None, max_length=500)
    nationality: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=2048)
    github_url: str | None = Field(default=None, max_length=2048)
    portfolio_url: str | None = Field(default=None, max_length=2048)
    career_goal: str | None = Field(default=None, max_length=10_000)
    target_roles: list[str] | None = Field(default=None, max_length=50)
    target_industries: list[str] | None = Field(default=None, max_length=50)
    target_locations: list[str] | None = Field(default=None, max_length=50)
    preferred_work_models: list[WorkModel] | None = Field(default=None, max_length=3)
    preferred_employment_types: list[EmploymentType] | None = Field(default=None, max_length=5)
    deal_breakers: list[str] | None = Field(default=None, max_length=50)
    default_language: Language | None = None
    status: Literal["active", "inactive"] | None = None
    change_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def normalize_goal_lists(self):
        return _normalize_profile_lists(self)


class ResourceBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    localizations: list[LocalizationInput] = Field(default_factory=list, max_length=2)
    change_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def languages_must_be_unique(self):
        languages = [item.language for item in (self.localizations or [])]
        if len(languages) != len(set(languages)):
            raise ValueError("Each localization language may occur only once.")
        return self


class SkillCreate(ResourceBase):
    canonical_name: str = Field(min_length=1, max_length=300)
    category: SkillCategory
    proficiency_level: SkillLevel | None = None
    years_experience: float | None = Field(default=None, ge=0, le=80)
    last_used_at: date | None = None
    aliases: list[str] = Field(default_factory=list, max_length=100)
    active: bool = True
    status: ContentStatus = "draft"


class SkillUpdate(ResourceBase):
    canonical_name: str | None = Field(default=None, min_length=1, max_length=300)
    category: SkillCategory | None = None
    proficiency_level: SkillLevel | None = None
    years_experience: float | None = Field(default=None, ge=0, le=80)
    last_used_at: date | None = None
    aliases: list[str] | None = Field(default=None, max_length=100)
    active: bool | None = None
    status: ContentStatus | None = None
    localizations: list[LocalizationInput] | None = Field(default=None, max_length=2)


class WorkExperienceCreate(ResourceBase):
    company: str = Field(min_length=1, max_length=500)
    employment_type: str | None = Field(default=None, max_length=100)
    start_date: date
    end_date: date | None = None
    location: str | None = Field(default=None, max_length=500)
    remote_model: str | None = Field(default=None, max_length=50)
    status: ContentStatus = "draft"


class WorkExperienceUpdate(ResourceBase):
    company: str | None = Field(default=None, min_length=1, max_length=500)
    employment_type: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = Field(default=None, max_length=500)
    remote_model: str | None = Field(default=None, max_length=50)
    status: ContentStatus | None = None
    localizations: list[LocalizationInput] | None = Field(default=None, max_length=2)


class PortfolioProjectCreate(ResourceBase):
    canonical_name: str = Field(min_length=1, max_length=500)
    project_type: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=300)
    start_date: date | None = None
    end_date: date | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    repository_url: str | None = Field(default=None, max_length=2048)
    technologies: list[str] = Field(default_factory=list, max_length=100)
    status: ContentStatus = "draft"


class PortfolioProjectUpdate(ResourceBase):
    canonical_name: str | None = Field(default=None, min_length=1, max_length=500)
    project_type: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=300)
    start_date: date | None = None
    end_date: date | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    repository_url: str | None = Field(default=None, max_length=2048)
    technologies: list[str] | None = Field(default=None, max_length=100)
    status: ContentStatus | None = None
    localizations: list[LocalizationInput] | None = Field(default=None, max_length=2)


class EducationCreate(ResourceBase):
    institution: str = Field(min_length=1, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = Field(default=None, max_length=500)
    status: ContentStatus = "draft"


class EducationUpdate(ResourceBase):
    institution: str | None = Field(default=None, min_length=1, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = Field(default=None, max_length=500)
    status: ContentStatus | None = None
    localizations: list[LocalizationInput] | None = Field(default=None, max_length=2)


class CertificateCreate(ResourceBase):
    official_name: str = Field(min_length=1, max_length=500)
    issuer: str = Field(min_length=1, max_length=500)
    issued_at: date | None = None
    expires_at: date | None = None
    credential_id: str | None = Field(default=None, max_length=500)
    verification_url: HttpUrl | None = None
    status: ContentStatus = "draft"


class CertificateUpdate(ResourceBase):
    official_name: str | None = Field(default=None, min_length=1, max_length=500)
    issuer: str | None = Field(default=None, min_length=1, max_length=500)
    issued_at: date | None = None
    expires_at: date | None = None
    credential_id: str | None = Field(default=None, max_length=500)
    verification_url: HttpUrl | None = None
    status: ContentStatus | None = None
    localizations: list[LocalizationInput] | None = Field(default=None, max_length=2)


class ReferenceCreate(ResourceBase):
    full_name: str = Field(min_length=1, max_length=500)
    organization: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=100)
    linkedin_url: HttpUrl | None = None
    preferred_language: Language | None = None
    usage_consent: bool = False
    status: ContentStatus = "draft"

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and value.host not in {"linkedin.com", "www.linkedin.com", "lnkd.in"}:
            raise ValueError("LinkedIn URL must use linkedin.com or lnkd.in")
        return value


class ReferenceUpdate(ResourceBase):
    full_name: str | None = Field(default=None, min_length=1, max_length=500)
    organization: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=100)
    linkedin_url: HttpUrl | None = None
    preferred_language: Language | None = None
    usage_consent: bool | None = None
    status: ContentStatus | None = None
    localizations: list[LocalizationInput] | None = Field(default=None, max_length=2)

    @field_validator("linkedin_url")
    @classmethod
    def validate_linkedin_url(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value is not None and value.host not in {"linkedin.com", "www.linkedin.com", "lnkd.in"}:
            raise ValueError("LinkedIn URL must use linkedin.com or lnkd.in")
        return value


class RevisionResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    revision: int
    action: str
    snapshot: dict
    change_reason: str | None
