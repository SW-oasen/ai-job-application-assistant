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
                    source_type="certificate" if model is Certificate else "manual",
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
    return {value.strip().lower() for value in values if value.strip().lower() not in STOPWORDS}


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
        }
