import hashlib
import json
import re
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

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
    JobActivity,
    JobRequirement,
    PortfolioProject,
    Profile,
    ProfileEvidence,
    ProfileSource,
    RequirementMatch,
    Skill,
    AppliedSkillLink,
    WorkExperience,
)
from app.database.session import get_session_factory
from app.core.config import get_settings
from app.services.embedding_service import (
    build_evidence_embedding_text,
    build_requirement_embedding_text,
    create_embedding_provider,
)
from app.services.hybrid_search import ChromaEvidenceStore
from app.parsers.job_metadata import (
    COMPANY_PATTERNS,
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
    RequirementInput,
    RequirementMatchResponse,
)
from app.services.application_file_service import remove_stored_files

__all__ = ["COMPANY_PATTERNS"]

WORD_PATTERN = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9+#.]{2,}")
MIN_YEARS_PATTERN = re.compile(
    r"(?:min_years:|mindestens\s+|at\s+least\s+|minimum\s+)?"
    r"(\d+(?:[.,]\d+)?)\s*(?:\+|plus)?\s*"
    r"(?:jahr(?:e|en)?|years?)\s*(?:of\s+)?"
    r"(?:berufs?\s*|profession(?:al)?\s+)?(?:erfahrung|experience)",
    re.IGNORECASE,
)
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
TARGET_FIT_CONCEPTS = {
    "data_science": {"data science", "data scientist", "datenanalyse", "data analysis", "statistik", "dataset", "evaluation", "benchmark", "experiment"},
    "machine_learning": {"machine learning", "ai ml", "mlops", "scikit", "pytorch", "tensorflow"},
    "automation": {"automatisierung", "automation", "automate", "workflow", "pipeline"},
    "ai_development": {"ki", "ai", "künstliche intelligenz", "artificial intelligence", "machine learning", "prototyp", "softwaredevelopment", "softwareentwicklung"},
}
SENIORITY_RANK = {"entry": 0, "junior": 1, "professional": 2, "senior": 3, "lead": 4}
TARGET_LEVEL_RANK = {"entry": 0, "junior": 1, "mid": 2, "senior": 3, "staff": 4, "principal": 5, "lead": 6, "manager": 6}
@dataclass
class StoredEvidence:
    item: EvidenceInput
    evidence_id: str


def _evidence_weight(stored: StoredEvidence) -> float:
    """Prefer production evidence while retaining projects and training as proof."""
    try:
        source = json.loads(stored.item.source_content)
    except (TypeError, json.JSONDecodeError):
        source = {}
    if isinstance(source, dict) and source.get("source_type") == "manual_training":
        return 0.5
    return {"professional": 1.0, "project": 0.9, "training": 0.8}.get(
        stored.item.experience_context, 0.5
    )


def _minimum_years(requirement: str, normalized_value: str | None = None) -> float | None:
    value = normalized_value or ""
    match = MIN_YEARS_PATTERN.search(value) or MIN_YEARS_PATTERN.search(requirement)
    if match is None:
        return None
    return float(match.group(1).replace(",", "."))


def _skill_years(stored: StoredEvidence) -> float | None:
    try:
        data = json.loads(stored.item.source_content)
    except (TypeError, json.JSONDecodeError):
        data = {}
    years = data.get("years_experience") if isinstance(data, dict) else None
    if years is None:
        match = re.search(r"\bJahre:\s*(\d+(?:[.,]\d+)?)", stored.item.evidence_text)
        years = match.group(1).replace(",", ".") if match else None
    if years is None:
        return None
    try:
        return float(years)
    except (TypeError, ValueError):
        return None


