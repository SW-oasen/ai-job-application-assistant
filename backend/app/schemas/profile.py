from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app.domain.skill_taxonomy import SkillCategory, SkillLevel

Language = Literal["de", "en"]
ContentStatus = Literal["draft", "approved", "inactive"]


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
    default_language: Language = "de"
    change_reason: str | None = Field(default=None, max_length=1000)


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
    default_language: Language | None = None
    status: Literal["active", "inactive"] | None = None
    change_reason: str | None = Field(default=None, max_length=1000)


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
    preferred_language: Language | None = None
    usage_consent: bool = False
    status: ContentStatus = "draft"


class ReferenceUpdate(ResourceBase):
    full_name: str | None = Field(default=None, min_length=1, max_length=500)
    organization: str | None = Field(default=None, max_length=500)
    email: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=100)
    preferred_language: Language | None = None
    usage_consent: bool | None = None
    status: ContentStatus | None = None
    localizations: list[LocalizationInput] | None = Field(default=None, max_length=2)


class RevisionResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    revision: int
    action: str
    snapshot: dict
    change_reason: str | None
