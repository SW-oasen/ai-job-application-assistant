import hashlib
import json
import re
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.errors import ApplicationError
from app.database.models import (
    Application,
    ApplicationFile,
    Certificate,
    Company,
    EducationEntry,
    Job,
    JobRequirement,
    PortfolioProject,
    Profile,
    ProfileEvidence,
    ProfileSource,
    RequirementMatch,
    Skill,
    WorkExperience,
)
from app.database.session import get_session_factory
from app.parsers.job_metadata import COMPANY_PATTERNS as COMPANY_PATTERNS
from app.parsers.job_metadata import (
    extract_job_metadata,
    first_metadata_match,
)
from app.parsers.markdown_renderer import render_safe_markdown
from app.schemas.matching import (
    EvidenceInput,
    JobMetadataUpdate,
    MatchEvidence,
    MatchingContextResponse,
    MatchingRequest,
    MatchingResponse,
    RequirementMatchResponse,
)
from app.services.application_file_service import remove_stored_files

WORD_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9+#.]{2,}")
STOPWORDS = {
    "and", "the", "with", "for", "from", "und", "der", "die", "das", "mit",
    "für", "von", "eine", "experience", "erfahrung", "kenntnisse",
    "ability", "along", "advantageous", "developing", "highly", "like",
    "professional", "proficiency", "proven", "significant", "skills", "strong",
    "such", "track", "environments", "field", "roles", "programming", "languages",
}

# Small, auditable cross-language concept groups for terminology that commonly
# appears as German compounds in job ads and as English skill names in profiles.
# These tags complement lexical matching; they do not infer a skill without a
# corresponding profile term.
TERM_CONCEPTS = {
    "predictive_modeling": {
        "forecasting", "prediction", "predictive", "vorhersage", "vorhersagen",
        "vorhersagealgorithmus", "vorhersagealgorithmen", "vorhersagemodell",
        "vorhersagemodelle", "pr\u00e4diktiv", "pr\u00e4diktive", "pr\u00e4diktiver",
        "prognose", "prognosen", "prognosemodell", "prognosemodelle",
    },
    "raw_data_analysis": {
        "eda", "exploratory", "rohdaten", "rohdatenanalyse",
        "rohdatenaufbereitung",
    },
    "data_cleaning": {
        "cleaning", "cleansing", "bereinigung", "datenbereinigung",
        "rohdatenaufbereitung",
    },
    "data_quality": {
        "quality", "qualit\u00e4t", "datenqualit\u00e4t",
    },
}
@dataclass
class StoredEvidence:
    item: EvidenceInput
    evidence_id: str


def _first_metadata_match(content: str, patterns: tuple[re.Pattern, ...]) -> str | None:
    return first_metadata_match(content, patterns)


def _job_metadata(job: Job, company: Company | None) -> dict:
    extracted = extract_job_metadata(
        job.normalized_content,
        source_filename=job.source_filename,
        source_url=job.source_url,
    )
    return {
        "title": job.title or extracted["title"],
        "company": company.name if company else extracted["company"],
        "published_text": extracted["published_text"],
        "location": job.location or extracted["location"],
        "work_model": job.work_model or extracted["work_model"],
        "employment_type": job.employment_type or extracted["employment_type"],
        "contract_term": job.contract_term or extracted["contract_term"],
        "source_portal": job.source_portal or extracted["source_portal"],
    }


GERMAN_NATIONALITY_ALIASES = {
    "deutsch",
    "deutsche",
    "deutscher",
    "deutschland",
    "german",
    "germany",
}


