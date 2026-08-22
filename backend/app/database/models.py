import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(300), unique=True)
    website: Mapped[str | None] = mapped_column(String(2048))
    industry: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(500))

    jobs: Mapped[list["Job"]] = relationship(back_populates="company")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_source_url", "source_url"),
        Index("ix_jobs_content_hash", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(30))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_filename: Mapped[str | None] = mapped_column(String(500))
    source_portal: Mapped[str | None] = mapped_column(String(300))
    location: Mapped[str | None] = mapped_column(String(500))
    work_model: Mapped[str | None] = mapped_column(String(50))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    contract_term: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="analyzing")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archive_reason: Mapped[str | None] = mapped_column(String(500))
    published_at: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    raw_content: Mapped[str | None] = mapped_column(Text)
    normalized_content: Mapped[str] = mapped_column(Text)
    extracted_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    content_hash: Mapped[str] = mapped_column(String(64))
    retrieval_method: Mapped[str] = mapped_column(String(50))
    import_warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)

    company: Mapped[Company | None] = relationship(back_populates="jobs")
    requirements: Mapped[list["JobRequirement"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    activities: Mapped[list["JobActivity"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(100))
    requirement_text: Mapped[str] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(String(500))
    priority: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)

    job: Mapped[Job] = relationship(back_populates="requirements")
    matches: Mapped[list["RequirementMatch"]] = relationship(
        back_populates="job_requirement",
        cascade="all, delete-orphan",
    )


class JobActivity(Base):
    __tablename__ = "job_activities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
    )
    activity_text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), default="responsibility")
    evidence: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    position: Mapped[int] = mapped_column(Integer, default=0)

    job: Mapped[Job] = relationship(back_populates="activities")


class Application(TimestampMixin, Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "profile_id", name="uq_application_job_profile"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE")
    )
    status: Mapped[str] = mapped_column(String(30), default="saved")
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    application_channel: Mapped[str | None] = mapped_column(String(50))
    application_portal_name: Mapped[str | None] = mapped_column(String(100))
    response_channel: Mapped[str | None] = mapped_column(String(50))
    response_portal_name: Mapped[str | None] = mapped_column(String(100))
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_action: Mapped[str | None] = mapped_column(Text)
    next_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="applications")
    documents: Mapped[list["GeneratedDocument"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["ApplicationFile"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
    )


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    channel: Mapped[str | None] = mapped_column(String(50))
    portal_name: Mapped[str | None] = mapped_column(String(100))
    contact_person: Mapped[str | None] = mapped_column(String(300))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    application: Mapped[Application] = relationship(back_populates="events")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "document_type",
            "language",
            "version",
            name="uq_generated_document_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE")
    )
    document_type: Mapped[str] = mapped_column(String(50))
    language: Mapped[str | None] = mapped_column(String(50))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    application: Mapped[Application] = relationship(back_populates="documents")


class ApplicationFile(Base):
    __tablename__ = "application_files"
    __table_args__ = (
        Index("ix_application_files_application_id", "application_id"),
        Index("ix_application_files_sha256", "sha256"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE")
    )
    document_type: Mapped[str] = mapped_column(String(50))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    original_filename: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    file_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    application: Mapped[Application] = relationship(back_populates="files")


class RequirementMatch(Base):
    __tablename__ = "requirement_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_requirement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_requirements.id", ondelete="CASCADE")
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE")
    )
    profile_source: Mapped[str] = mapped_column(String(500))
    match_level: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[list[str]] = mapped_column(JSONB, default=list)
    gap: Mapped[str | None] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    job_requirement: Mapped[JobRequirement] = relationship(back_populates="matches")


