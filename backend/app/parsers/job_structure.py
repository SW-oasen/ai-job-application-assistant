import re
from dataclasses import dataclass

HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
# Some ads use a bold standalone phrase instead of a markdown heading, e.g.
# "**Deine Aufgaben** Produkte entwickeln:" right before the list.
BOLD_HEADING_PATTERN = re.compile(r"^\s*\*\*(?P<heading>[^*]{2,60})\*\*\s*.{0,80}$")
LIST_ITEM_PATTERN = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.+?)\s*$")
ACTIVITY_HEADINGS = re.compile(
    r"\b("
    r"aufgaben|tätigkeiten|verantwortung|verantwortlichkeiten|mission|"
    r"(?:deine|ihre) rolle|rolle|ihr aufgabengebiet|das erwartet dich|"
    r"responsibilities|your role|what you(?:'|’)ll do|what you(?:'|’)ll be doing|"
    r"the role|in this (?:position|role)|key responsibilities|day[- ]to[- ]day|what you need to make a difference"
    r")\b",
    re.IGNORECASE,
)
ACTIVITY_CONTEXT_HEADINGS = re.compile(
    r"(?:\bas part of\b.{0,120}\byou will\b|\byou will\b|\byou are responsible for\b|"
    r"\bdeine aufgaben\b|\?bernehmen sie\b|\bdu wirst\b|\bsie werden\b)",
    re.IGNORECASE,
)
INLINE_ACTIVITY_CONTEXT = re.compile(
    r"\b(?:zu\s+(?:ihren|deinen)\s+aufgaben\s+(?:z[aä]hlen|geh[oö]ren)|"
    r"sie\s+sind\s+verantwortlich\s+f[uü]r)\b",
    re.IGNORECASE,
)
INLINE_REQUIREMENT_CONTEXT = re.compile(
    r"^\s*(?:sie\s+(?:verf[uü]gen|haben|besitzen)|weiterhin\s+verf[uü]gen)\b",
    re.IGNORECASE,
)
REQUIREMENT_HEADINGS = re.compile(
    r"\b("
    r"anforderungen|qualifikation(?:en)?|kompetenz\w*|profil|das bringst du(?:\s+.{0,80})?\s+mit|"
    r"das zeichnet dich aus|ihr profil|"
    r"requirements|qualifications|what you bring|your profile|"
    r"skills?\s*[+&]\s*education|skills?|education|"
    r"what we(?:'|’)re looking for|what you need to be successful|about you|who you are|"
    r"what you(?:'|’)ll bring|must[- ]haves?|skills (?:and|&) experience"
    r")\b",
    re.IGNORECASE,
)
# Some portals put responsibilities and candidate qualifications in one list
# without a heading between them. A blank line is only a potential boundary;
# it becomes meaningful when the next item unmistakably describes a candidate
# qualification. This deliberately excludes generic verbs such as "build" or
# "use", which commonly appear in responsibility lists.
IMPLICIT_REQUIREMENT_START = re.compile(
    r"^\s*(?:"
    r"(?:bachelor'?s|master'?s|ph\.?d\.?|university)\s+(?:degree|education)|"
    r"(?:abgeschlossen(?:es|e)?\s+(?:studium|ausbildung)|studium)\b|"
    r"(?:proficiency|familiarity|basic understanding|demonstrated hands-on experience|"
    r"exposure to|ability to|experience with)\b"
    r")",
    re.IGNORECASE,
)
BENEFIT_HEADINGS = re.compile(
    r"\b(benefits?|vorteile|wir bieten|was wir bieten|unser angebot|"
    r"das bieten wir|deine benefits|ihre benefits|perks|fringe benefits|"
    r"what we offer|our benefits|what you get|employee benefits)\b",
    re.IGNORECASE,
)
OPTIONAL_MARKERS = re.compile(
    r"\b(von vorteil|wünschenswert|idealerweise|nice to have|preferred|plus)\b",
    re.IGNORECASE,
)
OPTIONAL_ITEM_PREFIX = re.compile(
    r"^\s*(?:von vorteil|wÃ¼nschenswert|idealerweise|nice to have|preferred|plus)\b",
    re.IGNORECASE,
)
MUST_MARKERS = re.compile(
    r"\b(muss|zwingend|notwendig|erforderlich|required|must|mindestens)\b",
    re.IGNORECASE,
)
SENIORITY_PATTERN = re.compile(
    r"(?P<qualifier>mindestens|min\.|at\s+least|minimum|mehr\s+als|mehr\s+als|over)?\s*"
r"(?P<years>\d+(?:[.,]\d+)?(?:\s*(?:bis|-|–)\s*\d+(?:[.,]\d+)?)?|ein|eine|einem|einen|zwei|drei|vier|fünf|fuenf|"
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
    benefits: list[dict]


def _clean_item(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \t:;,.")


def _clean_heading(value: str) -> str:
    value = _clean_item(re.sub(r"(?:\*\*|__)", "", value))
    # Browser captures can contain UTF-8 decoded once too few (e.g. ``fÃ¼r``).
    # Repair the heading before applying the language-specific section rules.
    if any(marker in value for marker in ("Ã", "Â", "â")):
        try:
            repaired = value.encode("latin1").decode("utf-8")
            if repaired:
                value = repaired
        except UnicodeError:
            pass
    return value


def _join_list_continuations(content: str) -> list[str]:
    """Join indented Markdown continuation lines with their list item.

    A common export format renders one requirement across two lines, with the
    second line indented by two spaces. Treating it as a non-list line silently
    truncated the requirement and could create a false matching gap.
    """
    lines: list[str] = []
    for raw_line in content.splitlines():
        indentation = len(raw_line) - len(raw_line.lstrip(" "))
        if (
            0 < indentation <= 3
            and raw_line.strip()
            and not LIST_ITEM_PATTERN.match(raw_line.strip())
            and lines
            and LIST_ITEM_PATTERN.match(lines[-1])
        ):
            lines[-1] = f"{lines[-1].rstrip()} {raw_line.strip()}"
        else:
            lines.append(raw_line)
    return lines


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
    # An optional qualifier inside a larger requirement must not downgrade
    # the whole requirement. For example, AWS may be desirable while cloud
    # experience itself remains a normal qualification. Optional priority is
    # reserved for explicitly optional headings or items beginning with the
    # optional marker.
    if OPTIONAL_MARKERS.search(heading) or OPTIONAL_ITEM_PREFIX.search(value):
        return "nice_to_have"
    if MUST_MARKERS.search(f"{heading} {value}"):
        return "must"
    return "should"


def _seniority_requirement(value: str, heading: str) -> dict | None:
    match = SENIORITY_PATTERN.search(value)
    if match is None:
        return None
    raw_years = match.group("years").casefold()
    range_match = re.fullmatch(r"(?P<minimum>\d+(?:[.,]\d+)?)\s*(?:bis|-|–)\s*(?P<maximum>\d+(?:[.,]\d+)?)", raw_years)
    if range_match:
        minimum = float(range_match.group("minimum").replace(",", "."))
        years_text = f"{minimum:g}"
        normalized_value = f"min_years:{minimum:g}"
    else:
        years = NUMBER_WORDS.get(raw_years)
        if years is None:
            years = float(raw_years.replace(",", "."))
        years_text = f"{years:g}"
        normalized_value = f"min_years:{years:g}"
    return {
        "requirement": f"Mindestens {years_text} Jahre Berufserfahrung",
        "category": "experience",
        "priority": _priority(value, heading),
        "keywords": ["Berufserfahrung", "years_experience"],
        "normalized_value": normalized_value,
        "confidence": 0.95,
        "evidence": value,
    }


def extract_job_structure(content: str) -> ExtractedJobStructure:
    activities: list[dict] = []
    requirements: list[dict] = []
    benefits: list[dict] = []
    section: str | None = None
    heading = ""
    seen: dict[str, set[str]] = {"activity": set(), "requirement": set(), "benefit": set()}
    blank_line_after_list = False

    for raw_line in _join_list_continuations(content):
        # Some HTML-to-Markdown converters render section headings and list
        # items inside blockquotes (e.g. ``> ## Qualifikation``).
        raw_line = re.sub(r"^\s*>\s?", "", raw_line)
        if not raw_line.strip():
            blank_line_after_list = True
            continue
        heading_match = HEADING_PATTERN.match(raw_line)
        if heading_match:
            heading = _clean_heading(heading_match.group(1))
            # Benefits win for combined headings such as "Aufgaben & Benefits".
            if BENEFIT_HEADINGS.search(heading):
                section = "benefit"
            elif ACTIVITY_HEADINGS.search(heading) or ACTIVITY_CONTEXT_HEADINGS.search(heading):
                section = "activity"
            elif REQUIREMENT_HEADINGS.search(heading):
                section = "requirement"
            else:
                section = None
            blank_line_after_list = False
            continue
        bold_heading_match = BOLD_HEADING_PATTERN.match(raw_line)
        if bold_heading_match:
            candidate_heading = _clean_heading(bold_heading_match.group("heading"))
            if BENEFIT_HEADINGS.search(candidate_heading):
                heading = candidate_heading
                section = "benefit"
                continue
            if ACTIVITY_HEADINGS.search(candidate_heading) or ACTIVITY_CONTEXT_HEADINGS.search(candidate_heading):
                heading = candidate_heading
                section = "activity"
                continue
            if REQUIREMENT_HEADINGS.search(candidate_heading):
                heading = candidate_heading
                section = "requirement"
                continue
            # A new bold standalone heading must not inherit the previous
            # section (e.g. "Meine Kompetenzen" after an activity section).
            section = None
            heading = candidate_heading
        if section is None:
            if INLINE_ACTIVITY_CONTEXT.search(raw_line):
                section = "activity"
                heading = _clean_item(raw_line)
                continue
            if INLINE_REQUIREMENT_CONTEXT.search(raw_line):
                section = "requirement"
                heading = _clean_item(raw_line)
            elif (item_match := LIST_ITEM_PATTERN.match(raw_line)) and INLINE_REQUIREMENT_CONTEXT.search(item_match.group(1)):
                section = "requirement"
                heading = ""
            else:
                continue
        elif INLINE_REQUIREMENT_CONTEXT.search(raw_line):
            section = "requirement"
            heading = _clean_item(raw_line)
            continue
        item_match = LIST_ITEM_PATTERN.match(raw_line)
        if not item_match:
            continue
        text = _clean_item(item_match.group(1))
        if (
            section == "activity"
            and blank_line_after_list
            and IMPLICIT_REQUIREMENT_START.search(text)
        ):
            # The qualification block has no own heading. Do not treat the
            # whitespace alone as a section change: it is merely supporting
            # evidence for the explicit qualification signal in this item.
            section = "requirement"
            heading = ""
        blank_line_after_list = False
        normalized = text.casefold()
        if len(text) < 8 or normalized in seen[section]:
            continue
        seen[section].add(normalized)
        if section == "benefit":
            benefits.append(
                {
                    "benefit": text,
                    "evidence": text,
                    "confidence": 0.85,
                }
            )
        elif section == "activity":
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
        benefits=benefits[:100],
    )