def _nationality_evidence_input(profile_id, nationality: str) -> EvidenceInput:
    normalized = nationality.strip().casefold()
    is_german = normalized in GERMAN_NATIONALITY_ALIASES
    statements = [f"Im Profil hinterlegte Staatsangehörigkeit: {nationality.strip()}."]
    keywords = [
        nationality.strip(),
        "Nationalität",
        "Staatsangehörigkeit",
        "nationality",
        "citizenship",
    ]
    if is_german:
        statements.append(
            "Deutschland ist NATO-Mitglied; die deutsche Staatsangehörigkeit ist "
            "damit eine NATO-Staatsangehörigkeit."
        )
        statements.append(
            "Als deutsche Person besteht uneingeschränkter Zugang zum deutschen "
            "Arbeitsmarkt; für Aufenthalt und Beschäftigung in Deutschland ist kein "
            "Aufenthaltstitel und keine Arbeitserlaubnis erforderlich."
        )
        keywords.extend(
            [
                "Deutschland",
                "Germany",
                "deutsche Staatsangehörigkeit",
                "German citizenship",
                "NATO",
                "NATO-Staatsangehörigkeit",
                "NATO citizenship",
                "Arbeitserlaubnis Deutschland",
                "Arbeitsberechtigung Deutschland",
                "uneingeschränkte Arbeitserlaubnis",
                "work permit Germany",
                "work authorization Germany",
                "right to work in Germany",
                "Aufenthaltserlaubnis Deutschland",
                "Aufenthaltsberechtigung Deutschland",
                "Aufenthaltstitel Deutschland",
                "residence permit Germany",
                "residence authorization Germany",
            ]
        )
    source_content = json.dumps(
        {
            "profile_id": str(profile_id),
            "nationality": nationality.strip(),
            "nato_member_nationality": is_german,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return EvidenceInput(
        source_name=f"profile:{profile_id}:nationality",
        source_type="manual",
        source_content=source_content,
        label="Staatsangehörigkeit",
        evidence_text=" ".join(statements),
        experience_context="other",
        keywords=keywords,
    )


def _localized_content(row) -> tuple[str, list[str]]:
    titles = []
    content = []
    for localization in row.localizations:
        titles.append(localization.title)
        content.extend(
            [
                localization.title,
                localization.summary or "",
                *localization.bullets,
            ]
        )
    return "\n".join(part for part in content if part), titles


async def _profile_evidence_inputs(session, profile_id) -> list[EvidenceInput]:
    profile = await session.get(Profile, profile_id)
    if profile is None:
        raise ApplicationError("Profile not found.", code="profile_not_found", status_code=404)

    evidence: list[EvidenceInput] = []
    if profile.nationality and profile.nationality.strip():
        evidence.append(_nationality_evidence_input(profile_id, profile.nationality))
    definitions = (
        (Skill, "skill", "other"),
        (WorkExperience, "experience", "professional"),
        (PortfolioProject, "project", "project"),
        (EducationEntry, "education", "education"),
        (Certificate, "certificate", "training"),
    )
    for model, label_prefix, context in definitions:
        rows = (
            await session.scalars(
                select(model)
                .where(model.profile_id == profile_id)
                .options(selectinload(model.localizations))
            )
        ).all()
        for row in rows:
            data = {
                column.name: getattr(row, column.name)
                for column in row.__table__.columns
                if column.name not in {"created_at", "updated_at"}
            }
            localized_content, titles = _localized_content(row)
            if model is Skill:
                label = row.canonical_name
                core_content = (
                    f"Skill: {row.canonical_name}; Kategorie: {row.category}; "
                    f"Niveau: {row.proficiency_level or 'nicht angegeben'}; "
                    f"Jahre: {row.years_experience if row.years_experience is not None else 'nicht angegeben'}"
                )
                keywords = [row.canonical_name, *row.aliases]
            elif model is WorkExperience:
                label = f"{titles[0] if titles else 'Berufserfahrung'} · {row.company}"
                core_content = (
                    f"Berufserfahrung bei {row.company}, "
                    f"{row.start_date.isoformat()} bis "
                    f"{row.end_date.isoformat() if row.end_date else 'heute'}"
                )
                keywords = [row.company, *titles]
            elif model is PortfolioProject:
                label = titles[0] if titles else row.canonical_name
                core_content = (
                    f"Portfolio-Projekt {row.canonical_name}; "
                    f"Rolle: {row.role or 'nicht angegeben'}; "
                    f"Technologien: {', '.join(row.technologies)}"
                )
                keywords = [row.canonical_name, row.role, *row.technologies, *titles]
            elif model is EducationEntry:
                label = f"{titles[0] if titles else 'Ausbildung'} · {row.institution}"
                core_content = f"Ausbildung bei {row.institution}"
                keywords = [row.institution, *titles]
            else:
                label = f"{row.official_name} · {row.issuer}"
                core_content = f"Zertifikat {row.official_name}, ausgestellt von {row.issuer}"
                keywords = [row.official_name, row.issuer, *titles]

            source_content = json.dumps(data, default=str, ensure_ascii=False, sort_keys=True)
            evidence.append(
                EvidenceInput(
                    source_name=f"profile:{profile_id}:{label_prefix}:{row.id}",
                    source_type=(
                        "certificate"
                        if model is Certificate
                        else "github"
                        if model is PortfolioProject and row.repository_url
                        else "portfolio"
                        if model is PortfolioProject
                        else "manual"
                    ),
                    source_content=source_content,
                    label=label,
                    evidence_text="\n".join(
                        part for part in (core_content, localized_content) if part
                    ),
                    experience_context=context,
                    keywords=[keyword for keyword in keywords if keyword],
                )
            )
    return evidence


async def get_matching_context(job_id, profile_id) -> MatchingContextResponse:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Matching requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        evidence = await _profile_evidence_inputs(session, profile_id)
        return MatchingContextResponse(
            job_id=str(job.id),
            profile_id=str(profile_id),
            job_title=job.title,
            job_language=job.language,
            job_content=job.normalized_content,
            evidence=evidence,
        )


def _terms(text: str, keywords: list[str]) -> set[str]:
    values = WORD_PATTERN.findall(text.lower())
    for keyword in keywords:
        values.extend(WORD_PATTERN.findall(keyword.lower().replace("_", " ")))
    terms = {
        value.strip().lower()
        for value in values
        if value.strip().lower() not in STOPWORDS
    }
    for concept, aliases in TERM_CONCEPTS.items():
        if terms & aliases:
            terms.add(f"concept:{concept}")
    return terms


def _alternative_anchor_terms(requirement: str) -> set[str]:
    tokens = WORD_PATTERN.findall(requirement.lower())
    anchors: set[str] = set()
    for index, token in enumerate(tokens):
        if token not in {"or", "oder"}:
            continue
        if index:
            anchors.add(tokens[index - 1])
        if index + 1 < len(tokens):
            anchors.add(tokens[index + 1])
    return anchors - STOPWORDS


SOFT_SKILL_PATTERN = re.compile(
    r"\b(self[- ]?motivat|independen|team[- ]?(first|orient|player)|"
    r"pragmati|mindset|collaborat|communicat|adaptab|"
    r"selbstmotiv|unabhängig|eigenständig|teamorient|teamfähig|"
    r"pragmatisch|zusammenarbeit|kommunikation|lernbereit)",
    re.IGNORECASE,
)


def _evaluate(
    requirement_id: str,
    requirement: str,
    requirement_terms: set[str],
    evidence: list[StoredEvidence],
    *,
    category: str = "",
    keyword_terms: set[str] | None = None,
) -> RequirementMatchResponse:
    keyword_terms = keyword_terms or set()
    is_soft_skill = category.strip().lower() == "soft_skill" or bool(
        SOFT_SKILL_PATTERN.search(f"{category} {requirement}")
    )
    if not requirement_terms:
        return RequirementMatchResponse(
            requirement_id=requirement_id,
            requirement=requirement,
            match_level="unknown",
            evidence=[],
            explanation="The requirement could not be matched because no usable terms were found.",
            recommended_action="Review and classify this requirement manually.",
            confidence=0.2,
        )

    scored: list[tuple[float, StoredEvidence, set[str]]] = []
    for stored in evidence:
        evidence_terms = _terms(stored.item.evidence_text, stored.item.keywords)
        overlap = requirement_terms & evidence_terms
        if overlap:
            scored.append((len(overlap) / len(requirement_terms), stored, overlap))
    scored.sort(key=lambda pair: pair[0], reverse=True)

    if not scored:
        if is_soft_skill:
            return RequirementMatchResponse(
                requirement_id=requirement_id,
                requirement=requirement,
                match_level="unknown",
                evidence=[],
                explanation=(
                    "Soft skills cannot be treated as a factual gap solely because "
                    "no matching profile keyword was found."
                ),
                recommended_action=(
                    "Review references and concrete work examples manually; add a "
                    "behavioral example only when it is verifiable."
                ),
                confidence=0.3,
            )
        return RequirementMatchResponse(
            requirement_id=requirement_id,
            requirement=requirement,
            match_level="gap",
            evidence=[],
            explanation="No documented profile evidence supports this requirement.",
            recommended_action="Do not claim this skill; add verified evidence or address the gap.",
            confidence=0.9,
        )

    aggregate_overlap = set().union(*(overlap for _, _, overlap in scored))
    aggregate_score = len(aggregate_overlap) / len(requirement_terms)
    relevant = [
        stored
        for score, stored, overlap in scored
        if score >= 0.2 or len(overlap) >= 2 or bool(overlap & keyword_terms)
    ]
    has_direct_keyword = any(
        bool(overlap & keyword_terms) for _, _, overlap in scored
    )
    has_alternatives = bool(re.search(r"\b(or|oder)\b", requirement, re.IGNORECASE))
    alternative_anchors = _alternative_anchor_terms(requirement)
    has_professional_alternative = has_alternatives and any(
        stored.item.experience_context == "professional"
        and bool(overlap & alternative_anchors)
        for _, stored, overlap in scored
    )
    if (
        not relevant
        and not has_professional_alternative
        and aggregate_score < 0.35
    ):
        if is_soft_skill:
            return RequirementMatchResponse(
                requirement_id=requirement_id,
                requirement=requirement,
                match_level="unknown",
                evidence=[],
                explanation=(
                    "Only ambiguous wording overlaps were found. Soft skills require "
                    "a concrete behavioral example or reference."
                ),
                recommended_action=(
                    "Review this criterion manually instead of presenting it as a gap."
                ),
                confidence=0.3,
            )
        return RequirementMatchResponse(
            requirement_id=requirement_id,
            requirement=requirement,
            match_level="gap",
            evidence=[],
            explanation=(
                "Only incidental word overlap was found; no sufficiently relevant "
                "profile evidence supports this requirement."
            ),
            recommended_action=(
                "Do not claim this experience; add a concrete verified profile entry "
                "if applicable."
            ),
            confidence=0.85,
        )
    if not relevant:
        relevant = [stored for _, stored, _ in scored]
    has_professional = any(
        stored.item.experience_context == "professional" for stored in relevant
    )
    # Context words are deliberately excluded from the lexical term set because
    # they are not skills. Detect them in the original requirement instead.
    requires_professional_context = bool(
        re.search(r"\b(production|professional)\b", requirement, re.IGNORECASE)
    )
    is_nationality_or_work_authorization_requirement = bool(
        re.search(
            r"\b(nato|nationalit|citizenship|staatsangeh(?:ö|oe)rig|"
            r"arbeitserlaub|arbeitsberechtig|work (?:permit|authori[sz]ation)|"
            r"right to work|aufenthalt(?:serlaub|sberechtig|stitel)|"
            r"residence (?:permit|authori[sz]ation))",
            requirement,
            re.IGNORECASE,
        )
    )
    has_nationality_evidence = any(
        stored.item.label == "Staatsangehörigkeit" for stored in relevant
    )
    if (
        is_nationality_or_work_authorization_requirement
        and has_nationality_evidence
        and aggregate_score >= 0.6
    ):
        level = "strong_match"
        explanation = "Documented profile data directly supports this nationality requirement."
        action = "Use the cited nationality only for eligibility verification."
    elif has_professional_alternative or (has_professional and aggregate_score >= 0.6):
        level = "strong_match"
        explanation = "Documented professional evidence directly supports this requirement."
        action = "Use the cited professional evidence and keep the wording factual."
    elif requires_professional_context and not has_professional:
        if aggregate_score >= 0.2 and len(scored) >= 2:
            level = "partial_match"
            explanation = (
                "Several components are supported by education or skills, but the "
                "requested professional context is not fully documented."
            )
            action = "Claim only the supported components and state the professional gap."
        else:
            level = "transferable"
            explanation = (
                "Related evidence exists, but no professional or production evidence "
                "supports the required context."
            )
            action = (
                "Label this as transferable or project experience, "
                "not production experience."
            )
    elif has_professional or aggregate_score >= 0.35 or has_direct_keyword:
        level = "partial_match"
        explanation = "The combined profile evidence supports part, but not all, of this requirement."
        action = "Describe the supported portion and avoid implying broader experience."
    else:
        level = "transferable"
        explanation = (
            "Related evidence exists, but it comes from projects, training, or education "
            "rather than professional experience."
        )
        action = "Label this as transferable or project experience, not production experience."

    cited = [
        MatchEvidence(
            evidence_id=stored.evidence_id,
            source_name=stored.item.source_name,
            label=stored.item.label,
            evidence_text=stored.item.evidence_text,
            experience_context=stored.item.experience_context,
        )
        for stored in relevant
    ]
    return RequirementMatchResponse(
        requirement_id=requirement_id,
        requirement=requirement,
        match_level=level,
        evidence=cited,
        explanation=explanation,
        recommended_action=action,
        confidence=round(
            min(0.95, 0.5 + aggregate_score * 0.45 + (0.1 if has_professional else 0)),
            2,
        ),
    )


async def evaluate_matching(payload: MatchingRequest) -> MatchingResponse:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Matching requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )

    async with session_factory() as session:
        job = await session.scalar(select(Job).where(Job.id == payload.job_id))
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)

        stored_evidence: list[StoredEvidence] = []
        evidence_inputs = list(payload.evidence)
        if payload.profile_id:
            evidence_inputs.extend(
                await _profile_evidence_inputs(session, payload.profile_id)
            )
        for item in evidence_inputs:
            content_hash = hashlib.sha256(item.source_content.encode("utf-8")).hexdigest()
            source = await session.scalar(
                select(ProfileSource).where(ProfileSource.content_hash == content_hash)
            )
            if source is None:
                source = ProfileSource(
                    name=item.source_name,
                    source_type=item.source_type,
                    content=item.source_content,
                    content_hash=content_hash,
                )
                session.add(source)
                await session.flush()
            evidence_row = await session.scalar(
                select(ProfileEvidence).where(
                    ProfileEvidence.profile_source_id == source.id,
                    ProfileEvidence.label == item.label,
                    ProfileEvidence.evidence_text == item.evidence_text,
                )
            )
            if evidence_row is None:
                evidence_row = ProfileEvidence(
                    profile_source_id=source.id,
                    label=item.label,
                    evidence_text=item.evidence_text,
                    experience_context=item.experience_context,
                    keywords=item.keywords,
                )
                session.add(evidence_row)
                await session.flush()
            stored_evidence.append(StoredEvidence(item=item, evidence_id=str(evidence_row.id)))

        # A fresh extraction may intentionally omit requirements that an older
        # workflow run classified incorrectly. Remove the previous result set
        # for this job/profile before storing the recalculated matches.
        await session.execute(
            delete(RequirementMatch).where(
                RequirementMatch.profile_id == payload.profile_id,
                RequirementMatch.job_requirement_id.in_(
                    select(JobRequirement.id).where(JobRequirement.job_id == job.id)
                ),
            )
        )

        results: list[RequirementMatchResponse] = []
        for item in payload.requirements:
            requirement = await session.scalar(
                select(JobRequirement).where(
                    JobRequirement.job_id == job.id,
                    JobRequirement.requirement_text == item.requirement,
                )
            )
            if requirement is None:
                requirement = JobRequirement(
                    job_id=job.id,
                    category=item.category,
                    requirement_text=item.requirement,
                    priority=item.priority,
                    keywords=item.keywords,
                )
                session.add(requirement)
                await session.flush()

            result = _evaluate(
                str(requirement.id),
                item.requirement,
                _terms(item.requirement, item.keywords),
                stored_evidence,
                category=item.category,
                keyword_terms=_terms("", item.keywords),
            )
            session.add(
                RequirementMatch(
                    job_requirement_id=requirement.id,
                    profile_id=payload.profile_id,
                    profile_source=", ".join(
                        sorted(
                            {
                                entry.experience_context
                                for entry in result.evidence
                            }
                        )
                    )
                    or "none",
                    match_level=result.match_level,
                    evidence=[entry.model_dump() for entry in result.evidence],
                    gap=result.requirement if result.match_level == "gap" else None,
                    explanation=result.explanation,
                    recommended_action=result.recommended_action,
                    confidence=result.confidence,
                )
            )
            results.append(result)

        await session.commit()

    summary: dict[str, int] = {}
    for result in results:
        summary[result.match_level] = summary.get(result.match_level, 0) + 1
    return MatchingResponse(job_id=str(payload.job_id), matches=results, summary=summary)


