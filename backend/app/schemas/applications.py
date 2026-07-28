from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "draft",
    "applied",
    "followed_up",
    "interview",
    "rejected",
    "offer",
    "accepted",
    "withdrawn",
    "closed",
]
ApplicationChannel = Literal[
    "email",
    "company_portal",
    "job_portal",
    "phone",
    "personal",
    "other",
]
EventType = Literal["created", "status_change", "communication", "note"]


class ApplicationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    profile_id: UUID
    status: ApplicationStatus = "draft"
    occurred_at: datetime | None = None
    channel: ApplicationChannel | None = None
    portal_name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=5000)
    next_action: str | None = Field(default=None, max_length=2000)
    next_action_at: datetime | None = None


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus | None = None
    occurred_at: datetime | None = None
    channel: ApplicationChannel | None = None
    portal_name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=5000)
    next_action: str | None = Field(default=None, max_length=2000)
    next_action_at: datetime | None = None


class ApplicationEventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    status: ApplicationStatus | None = None
    occurred_at: datetime | None = None
    channel: ApplicationChannel | None = None
    portal_name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=5000)


class ApplicationEventUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus
    occurred_at: datetime
    channel: ApplicationChannel | None = None
    portal_name: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=5000)
