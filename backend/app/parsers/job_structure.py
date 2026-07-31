import re
from dataclasses import dataclass

HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$")
ACTIVITY_HEADINGS = re.compile(
    r"\b("
    r"aufgaben|tätigkeiten|verantwortung|verantwortlichkeiten|"
    r"deine rolle|ihr aufgabengebiet|das erwartet dich|"
    r"responsibilities|your role|what you(?:'|’)ll do|the role"
    r")\b",
    re.IGNORECASE,
)
REQUIREMENT_HEADINGS = re.compile(
    r"\b("
    r"anforderungen|qualifikationen|profil|das bringst du mit|"
    r"das zeichnet dich aus|ihr profil|"
    r"requirements|qualifications|what you bring|your profile|"
    r"what we(?:'|’)re looking for"
    r")\b",
    re.IGNORECASE,
)
OPTIONAL_MARKERS = re.compile(
    r"\b(von vorteil|wünschenswert|idealerweise|nice to have|preferred|plus)\b",
    re.IGNORECASE,
)
MUST_MARKERS = re.compile(
    r"\b(muss|zwingend|erforderlich|required|must|mindestens)\b",
    re.IGNORECASE,
)
SENIORITY_PATTERN = re.compile(
    r"(?P<qualifier>mindestens|min\.|at\s+least|minimum|mehr\s+als|mehr\s+als|over)?\s*"
    r"(?P<years>\d+(?:[.,]\d+)?|ein|eine|einem|einen|zwei|drei|vier|fünf|fuenf|"
    r"sechs|sieben|acht|neun|zehn|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
    r"(?:jahr(?:e|en)?|years?)\s*(?:of\s+)?"
    r"(?:berufs?\s*|profession(?:al)?\s+)?(?:erfahrung|experience)",
    re.IGNORECASE,
)
NUMBER_WORDS = {
    "ein": 1.0,
    "eine": 1.0,
    "einem": 1.0,
    "einen": 1.0,
    "zwei": 2.0,
    "drei": 3.0,
    "vier": 4.0,
    "fünf": 5.0,
    "fuenf": 5.0,
    "sechs": 6.0,
    "sieben": 7.0,
    "acht": 8.0,
    "neun": 9.0,
    "zehn": 10.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
}
WORD_PATTERN = re.compile(r"[A-Za-zÄÖÜäöüß0-9+#.-]{3,}")
STOP_WORDS = {
    "aber",
    "auch",
    "dabei",
    "eine",
    "einem",
    "einen",
    "einer",
    "sowie",
    "über",
    "oder",
    "und",
    "with",
    "your",
    "you",
    "the",
    "and",
    "for",
}


@dataclass(frozen=True)
class ExtractedJobStructure:
    activities: list[dict]
    requirements: list[dict]


def _clean_item(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t:;,.")


def _keywords(value: str) -> list[str]:
    seen: set[str] = set()
    result = []
    for term in WORD_PATTERN.findall(value):
        normalized = term.casefold()
        if normalized in STOP_WORDS or normalized in seen:
            continue
        seen.add(normalized)
        result.append(term)
        if len(result) == 12:
            break
    return result


def _priority(value: str, heading: str) -> str:
    combined = f"{heading} {value}"
    if OPTIONAL_MARKERS.search(combined):
        return "nice_to_have"
    if MUST_MARKERS.search(combined):
        return "must"
    return "should"


def _seniority_requirement(value: str, heading: str) -> dict | None:
    match = SENIORITY_PATTERN.search(value)
    if match is None:
        return None
    raw_years = match.group("years").casefold()
    years = NUMBER_WORDS.get(raw_years)
    if years is None:
        years = float(raw_years.replace(",", "."))
    years_text = f"{years:g}"
    return {
        "requirement": f"Mindestens {years_text} Jahre Berufserfahrung",
        "category": "experience",
        "priority": _priority(value, heading),
        "keywords": ["Berufserfahrung", "years_experience"],
        "normalized_value": f"min_years:{years:g}",
        "confidence": 0.95,
        "evidence": value,
    }


def extract_job_structure(content: str) -> ExtractedJobStructure:
    activities: list[dict] = []
    requirements: list[dict] = []
    section: str | None = None
    heading = ""
    seen: dict[str, set[str]] = {"activity": set(), "requirement": set()}

    for raw_line in content.splitlines():
        heading_match = HEADING_PATTERN.match(raw_line)
        if heading_match:
            heading = _clean_item(heading_match.group(1))
            if ACTIVITY_HEADINGS.search(heading):
                section = "activity"
            elif REQUIREMENT_HEADINGS.search(heading):
                section = "requirement"
            else:
                section = None
            continue
        if section is None:
            continue
        item_match = LIST_ITEM_PATTERN.match(raw_line)
        if not item_match:
            continue
        text = _clean_item(item_match.group(1))
        normalized = text.casefold()
        if len(text) < 8 or normalized in seen[section]:
            continue
        seen[section].add(normalized)
        if section == "activity":
            activities.append(
                {
                    "activity": text,
                    "category": "responsibility",
                    "keywords": _keywords(text),
                    "confidence": 0.85,
                    "evidence": text,
                }
            )
        else:
            seniority = _seniority_requirement(text, heading)
            if seniority is not None:
                requirements.append(seniority)
                residual = SENIORITY_PATTERN.sub("", text, count=1)
                residual = re.sub(
                    r"^\s*(?:with|of|in|and|oder|mit|sowie|für)\s+",
                    "",
                    residual,
                    flags=re.IGNORECASE,
                )
                residual = _clean_item(residual)
                if len(residual) >= 3:
                    requirements.append(
                        {
                            "requirement": residual,
                            "category": "other",
                            "priority": _priority(text, heading),
                            "keywords": _keywords(residual),
                            "confidence": 0.8,
                            "evidence": text,
                        }
                    )
                continue
            requirements.append(
                {
                    "requirement": text,
                    "category": "other",
                    "priority": _priority(text, heading),
                    "keywords": _keywords(text),
                    "confidence": 0.8,
                    "evidence": text,
                }
            )

    return ExtractedJobStructure(
        activities=activities[:100],
        requirements=requirements[:200],
    )