async def list_matching_jobs(profile_id=None) -> list[dict]:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Matching requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        matched_statement = (
            select(JobRequirement.job_id)
            .join(
                RequirementMatch,
                RequirementMatch.job_requirement_id == JobRequirement.id,
            )
            .distinct()
        )
        if profile_id is not None:
            matched_statement = matched_statement.where(
                RequirementMatch.profile_id == profile_id
            )
        matched_job_ids = set((await session.scalars(matched_statement)).all())
        rows = (
            await session.execute(
                select(Job, Company)
                .outerjoin(Company, Company.id == Job.company_id)
                .order_by(Job.imported_at.desc())
            )
        ).all()
        return [
            {
                "id": str(job.id),
                "title": job.title or "Unbenannte Stelle",
                **_job_metadata(job, company),
                "source_url": job.source_url,
                "source_filename": job.source_filename,
                "language": job.language,
                "published_at": job.published_at,
                "deadline": job.deadline,
                "imported_at": job.imported_at,
                "has_matching": job.id in matched_job_ids,
            }
            for job, company in rows
        ]


async def get_matching_job(job_id) -> dict:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Matching requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        row = (
            await session.execute(
                select(Job, Company)
                .outerjoin(Company, Company.id == Job.company_id)
                .where(Job.id == job_id)
            )
        ).one_or_none()
        if row is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        job, company = row
        requirements = (
            await session.scalars(
                select(JobRequirement)
                .where(JobRequirement.job_id == job.id)
                .order_by(
                    JobRequirement.category,
                    JobRequirement.priority,
                    JobRequirement.requirement_text,
                )
            )
        ).all()
        return {
            "id": str(job.id),
            "title": job.title or "Unbenannte Stelle",
            **_job_metadata(job, company),
            "source_type": job.source_type,
            "source_url": job.source_url,
            "source_filename": job.source_filename,
            "language": job.language,
            "status": job.status,
            "published_at": job.published_at,
            "deadline": job.deadline,
            "imported_at": job.imported_at,
            "retrieval_method": job.retrieval_method,
            "import_warnings": job.import_warnings or [],
            "requirements": [
                {
                    "id": str(requirement.id),
                    "category": requirement.category,
                    "requirement": requirement.requirement_text,
                    "priority": requirement.priority,
                    "keywords": requirement.keywords or [],
                    "confidence": requirement.confidence,
                }
                for requirement in requirements
            ],
            "content": job.normalized_content,
            "content_html": render_safe_markdown(job.normalized_content),
        }