class ReviewRun(TimestampMixin, Base):
    __tablename__ = "review_runs"
    __table_args__ = (
        Index("ix_review_runs_subject", "subject_type", "subject_id"),
        Index("ix_review_runs_type_status", "review_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(String(50))
    subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    review_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="pending")
    decision: Mapped[str | None] = mapped_column(String(30))
    overall_confidence: Mapped[float | None] = mapped_column(Float)
    source_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    corrected_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    final_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    field_confidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    retry_instructions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    reviewer_model: Mapped[str | None] = mapped_column(String(500))
    workflow_version: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    technical_error: Mapped[str | None] = mapped_column(Text)

    issues: Mapped[list["ReviewIssue"]] = relationship(
        back_populates="review_run",
        cascade="all, delete-orphan",
    )


class ReviewIssue(Base):
    __tablename__ = "review_issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("review_runs.id", ondelete="CASCADE"),
        index=True,
    )
    field: Mapped[str] = mapped_column(String(500))
    issue_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    suggested_value: Mapped[Any | None] = mapped_column(JSONB)
    position: Mapped[int] = mapped_column(Integer, default=0)

    review_run: Mapped[ReviewRun] = relationship(back_populates="issues")


class ProfileSource(TimestampMixin, Base):
    __tablename__ = "profile_sources"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    evidence_items: Mapped[list["ProfileEvidence"]] = relationship(
        back_populates="profile_source",
        cascade="all, delete-orphan",
    )


class ProfileEvidence(Base):
    __tablename__ = "profile_evidence"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile_sources.id", ondelete="CASCADE")
    )
    label: Mapped[str] = mapped_column(String(500))
    evidence_text: Mapped[str] = mapped_column(Text)
    experience_context: Mapped[str] = mapped_column(String(30))
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    profile_source: Mapped[ProfileSource] = relationship(back_populates="evidence_items")


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name: Mapped[str] = mapped_column(String(300))
    full_name: Mapped[str | None] = mapped_column(String(500))
    nationality: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(2048))
    github_url: Mapped[str | None] = mapped_column(String(2048))
    portfolio_url: Mapped[str | None] = mapped_column(String(2048))
    career_goal: Mapped[str | None] = mapped_column(Text)
    target_roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    target_role_preferences: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    target_industries: Mapped[list[str]] = mapped_column(JSONB, default=list)
    target_locations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    preferred_work_models: Mapped[list[str]] = mapped_column(JSONB, default=list)
    preferred_employment_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    minimum_contract_duration_months: Mapped[int | None] = mapped_column(Integer)
    deal_breakers: Mapped[list[str]] = mapped_column(JSONB, default=list)
    default_language: Mapped[str] = mapped_column(String(5), default="de")
    status: Mapped[str] = mapped_column(String(30), default="active")
    revision: Mapped[int] = mapped_column(Integer, default=1)


class LocalizedTextMixin:
    language: Mapped[str] = mapped_column(String(5))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(Text)
    bullets: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft")


