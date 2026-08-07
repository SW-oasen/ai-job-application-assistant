"""Deterministic extraction of job seniority signals."""

import re
from typing import Literal, TypedDict

SeniorityLevel = Literal["entry", "junior", "professional", "senior", "lead"]


class JobSeniority(TypedDict):
    level: SeniorityLevel
    confidence: float
    years_required: float | None
    signals: list[str]


YEAR_PATTERN = re.compile(
    r"\b(?:mindestens|mind\.?|at least|minimum|over|mehr als)?\s*"
    r"(?P<years>\d+(?:[.,]\d+)?)(?:\s*(?:bis|-|–)\s*\d+(?:[.,]\d+)?)?\s*(?:\+|plus)?\s*"
    r"(?:jahr(?:e|en)?|years?)\s*(?:of\s+)?"
    r"(?:berufs?|professional)?\s*(?:erfahrung|experience)\b",
    re.IGNORECASE,
)
LEVEL_PATTERNS: tuple[tuple[SeniorityLevel, re.Pattern[str]], ...] = (
    (
        "senior",
        re.compile(r"\barchitectural\s+leadership\b", re.IGNORECASE),
    ),
    (
        "lead",
        re.compile(
            r"\b(?:teamlead|team lead|lead(?!\s+times)|leiter(?:in)?|head of)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "senior",
        re.compile(r"\b(?:senior|mehrj[aä]hrig)\b", re.IGNORECASE),
    ),
    (
        "junior",
        re.compile(
            r"\b(?:junior|berufseinsteiger|erste\s+(?:berufs|praktische\s+)erfahrungen?)\b",
            re.IGNORECASE,
        ),
    ),
)
PROFESSIONAL_SIGNALS = re.compile(
    r"\b(?:eigenverantwortlich|selbstständig|independent(?:ly)?|architecture|architektur|"
    r"konzeption|verantwortung(?:sbereich)?|ownership)\b",
    re.IGNORECASE,
)


def extract_job_seniority(content: str) -> JobSeniority | None:
    """Return explicit seniority evidence, without guessing from job titles alone."""
    years = [float(match.group("years").replace(",", ".")) for match in YEAR_PATTERN.finditer(content)]
    signal_lines = [line.strip() for line in content.splitlines() if line.strip()]

    for level, pattern in LEVEL_PATTERNS:
        matches = [line for line in signal_lines if pattern.search(line)]
        if matches:
            return {
                "level": level,
                "confidence": 0.95 if level in {"lead", "senior", "junior"} else 0.8,
                "years_required": max(years) if years else None,
                "signals": matches[:5],
            }

    professional_matches = [line for line in signal_lines if PROFESSIONAL_SIGNALS.search(line)]
    if years or professional_matches:
        return {
            "level": "professional",
            "confidence": 0.92 if years else 0.7,
            "years_required": max(years) if years else None,
            "signals": (
                professional_matches
                or [line for line in signal_lines if YEAR_PATTERN.search(line)]
            )[:5],
        }
    return None


def seniority_requirement(seniority: JobSeniority | None) -> dict | None:
    """Represent a numeric seniority demand in the existing requirement pipeline."""
    if seniority is None or seniority["years_required"] is None:
        return None
    years = seniority["years_required"]
    return {
        "requirement": f"Mindestens {years:g} Jahre Berufserfahrung",
        "category": "experience",
        "priority": "must",
        "keywords": ["Berufserfahrung", "years_experience"],
        "normalized_value": f"min_years:{years:g}",
        "confidence": seniority["confidence"],
        "evidence": "; ".join(seniority["signals"]),
    }


def ensure_seniority_requirement(
    requirements: list[dict], seniority: JobSeniority | None
) -> list[dict]:
    generated = seniority_requirement(seniority)
    if generated is None:
        return requirements
    if any(item.get("category") == "experience" for item in requirements):
        return requirements
    return [*requirements, generated]