async def update_job_metadata(job_id, payload: JobMetadataUpdate) -> dict:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Job metadata editing requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)

        values = payload.model_dump(exclude_unset=True)
        if "company" in values:
            company_name = (values.pop("company") or "").strip()
            if company_name:
                company = await session.scalar(
                    select(Company).where(func.lower(Company.name) == company_name.lower())
                )
                if company is None:
                    company = Company(name=company_name)
                    session.add(company)
                    await session.flush()
                job.company_id = company.id
            else:
                job.company_id = None

        for field, value in values.items():
            if isinstance(value, str):
                value = value.strip() or None
            setattr(job, field, value)
        await session.commit()
    return await get_matching_job(job_id)


async def delete_matching_job(job_id) -> None:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Job deletion requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        storage_keys = (
            await session.scalars(
                select(ApplicationFile.storage_key)
                .join(Application, Application.id == ApplicationFile.application_id)
                .where(Application.job_id == job_id)
            )
        ).all()
        await session.delete(job)
        await session.commit()
    remove_stored_files(list(storage_keys))


def _normalized_target_text(value: object) -> str:
    return " ".join(
        re.findall(
            r"[a-z0-9+#]+",
            str(value or "").casefold()
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss"),
        )
    )


def _target_overlap(desired: str, actual: str) -> float:
    desired_terms = set(_normalized_target_text(desired).split())
    actual_terms = set(_normalized_target_text(actual).split())
    if not desired_terms or not actual_terms:
        return 0.0
    return len(desired_terms & actual_terms) / len(desired_terms)