class Skill(TimestampMixin, Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("profile_id", "canonical_name", name="uq_profile_skill"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    canonical_name: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(100))
    proficiency_level: Mapped[str | None] = mapped_column(String(50))
    years_experience: Mapped[float | None] = mapped_column(Float)
    last_used_at: Mapped[date | None] = mapped_column(Date)
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    localizations: Mapped[list["SkillLocalization"]] = relationship(
        cascade="all, delete-orphan"
    )
    evidence_links: Mapped[list["SkillEvidence"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )


class SkillLocalization(LocalizedTextMixin, Base):
    __tablename__ = "skill_localizations"
    __table_args__ = (UniqueConstraint("skill_id", "language", name="uq_skill_language"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))


class SkillEvidence(TimestampMixin, Base):
    """A concrete, auditable use of one skill in a profile resource.

    ``source_resource_id`` intentionally is polymorphic: it may point to a work
    experience, portfolio project, certificate, education entry, or be empty
    for a manually documented training item.
    """

    __tablename__ = "skill_evidence"
    __table_args__ = (
        UniqueConstraint(
            "skill_id", "source_resource_type", "source_resource_id",
            name="uq_skill_evidence_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    source_resource_type: Mapped[str] = mapped_column(String(30))
    source_resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    experience_context: Mapped[str] = mapped_column(String(30))
    evidence_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    skill: Mapped["Skill"] = relationship(back_populates="evidence_links")


class WorkExperience(TimestampMixin, Base):
    __tablename__ = "work_experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    company: Mapped[str] = mapped_column(String(500))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(500))
    remote_model: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    localizations: Mapped[list["WorkExperienceLocalization"]] = relationship(
        cascade="all, delete-orphan"
    )


class WorkExperienceLocalization(LocalizedTextMixin, Base):
    __tablename__ = "work_experience_localizations"
    __table_args__ = (
        UniqueConstraint("work_experience_id", "language", name="uq_work_experience_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    work_experience_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_experiences.id", ondelete="CASCADE")
    )


class PortfolioProject(TimestampMixin, Base):
    __tablename__ = "portfolio_projects"
    __table_args__ = (
        UniqueConstraint("profile_id", "canonical_name", name="uq_profile_portfolio_project"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    canonical_name: Mapped[str] = mapped_column(String(500))
    project_type: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str | None] = mapped_column(String(300))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    repository_url: Mapped[str | None] = mapped_column(String(2048))
    technologies: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    localizations: Mapped[list["PortfolioProjectLocalization"]] = relationship(
        cascade="all, delete-orphan"
    )


class PortfolioProjectLocalization(LocalizedTextMixin, Base):
    __tablename__ = "portfolio_project_localizations"
    __table_args__ = (
        UniqueConstraint(
            "portfolio_project_id",
            "language",
            name="uq_portfolio_project_language",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolio_projects.id", ondelete="CASCADE")
    )


class EducationEntry(TimestampMixin, Base):
    __tablename__ = "education_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    institution: Mapped[str] = mapped_column(String(500))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    localizations: Mapped[list["EducationLocalization"]] = relationship(
        cascade="all, delete-orphan"
    )


class EducationLocalization(LocalizedTextMixin, Base):
    __tablename__ = "education_localizations"
    __table_args__ = (
        UniqueConstraint("education_entry_id", "language", name="uq_education_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    education_entry_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("education_entries.id", ondelete="CASCADE")
    )


class Certificate(TimestampMixin, Base):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    official_name: Mapped[str] = mapped_column(String(500))
    issuer: Mapped[str] = mapped_column(String(500))
    issued_at: Mapped[date | None] = mapped_column(Date)
    expires_at: Mapped[date | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(String(500))
    verification_url: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    localizations: Mapped[list["CertificateLocalization"]] = relationship(
        cascade="all, delete-orphan"
    )


class CertificateLocalization(LocalizedTextMixin, Base):
    __tablename__ = "certificate_localizations"
    __table_args__ = (
        UniqueConstraint("certificate_id", "language", name="uq_certificate_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificates.id", ondelete="CASCADE")
    )


class ProfileReference(TimestampMixin, Base):
    __tablename__ = "profile_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(500))
    organization: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(100))
    linkedin_url: Mapped[str | None] = mapped_column(String(2048))
    preferred_language: Mapped[str | None] = mapped_column(String(5))
    usage_consent: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    revision: Mapped[int] = mapped_column(Integer, default=1)
    localizations: Mapped[list["ReferenceLocalization"]] = relationship(
        cascade="all, delete-orphan"
    )


class ReferenceLocalization(LocalizedTextMixin, Base):
    __tablename__ = "reference_localizations"
    __table_args__ = (
        UniqueConstraint("profile_reference_id", "language", name="uq_reference_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_reference_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("profile_references.id", ondelete="CASCADE")
    )


class ProfileEntityRevision(Base):
    __tablename__ = "profile_entity_revisions"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "revision", name="uq_profile_entity_revision"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    revision: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(30))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    change_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CvImportBatch(Base):
    __tablename__ = "cv_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    source_filename: Mapped[str] = mapped_column(String(500))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    source_language: Mapped[str | None] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(30), default="pending_review")
    source_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CvImportSuggestion(Base):
    __tablename__ = "cv_import_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cv_import_batches.id", ondelete="CASCADE")
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    resource_type: Mapped[str] = mapped_column(String(30))
    proposed_data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_excerpt: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    matched_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    applied_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