def _evaluate_seniority(
    requirement_id: str,
    requirement: str,
    minimum_years: float,
    evidence: list[StoredEvidence],
) -> RequirementMatchResponse:
    skill_evidence = [
        (stored, years)
        for stored in evidence
        if (years := _skill_years(stored)) is not None
        and stored.item.experience_context == "professional"
    ]
    # Generic experience requirements are evaluated from the longest
    # documented employment station. Skill-specific requirements stay bound
    # to explicit skill evidence.
    generic = not re.search(r"\b(?:mit|in|with|for)\b", requirement, re.IGNORECASE)
    if generic:
        station_years = []
        for stored in evidence:
            if stored.item.experience_context != "professional":
                continue
            try:
                data = json.loads(stored.item.source_content)
                start = datetime.fromisoformat(str(data["start_date"])).date()
                end = datetime.fromisoformat(str(data["end_date"])).date() if data.get("end_date") else datetime.now(UTC).date()
                station_years.append((max(0.0, (end - start).days / 365.25), stored))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        if station_years:
            highest_years, stored = max(station_years, key=lambda item: item[0])
            return RequirementMatchResponse(
                requirement_id=requirement_id,
                requirement=requirement,
                match_level="strong_match" if highest_years >= minimum_years else "gap",
                evidence=[],
                explanation=f"Die längste dokumentierte Berufsstation umfasst {highest_years:g} Jahre.",
                recommended_action="",
                confidence=0.95,
            )
    if not skill_evidence:
        return RequirementMatchResponse(
            requirement_id=requirement_id,
            requirement=requirement,
            match_level="unknown",
            evidence=[],
            explanation="Für die Skills des Profils sind keine Erfahrungsjahre dokumentiert.",
            recommended_action="Erfahrungsjahre bei den relevanten Skills ergänzen und manuell prüfen.",
            confidence=0.3,
        )
    highest_years = max(years for _, years in skill_evidence)
    cited = [
        MatchEvidence(
            evidence_id=stored.evidence_id,
            source_name=stored.item.source_name,
            label=stored.item.label,
            evidence_text=stored.item.evidence_text,
            experience_context=stored.item.experience_context,
        )
        for stored, years in skill_evidence
        if years == highest_years
    ]
    if highest_years >= minimum_years:
        return RequirementMatchResponse(
            requirement_id=requirement_id,
            requirement=requirement,
            match_level="strong_match",
            evidence=cited,
            explanation=(
                f"Das Profil weist {highest_years:g} Jahre Skill-Erfahrung nach "
                f"und erfüllt damit die Mindestanforderung von {minimum_years:g} Jahren."
            ),
            recommended_action="Die nachgewiesenen Erfahrungsjahre sachlich angeben.",
            confidence=0.95,
        )
    return RequirementMatchResponse(
        requirement_id=requirement_id,
        requirement=requirement,
        match_level="gap",
        evidence=cited,
        explanation=(
            f"Das Profil weist höchstens {highest_years:g} Jahre Skill-Erfahrung nach; "
            f"gefordert sind mindestens {minimum_years:g} Jahre."
        ),
        recommended_action="Die fehlenden Erfahrungsjahre nicht behaupten; Anforderung manuell prüfen.",
        confidence=0.95,
    )


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
            if model is WorkExperience:
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
    evidence.extend(await _linked_skill_evidence_inputs(session, profile_id))
    return evidence