def _preference_criterion(
    *,
    key: str,
    label: str,
    desired: list[str],
    actual: str | None,
    weight: int,
) -> dict:
    if not desired:
        return {
            "key": key,
            "label": label,
            "status": "not_configured",
            "desired": [],
            "actual": actual,
            "score": None,
            "weight": weight,
            "explanation": "Für dieses Kriterium ist keine Zielpräferenz hinterlegt.",
        }
    if not actual:
        return {
            "key": key,
            "label": label,
            "status": "unknown",
            "desired": desired,
            "actual": None,
            "score": None,
            "weight": weight,
            "explanation": "Die Stellenanzeige enthält hierzu keine auswertbare Angabe.",
        }
    best = max(_target_overlap(value, actual) for value in desired)
    if best >= 1:
        status, score = "match", 1.0
    elif best >= 0.5:
        status, score = "partial", 0.6
    else:
        status, score = "mismatch", 0.0
    return {
        "key": key,
        "label": label,
        "status": status,
        "desired": desired,
        "actual": actual,
        "score": score,
        "weight": weight,
        "explanation": {
            "match": "Die Stellenangabe entspricht einer hinterlegten Zielpräferenz.",
            "partial": "Die Stellenangabe überschneidet sich teilweise mit einer Zielpräferenz.",
            "mismatch": "Die Stellenangabe entspricht keiner hinterlegten Zielpräferenz.",
        }[status],
    }


def _canonical_work_model(value: str | None) -> str | None:
    normalized = _normalized_target_text(value)
    if any(term in normalized for term in ("remote", "homeoffice", "home office")):
        return "remote"
    if "hybrid" in normalized:
        return "hybrid"
    if any(term in normalized for term in ("onsite", "on site", "vor ort", "praesenz")):
        return "onsite"
    return normalized or None


def _canonical_employment_type(value: str | None) -> str | None:
    normalized = _normalized_target_text(value)
    mappings = (
        ("working_student", ("werkstudent", "working student")),
        ("internship", ("praktikum", "internship", "intern")),
        ("freelance", ("freelance", "freiberuf", "contractor")),
        ("permanent", ("festanstellung", "unbefrist", "permanent", "full time", "vollzeit")),
        ("temporary", ("befrist", "temporary", "fixed term")),
    )
    for canonical, markers in mappings:
        if any(marker in normalized for marker in markers):
            return canonical
    return normalized or None


def _evaluate_target_fit(job: Job, company: Company | None, profile: Profile) -> dict:
    criteria = [
        _preference_criterion(
            key="role",
            label="Zielrolle",
            desired=profile.target_roles or [],
            actual=job.title,
            weight=40,
        ),
        _preference_criterion(
            key="industry",
            label="Zielbranche",
            desired=profile.target_industries or [],
            actual=company.industry if company else None,
            weight=10,
        ),
        _preference_criterion(
            key="location",
            label="Zielort",
            desired=profile.target_locations or [],
            actual=job.location,
            weight=20,
        ),
        _preference_criterion(
            key="work_model",
            label="Arbeitsmodell",
            desired=profile.preferred_work_models or [],
            actual=_canonical_work_model(job.work_model),
            weight=15,
        ),
        _preference_criterion(
            key="employment_type",
            label="Beschäftigungsart",
            desired=profile.preferred_employment_types or [],
            actual=_canonical_employment_type(job.employment_type),
            weight=15,
        ),
    ]
    source_text = " ".join(
        value
        for value in (
            job.title,
            job.location,
            job.work_model,
            job.employment_type,
            job.normalized_content,
        )
        if value
    )
    exclusions = []
    hard_conflict = False
    for value in profile.deal_breakers or []:
        normalized = _normalized_target_text(value)
        actual_employment = _canonical_employment_type(job.employment_type)
        definite = (
            ("freiberuf" in normalized or "freelance" in normalized)
            and actual_employment == "freelance"
        ) or (
            ("student" in normalized or "werkstudent" in normalized)
            and (
                actual_employment == "working_student"
                or "immatrikul" in _normalized_target_text(source_text)
            )
        )
        overlap = _target_overlap(value, source_text)
        status = "conflict" if definite else "review" if overlap >= 0.5 else "clear"
        hard_conflict = hard_conflict or definite
        exclusions.append(
            {
                "criterion": value,
                "status": status,
                "explanation": (
                    "Das Ausschlusskriterium trifft anhand strukturierter Stellenangaben zu."
                    if definite
                    else "Die Stellenbeschreibung enthält ähnliche Begriffe; bitte manuell prüfen."
                    if status == "review"
                    else "Kein eindeutiger Hinweis auf dieses Ausschlusskriterium gefunden."
                ),
            }
        )

    scored = [item for item in criteria if item["score"] is not None]
    total_weight = sum(item["weight"] for item in scored)
    score = (
        round(
            sum(item["score"] * item["weight"] for item in scored)
            / total_weight
            * 100
        )
        if total_weight
        else None
    )
    if hard_conflict:
        level = "conflict"
    elif score is None:
        level = "unknown"
    elif score >= 75:
        level = "strong"
    elif score >= 45:
        level = "partial"
    else:
        level = "weak"
    return {
        "level": level,
        "score": score,
        "criteria": criteria,
        "exclusions": exclusions,
        "summary": {
            "strong": "Die bekannten Stellenmerkmale passen gut zum Zielprofil.",
            "partial": "Die Stelle passt teilweise zum Zielprofil.",
            "weak": "Mehrere bekannte Stellenmerkmale weichen vom Zielprofil ab.",
            "conflict": "Mindestens ein strukturiert erkennbares Ausschlusskriterium trifft zu.",
            "unknown": "Für eine Ziel-Fit-Bewertung fehlen auswertbare Stellenmerkmale.",
        }[level],
    }