async def _linked_skill_evidence_inputs(session, profile_id) -> list[EvidenceInput]:
    links = (await session.scalars(
        select(AppliedSkillLink).join(Skill).where(Skill.profile_id == profile_id)
        .options(selectinload(AppliedSkillLink.skill))
    )).all()
    result: list[EvidenceInput] = []
    for link in links:
        source = None
        if link.source_resource_type == "experience" and link.source_resource_id:
            source = await session.scalar(
                select(WorkExperience)
                .where(WorkExperience.id == link.source_resource_id)
                .options(selectinload(WorkExperience.localizations))
            )
        elif link.source_resource_type == "project" and link.source_resource_id:
            source = await session.scalar(
                select(PortfolioProject)
                .where(PortfolioProject.id == link.source_resource_id)
                .options(selectinload(PortfolioProject.localizations))
            )
        elif link.source_resource_type == "certificate" and link.source_resource_id:
            source = await session.get(Certificate, link.source_resource_id)
        elif link.source_resource_type == "education" and link.source_resource_id:
            source = await session.get(EducationEntry, link.source_resource_id)
        if source is None:
            continue
        label = "Manuelles Training"
        years = None
        if isinstance(source, WorkExperience):
            label = source.company
            years = max(0.0, ((source.end_date or datetime.now(UTC).date()) - source.start_date).days / 365.25)
            role_context = " ".join(
                value for value in (
                    *(localization.title for localization in source.localizations),
                    getattr(source, "role", None),
                )
                if value
            )
        elif isinstance(source, PortfolioProject): label = source.canonical_name
        elif isinstance(source, Certificate): label = source.official_name
        elif isinstance(source, EducationEntry): label = source.institution
        if isinstance(source, PortfolioProject):
            role_context = " ".join(
                value for value in (source.role, source.canonical_name, *source.technologies)
                if value
            )
        elif not isinstance(source, WorkExperience):
            role_context = ""
        content = {
            "skill": link.skill.canonical_name,
            "source_type": link.source_resource_type,
            "source_context": role_context,
        }
        if years is not None: content["years_experience"] = round(years, 2)
        context_text = f"Rollen- und Domänenkontext: {role_context}" if role_context else ""
        result.append(EvidenceInput(
            source_name=f"profile:{profile_id}:skill-evidence:{link.id}", source_type="manual",
            source_content=json.dumps(content, ensure_ascii=False, sort_keys=True),
            label=f"{link.skill.canonical_name} · {label}",
            evidence_text="\n".join(value for value in (f"Skill: {link.skill.canonical_name}", f"Quelle: {label}", context_text) if value),
            experience_context={"experience": "professional", "project": "project", "education": "education", "certificate": "training"}[link.source_resource_type],
            keywords=[link.skill.canonical_name, *link.skill.aliases, *role_context.split()],
        ))
    return result


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


def _role_context_terms(requirement: str) -> set[str]:
    """Return role/domain anchors that generic experience must not replace."""
    matches = re.findall(
        r"\b(?:als|as)\s+([\w][\w -]{1,50})",
        requirement,
        re.IGNORECASE,
    )
    anchors: set[str] = set()
    for match in matches:
        phrase = re.split(r",|\b(?:idealerweise|preferably|with|in)\b", match, maxsplit=1, flags=re.IGNORECASE)[0]
        anchors.update(_terms(phrase, []))
    return anchors


def _required_domain_terms(requirement: str) -> set[str]:
    normalized = requirement.casefold()
    groups = (
        ("financial services", {"financial", "finance", "banking", "fintech", "trading", "hedge", "fund"}),
        ("cloud", {"cloud", "aws", "azure", "gcp", "cloud-native", "cloudnative"}),
    )
    required: set[str] = set()
    for marker, terms in groups:
        if marker in normalized or any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in terms):
            required.update(terms)
    return required


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

AGENTIC_CODING_REQUIREMENT_PATTERN = re.compile(
    r"\b(?:agentic|agent[- ]?based|ai[- ]?assisted)\s+coding\s+tools?\b",
    re.IGNORECASE,
)
DAILY_USE_PATTERN = re.compile(
    r"\b(?:daily|every day|täglich|taeglich)\b", re.IGNORECASE
)
AGENTIC_CODING_TOOL_PATTERN = re.compile(
    r"\b(?:codex|claude code|cursor|copilot|aider|coding agent)\b",
    re.IGNORECASE,
)


def _documents_daily_agentic_coding_use(stored: StoredEvidence) -> bool:
    """Check a factual use claim, not a generic AI-tool skill label."""
    text = f"{stored.item.label}\n{stored.item.evidence_text}"
    return bool(DAILY_USE_PATTERN.search(text) and AGENTIC_CODING_TOOL_PATTERN.search(text))