async def get_target_fit(job_id, profile_id) -> dict:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Matching requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        row = (
            await session.execute(
                select(Job, Company)
                .outerjoin(Company, Company.id == Job.company_id)
                .where(Job.id == job_id)
            )
        ).one_or_none()
        if row is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        profile = await session.get(Profile, profile_id)
        if profile is None:
            raise ApplicationError("Profile not found.", code="profile_not_found", status_code=404)
        return _evaluate_target_fit(row[0], row[1], profile)


def _qualification_fit(matches: list[dict]) -> dict:
    priority_weights = {"must": 3, "should": 2, "nice_to_have": 1}
    level_scores = {
        "strong_match": 1.0,
        "partial_match": 0.65,
        "transferable": 0.4,
        "gap": 0.0,
        "unknown": 0.0,
    }
    weighted_requirements = []
    achieved = 0.0
    possible = 0
    for match in matches:
        priority = match.get("priority") or "should"
        match_level = match.get("match_level") or "unknown"
        weight = priority_weights.get(priority, 2)
        fulfillment = level_scores.get(match_level, 0.0)
        contribution = weight * fulfillment
        achieved += contribution
        possible += weight
        weighted_requirements.append(
            {
                "requirement_id": match.get("requirement_id"),
                "requirement": match.get("requirement"),
                "priority": priority,
                "priority_weight": weight,
                "match_level": match_level,
                "fulfillment_percent": round(fulfillment * 100),
                "weighted_points": round(contribution, 2),
                "possible_points": weight,
            }
        )
    score = round(achieved / possible * 100) if possible else None
    if score is None:
        level = "unknown"
    elif score >= 80:
        level = "strong"
    elif score >= 60:
        level = "good"
    elif score >= 40:
        level = "partial"
    else:
        level = "weak"
    return {
        "score": score,
        "level": level,
        "achieved_points": round(achieved, 2),
        "possible_points": possible,
        "requirement_count": len(matches),
        "weights": {
            "priority": priority_weights,
            "match_level_percent": {
                key: round(value * 100) for key, value in level_scores.items()
            },
        },
        "weighted_requirements": weighted_requirements,
        "summary": {
            "strong": "Die gewichteten Anforderungen werden insgesamt sehr gut erfüllt.",
            "good": "Die gewichteten Anforderungen werden insgesamt gut erfüllt.",
            "partial": "Die gewichteten Anforderungen werden teilweise erfüllt.",
            "weak": "Viele oder besonders wichtige Anforderungen sind nicht ausreichend belegt.",
            "unknown": "Es liegen noch keine bewerteten Anforderungen vor.",
        }[level],
    }


def _matching_recommendation(
    qualification_fit: dict,
    target_fit: dict,
) -> dict:
    qualification_score = qualification_fit.get("score")
    target_score = target_fit.get("score")
    target_conflict = target_fit.get("level") == "conflict"
    must_gaps = sum(
        1
        for item in qualification_fit.get("weighted_requirements", [])
        if item["priority"] == "must" and item["match_level"] in {"gap", "unknown"}
    )
    review_exclusions = sum(
        1
        for item in target_fit.get("exclusions", [])
        if item["status"] == "review"
    )

    if target_conflict:
        verdict = "deprioritize"
        headline = "Nicht priorisieren"
        rationale = (
            "Ein strukturiert erkennbares Ausschlusskriterium trifft zu. "
            "Die Stelle sollte nur weiterverfolgt werden, wenn dieses Kriterium "
            "inhaltlich falsch erkannt wurde oder nicht mehr gilt."
        )
    elif qualification_score is None:
        verdict = "review"
        headline = "Zunächst Qualifikationen prüfen"
        rationale = "Es liegt noch keine belastbare Qualifikationsbewertung vor."
    elif target_score is None:
        verdict = "review"
        headline = "Ziel-Fit manuell prüfen"
        rationale = (
            "Der Qualifikations-Fit ist bewertbar, für den Ziel-Fit fehlen jedoch "
            "ausreichende strukturierte Stellenmerkmale."
        )
    elif qualification_score >= 60 and target_score >= 60 and must_gaps == 0:
        verdict = "apply"
        headline = "Bewerbung empfohlen"
        rationale = (
            "Qualifikationen und berufliche Ziele passen insgesamt gut zur Stelle; "
            "es wurden keine unbelegten Muss-Anforderungen erkannt."
        )
    elif qualification_score >= 40 and target_score >= 60:
        verdict = "consider"
        headline = "Bewerbung erwägen"
        rationale = (
            "Die Stelle passt zum Zielprofil, der Qualifikations-Fit ist jedoch nur "
            "teilweise gegeben. Vor einer Bewerbung sollten die wichtigsten Lücken "
            "und übertragbaren Erfahrungen geprüft werden."
        )
    elif qualification_score >= 60 and target_score < 45:
        verdict = "review"
        headline = "Fachlich passend, Ziel-Fit schwach"
        rationale = (
            "Die Qualifikationen passen, mehrere Stellenmerkmale weichen aber vom "
            "beruflichen Zielprofil ab. Nur weiterverfolgen, wenn diese Präferenzen "
            "verhandelbar sind."
        )
    elif qualification_score < 40:
        verdict = "deprioritize"
        headline = "Eher nicht priorisieren"
        rationale = (
            "Der gewichtete Qualifikations-Fit ist niedrig. Eine Bewerbung ist nur "
            "sinnvoll, wenn die Stelle strategisch besonders interessant ist und "
            "die Muss-Lücken realistisch erklärt oder geschlossen werden können."
        )
    else:
        verdict = "review"
        headline = "Manuell abwägen"
        rationale = (
            "Die beiden Bewertungen ergeben kein eindeutiges Gesamtbild. "
            "Einzelanforderungen und Zielkriterien sollten manuell geprüft werden."
        )

    reasons = [
        (
            f"Qualifikations-Fit: {qualification_score} %"
            if qualification_score is not None
            else "Qualifikations-Fit: unklar"
        ),
        (
            f"Ziel-Fit: {target_score} %"
            if target_score is not None
            else "Ziel-Fit: unklar"
        ),
    ]
    if must_gaps:
        reasons.append(f"{must_gaps} unbelegte oder unklare Muss-Anforderung(en)")
    if review_exclusions:
        reasons.append(f"{review_exclusions} Ausschlusskriterium/-kriterien manuell prüfen")
    return {
        "verdict": verdict,
        "headline": headline,
        "rationale": rationale,
        "reasons": reasons,
        "requires_manual_review": (
            verdict in {"consider", "review"}
            or must_gaps > 0
            or review_exclusions > 0
        ),
    }


async def get_stored_matching(job_id, profile_id) -> dict:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Matching requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        job_row = (
            await session.execute(
                select(Job, Company)
                .outerjoin(Company, Company.id == Job.company_id)
                .where(Job.id == job_id)
            )
        ).one_or_none()
        if job_row is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        job, company = job_row
        profile = await session.get(Profile, profile_id)
        if profile is None:
            raise ApplicationError(
                "Profile not found.",
                code="profile_not_found",
                status_code=404,
            )
        rows = (
            await session.execute(
                select(JobRequirement, RequirementMatch)
                .join(
                    RequirementMatch,
                    RequirementMatch.job_requirement_id == JobRequirement.id,
                )
                .where(
                    JobRequirement.job_id == job_id,
                    RequirementMatch.profile_id == profile_id,
                )
                .order_by(JobRequirement.priority, JobRequirement.requirement_text)
            )
        ).all()
        matches = [
            {
                "requirement_id": str(requirement.id),
                "requirement": requirement.requirement_text,
                "category": requirement.category,
                "priority": requirement.priority,
                "keywords": requirement.keywords,
                "match_level": match.match_level,
                "evidence": match.evidence,
                "gap": match.gap,
                "explanation": match.explanation,
                "recommended_action": match.recommended_action,
                "confidence": match.confidence,
                "evaluated_at": match.evaluated_at,
            }
            for requirement, match in rows
        ]
        summary: dict[str, int] = {}
        for match in matches:
            level = match["match_level"]
            summary[level] = summary.get(level, 0) + 1
        qualification_fit = _qualification_fit(matches)
        target_fit = _evaluate_target_fit(job, company, profile)
        return {
            "job": {
                "id": str(job.id),
                "title": job.title or "Unbenannte Stelle",
                **_job_metadata(job, company),
                "source_url": job.source_url,
                "source_filename": job.source_filename,
                "language": job.language,
                "published_at": job.published_at,
                "deadline": job.deadline,
                "imported_at": job.imported_at,
            },
            "profile": {
                "id": str(profile.id),
                "display_name": profile.display_name,
            },
            "matches": matches,
            "summary": summary,
            "qualification_fit": qualification_fit,
            "target_fit": target_fit,
            "recommendation": _matching_recommendation(
                qualification_fit,
                target_fit,
            ),
        }