def _evaluate(
    requirement_id: str,
    requirement: str,
    requirement_terms: set[str],
    evidence: list[StoredEvidence],
    *,
    category: str = "",
    keyword_terms: set[str] | None = None,
    normalized_value: str | None = None,
    semantic_candidate_ids: set[str] | None = None,
) -> RequirementMatchResponse:
    keyword_terms = keyword_terms or set()
    minimum_years = _minimum_years(requirement, normalized_value)
    if minimum_years is not None:
        return _evaluate_seniority(
            requirement_id,
            requirement,
            minimum_years,
            evidence,
        )
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
        elif semantic_candidate_ids and stored.evidence_id in semantic_candidate_ids:
            # Retrieval only establishes relevance; with no lexical proof this
            # candidate can never become a direct/strong match.
            scored.append((0.0, stored, set()))
    scored.sort(
        key=lambda pair: (pair[0] * _evidence_weight(pair[1]), _evidence_weight(pair[1])),
        reverse=True,
    )

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
    has_semantic_candidate = any(not overlap for _, _, overlap in scored)
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
        and not has_semantic_candidate
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
    if AGENTIC_CODING_REQUIREMENT_PATTERN.search(requirement):
        daily_use_evidence = [
            stored for stored in relevant if _documents_daily_agentic_coding_use(stored)
        ]
        if daily_use_evidence:
            cited = [
                MatchEvidence(
                    evidence_id=stored.evidence_id,
                    source_name=stored.item.source_name,
                    label=stored.item.label,
                    evidence_text=stored.item.evidence_text,
                    experience_context=stored.item.experience_context,
                )
                for stored in daily_use_evidence[:3]
            ]
            return RequirementMatchResponse(
                requirement_id=requirement_id,
                requirement=requirement,
                match_level="strong_match",
                evidence=cited,
                explanation="Documented evidence explicitly confirms daily use of agentic coding tools.",
                recommended_action="Cite the concrete daily-use example and the tool names factually.",
                confidence=0.9,
            )
    if has_semantic_candidate and aggregate_score == 0:
        cited = [
            MatchEvidence(
                evidence_id=stored.evidence_id,
                source_name=stored.item.source_name,
                label=stored.item.label,
                evidence_text=stored.item.evidence_text,
                experience_context=stored.item.experience_context,
            )
            for stored in relevant[:3]
        ]
        return RequirementMatchResponse(
            requirement_id=requirement_id,
            requirement=requirement,
            match_level="transferable",
            evidence=cited,
            explanation="Semantisch verwandte Evidence wurde gefunden, belegt die konkrete Anforderung aber nicht explizit.",
            recommended_action="Nur als übertragbare Erfahrung darstellen; die konkrete Kompetenz separat nachweisen.",
            confidence=0.45,
        )
    has_professional = any(
        stored.item.experience_context == "professional" for stored in relevant
    )
    role_context_terms = _role_context_terms(requirement)
    has_role_context = bool(
        role_context_terms
        and any(
            role_context_terms & _terms(stored.item.evidence_text, stored.item.keywords)
            for stored in relevant
        )
    ) if role_context_terms else True
    required_domain_terms = _required_domain_terms(requirement)
    has_domain_context = bool(
        required_domain_terms
        and any(
            required_domain_terms & _terms(stored.item.evidence_text, stored.item.keywords)
            for stored in relevant
        )
    ) if required_domain_terms else True
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
    elif required_domain_terms and not has_domain_context:
        if "cloud" in required_domain_terms and any(
            term in required_domain_terms for term in ("aws", "azure", "gcp")
        ):
            level = "gap"
            explanation = "Related technical evidence exists, but no documented cloud-platform evidence supports this requirement."
            action = "Add verified AWS, Azure, GCP, or equivalent cloud-platform evidence before claiming this requirement."
        else:
            level = "partial_match"
            explanation = "The technical capability is partly evidenced, but the required industry or domain context is not documented."
            action = "Cite the technical evidence separately and do not imply experience in the required industry."
    elif has_professional_alternative or (
        has_professional and aggregate_score >= 0.6 and has_role_context and has_domain_context
    ):
        level = "strong_match"
        explanation = "Documented professional evidence directly supports this requirement."
        action = "Use the cited professional evidence and keep the wording factual."
    elif role_context_terms and not has_role_context and has_professional:
        level = "partial_match"
        explanation = (
            "General professional experience is documented, but the required role "
            "or domain context is not evidenced."
        )
        action = "Cite the general experience separately; do not present it as role-specific experience."
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
        explanation = (
            "The combined profile evidence supports part, but not all, of this requirement."
        )
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
        for stored in sorted(relevant, key=_evidence_weight, reverse=True)[:3]
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
        embedding_provider = create_embedding_provider(get_settings())
        chroma_store = None
        if embedding_provider is not None:
            settings = get_settings()
            chroma_store = ChromaEvidenceStore(host=settings.chroma_host, port=settings.chroma_port, collection_name=settings.chroma_collection)
        job = await session.scalar(select(Job).where(Job.id == payload.job_id))
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        stored_requirements = (
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
        requirement_inputs = (
            [
                RequirementInput(
                    requirement=item.requirement_text,
                    category=item.category,
                    priority=item.priority,
                    keywords=item.keywords or [],
                    normalized_value=item.normalized_value,
                )
                for item in stored_requirements
            ]
            if stored_requirements
            else list(payload.requirements)
        )

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
                    source_metadata={"profile_id": str(payload.profile_id)} if payload.profile_id else None,
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
            if embedding_provider is not None and chroma_store is not None:
                text = build_evidence_embedding_text(
                    label=item.label,
                    evidence_text=item.evidence_text,
                    source_name=item.source_name,
                )
                vector = await asyncio.to_thread(embedding_provider.embed_text, text)
                await asyncio.to_thread(chroma_store.upsert, evidence_id=str(evidence_row.id), profile_id=str(payload.profile_id), embedding=vector, document=text, model=embedding_provider.model)
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
        for item in requirement_inputs:
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

            semantic_candidate_ids: set[str] = set()
            if embedding_provider is not None and chroma_store is not None and payload.profile_id:
                requirement_vector = await asyncio.to_thread(
                    embedding_provider.embed_text,
                    build_requirement_embedding_text(item.requirement),
                )
                semantic_candidates = await asyncio.to_thread(chroma_store.query, profile_id=str(payload.profile_id), embedding=requirement_vector, top_k=10)
                semantic_candidate_ids = {str(candidate.evidence_id) for candidate in semantic_candidates}

            result = _evaluate(
                str(requirement.id),
                item.requirement,
                _terms(item.requirement, item.keywords),
                stored_evidence,
                category=item.category,
                keyword_terms=_terms("", item.keywords),
                normalized_value=item.normalized_value,
                semantic_candidate_ids=semantic_candidate_ids,
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


async def list_matching_jobs(profile_id=None, *, include_archived: bool = False) -> list[dict]:
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
        applications_by_job = {}
        if profile_id is not None:
            applications_by_job = {
                application.job_id: application
                for application in (
                    await session.scalars(
                        select(Application).where(Application.profile_id == profile_id)
                    )
                ).all()
            }
        jobs_statement = select(Job, Company).outerjoin(
            Company, Company.id == Job.company_id
        )
        if not include_archived:
            jobs_statement = jobs_statement.where(Job.archived_at.is_(None))
        rows = (
            await session.execute(
                jobs_statement.order_by(Job.imported_at.desc())
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
                "application_status": (
                    applications_by_job[job.id].status
                    if job.id in applications_by_job
                    else "open"
                ),
                "application_status_changed_at": (
                    applications_by_job[job.id].status_changed_at
                    if job.id in applications_by_job
                    else job.imported_at
                ),
                "published_at": job.published_at,
                "deadline": job.deadline,
                "imported_at": job.imported_at,
                "archived_at": job.archived_at,
                "archive_reason": job.archive_reason,
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
        activities = (
            await session.scalars(
                select(JobActivity)
                .where(JobActivity.job_id == job.id)
                .order_by(JobActivity.position)
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
            "archived_at": job.archived_at,
            "archive_reason": job.archive_reason,
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
            "activities": [
                {
                    "id": str(activity.id),
                    "activity": activity.activity_text,
                    "category": activity.category,
                    "keywords": activity.keywords or [],
                    "confidence": activity.confidence,
                }
                for activity in activities
            ],
            "content": job.normalized_content,
            "content_html": render_safe_markdown(job.normalized_content),
        }


async def get_original_job_html(job_id) -> dict:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError("Database is not configured.", code="database_not_configured", status_code=503)
    async with session_factory() as session:
        job = await session.scalar(select(Job).where(Job.id == job_id))
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        if job.source_type not in {"html", "url"}:
            raise ApplicationError("Original HTML is only available for HTML and URL imports.", code="original_html_not_available", status_code=404)
        return {"source_type": job.source_type, "raw_content": job.raw_content or ""}


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


async def archive_matching_job(job_id, reason: str | None = None) -> dict:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Job archiving requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        job.archived_at = func.now()
        job.archive_reason = (reason or "").strip() or None
        await session.commit()
    return await get_matching_job(job_id)


async def restore_matching_job(job_id) -> dict:
    session_factory = get_session_factory()
    if session_factory is None:
        raise ApplicationError(
            "Job restoration requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    async with session_factory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            raise ApplicationError("Job not found.", code="job_not_found", status_code=404)
        job.archived_at = None
        job.archive_reason = None
        await session.commit()
    return await get_matching_job(job_id)


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
    lexical_overlap = len(desired_terms & actual_terms) / len(desired_terms)
    desired_concepts = {
        name
        for name, markers in TARGET_FIT_CONCEPTS.items()
        if any(marker in _normalized_target_text(desired) for marker in markers)
    }
    actual_concepts = {
        name
        for name, markers in TARGET_FIT_CONCEPTS.items()
        if any(marker in _normalized_target_text(actual) for marker in markers)
    }
    concept_overlap = (
        len(desired_concepts & actual_concepts) / len(desired_concepts)
        if desired_concepts
        else 0.0
    )
    return max(lexical_overlap, concept_overlap)


def _preference_criterion(
    *,
    key: str,
    label: str,
    desired: list[str],
    actual: str | None,
    weight: int,
    comparison_actual: str | None = None,
) -> dict:
    desired = [value for value in desired if value and value.strip()]
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
    best = max(_target_overlap(value, comparison_actual or actual) for value in desired)
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


def _target_role_preferences(profile: Profile) -> list[dict]:
    structured = getattr(profile, "target_role_preferences", None) or []
    if structured:
        return [item for item in structured if isinstance(item, dict) and item.get("role")]
    return [{"role": role, "level": None, "priority": index + 1}
            for index, role in enumerate(profile.target_roles or [])]


def _target_role_seniority_criterion(job_seniority: dict | None, preferences: list[dict], role_actual: str | None) -> dict:
    matched = [item for item in preferences if item.get("level") and _target_overlap(item.get("role", ""), role_actual)]
    if not matched:
        return _seniority_criterion(job_seniority, 0.0)
    desired = max(matched, key=lambda item: _target_overlap(item["role"], role_actual))
    desired_level = str(desired["level"]).casefold()
    actual_level = str((job_seniority or {}).get("level") or "unknown").casefold()
    if actual_level not in TARGET_LEVEL_RANK:
        return {"key": "seniority", "label": "Seniorität", "status": "unknown", "desired": [desired["level"]], "actual": None, "score": None, "weight": 20, "explanation": "Die Stellenanzeige enthält kein eindeutig erkanntes Level."}
    delta = TARGET_LEVEL_RANK[actual_level] - TARGET_LEVEL_RANK.get(desired_level, 2)
    score = 1.0 if delta == 0 else 0.8 if delta > 0 else 0.6 if delta == -1 else 0.0
    status = "match" if score == 1 else "partial" if score else "mismatch"
    return {"key": "seniority", "label": "Seniorität", "status": status, "desired": [desired["level"]], "actual": actual_level.title(), "score": score, "weight": 20, "explanation": "Das erkannte Stellenlevel passt zum Ziellevel." if status == "match" else "Das Stellenlevel liegt leicht über dem Ziellevel." if delta > 0 else "Das Stellenlevel weicht vom Ziellevel ab."}


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
    if normalized in {"angestellte r", "angestellter", "employee"}:
        return None
    return normalized or None


def _contract_duration_months(value: str | None) -> int | None:
    """Convert a stated fixed-term duration to whole months when possible."""
    if not value:
        return None
    match = re.search(
        r"\b(\d+(?:[.,]\d+)?)\s*(years?|months?|jahre?|monate?)\b",
        value,
        re.IGNORECASE,
    )
    if not match:
        return None
    amount = float(match.group(1).replace(",", "."))
    unit = match.group(2).casefold()
    return round(amount * 12) if unit.startswith(("year", "jahr")) else round(amount)


def _employment_type_criterion(job: Job, profile: Profile) -> dict:
    preferences = set(profile.preferred_employment_types or [])
    minimum_months = getattr(profile, "minimum_contract_duration_months", None)
    contract_term = getattr(job, "contract_term", None)
    if not preferences:
        return {
            "key": "employment_type", "label": "Beschäftigungsarten", "status": "unknown",
            "desired": [], "actual": None, "score": None, "weight": 30,
            "explanation": "Im Profil sind keine Beschäftigungsarten hinterlegt.",
        }
    actual = (
        "temporary" if contract_term and re.search(r"\b(?:befristet|temporary|fixed[- ]term)\b", contract_term, re.IGNORECASE)
        else "permanent" if contract_term and re.search(r"\b(?:unbefristet|permanent)\b", contract_term, re.IGNORECASE)
        else _canonical_employment_type(job.employment_type)
    )
    desired = list(preferences)
    if actual is None:
        return _preference_criterion(
            key="employment_type", label="Beschäftigungsarten", desired=desired, actual=None, weight=30
        )
    months = _contract_duration_months(contract_term)
    permanent_match = actual == "permanent" and "permanent" in preferences
    temporary_match = (
        actual == "temporary" and "temporary" in preferences
        and months is not None
        and minimum_months is not None
        and months >= minimum_months
    )
    if permanent_match or temporary_match:
        status, score = "match", 1.0
        explanation = "Die Vertragslaufzeit entspricht einer hinterlegten Präferenz."
    elif actual == "temporary" and "temporary" in preferences and months is None:
        status, score = "partial", 0.6
        explanation = "Die Stelle ist befristet, aber die Laufzeit ist nicht eindeutig angegeben."
    else:
        status, score = "mismatch", 0.0
        explanation = "Die Vertragslaufzeit entspricht keiner hinterlegten Präferenz."
    return {
        "key": "employment_type", "label": "Beschäftigungsarten", "status": status,
        "desired": desired, "actual": contract_term or job.employment_type,
        "score": score, "weight": 30,
        "explanation": explanation,
    }


def _profile_seniority_years(experiences: list[WorkExperience]) -> float:
    if not experiences:
        return 0.0
    return max(
        0.0,
        max(
            ((entry.end_date or datetime.now(UTC).date()) - entry.start_date).days / 365.25
            for entry in experiences
        ),
    )


def _profile_seniority_level(years: float) -> str:
    if years >= 7:
        return "senior"
    if years >= 3:
        return "professional"
    if years > 0:
        return "junior"
    return "entry"


def _seniority_criterion(seniority: dict | None, profile_years: float) -> dict:
    if not isinstance(seniority, dict) or seniority.get("level") not in SENIORITY_RANK:
        return {
            "key": "seniority", "label": "Seniorität", "status": "unknown",
            "desired": [], "actual": None, "score": None, "weight": 15,
            "explanation": "Die Stellenanzeige enthält keine belastbare Senioritätsanforderung.",
        }
    return {
        "key": "seniority", "label": "Seniority", "status": "unknown",
        "desired": [str(seniority["level"])], "actual": None,
            "score": None, "weight": 20,
        "explanation": "Skill-specific professional evidence is required; total employment years are not used.",
    }
    desired_level = seniority["level"]
    actual_level = _profile_seniority_level(profile_years)
    required_years = seniority.get("years_required")
    meets_level = SENIORITY_RANK[actual_level] >= SENIORITY_RANK[desired_level]
    meets_years = required_years is None or profile_years >= float(required_years)
    score = 1.0 if meets_level and meets_years else 0.6 if meets_level else 0.0
    status = "match" if score == 1 else "partial" if score else "mismatch"
    required_text = (
        f"; mindestens {float(required_years):g} Jahre" if required_years is not None else ""
    )
    return {
        "key": "seniority", "label": "Seniorität", "status": status,
        "desired": [f"{desired_level}{required_text}"],
        "actual": f"{actual_level} ({profile_years:.1f} Jahre dokumentierte Berufserfahrung)",
        "score": score, "weight": 20,
        "explanation": "Die dokumentierte Berufserfahrung erfüllt die Senioritätsanforderung."
        if score == 1 else "Die Senioritätsanforderung ist nur teilweise belegt."
        if score else "Die dokumentierte Berufserfahrung liegt unter der Senioritätsanforderung.",
    }


def _evaluate_target_fit(
    job: Job,
    company: Company | None,
    profile: Profile,
    activities: list[JobActivity] | None = None,
    profile_seniority_years: float = 0.0,
) -> dict:
    activity_text = " ".join(
        item.activity_text for item in activities or [] if item.activity_text
    )
    # Job imports occasionally classify a growth/benefits section as an
    # activity.  Keep that text visible in the result, but use the complete
    # advert as an additional comparison source so the target fit is not
    # determined by that extraction artefact alone.
    target_fit_context = " ".join(
        value
        for value in (job.title, activity_text, getattr(job, "normalized_content", ""))
        if value
    )
    career_goal = getattr(profile, "career_goal", "") or ""
    activity_goals = [career_goal.strip()] if career_goal.strip() else []
    job_seniority = (getattr(job, "extracted_json", None) or {}).get("seniority")
    role_preferences = _target_role_preferences(profile)
    role_desired = [item["role"] for item in role_preferences]
    criteria = [
        _preference_criterion(
            key="role",
            label="Zielrolle",
            desired=role_desired,
            actual=(getattr(job, "extracted_json", None) or {}).get("role") or job.title,
            # Job titles are noisy and vary strongly between employers. The
            # actual responsibilities and qualification matching are more
            # reliable signals for the target fit.
            weight=10,
        ),
        _preference_criterion(
            key="activities",
            label="Tätigkeits-Fit",
            desired=activity_goals,
            actual=activity_text or None,
            weight=35,
            # Imports can shorten an activity to its bold lead-in (for
            # example "Automate Benchmarks"). The title supplies the domain
            # context for comparison without changing the displayed list.
            comparison_actual=target_fit_context or None,
        ),
            _target_role_seniority_criterion(job_seniority, role_preferences, (getattr(job, "extracted_json", None) or {}).get("role") or job.title),
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
            weight=15,
        ),
        _preference_criterion(
            key="work_model",
            label="Arbeitsmodell",
            desired=profile.preferred_work_models or [],
            actual=_canonical_work_model(job.work_model),
            weight=10,
        ),
        _employment_type_criterion(job, profile),
    ]
    if criteria[0]["desired"]:
        actual_role = (getattr(job, "extracted_json", None) or {}).get("role") or job.title
        ranked_roles = sorted(
            ((item, _target_overlap(item["role"], actual_role)) for item in role_preferences),
            key=lambda pair: pair[1], reverse=True,
        )
        if ranked_roles and ranked_roles[0][1] > 0:
            selected_priority = max(1, min(5, int(ranked_roles[0][0].get("priority", 1))))
            criteria[0]["priority"] = selected_priority
            criteria[0]["weight"] = 10 * (6 - selected_priority) / 5
            criteria[0]["explanation"] += f" Priorität {selected_priority} wurde als Gewichtung berücksichtigt."
        criteria[0]["desired"] = [
            f"{item['role']} · Priorität {item.get('priority', 1)}"
            for item in role_preferences
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
        activities = (
            await session.scalars(
                select(JobActivity)
                .where(JobActivity.job_id == job_id)
                .order_by(JobActivity.position)
            )
        ).all()
        experiences = (
            await session.scalars(
                select(WorkExperience).where(WorkExperience.profile_id == profile_id)
            )
        ).all()
        return _evaluate_target_fit(
            row[0], row[1], profile, list(activities), _profile_seniority_years(list(experiences))
        )


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
        activities = (
            await session.scalars(
                select(JobActivity)
                .where(JobActivity.job_id == job.id)
                .order_by(JobActivity.position)
            )
        ).all()
        target_fit = _evaluate_target_fit(job, company, profile, list(activities))
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
