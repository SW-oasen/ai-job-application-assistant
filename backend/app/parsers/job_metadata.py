import re

LANGUAGE_MARKERS = {
    "de": {
        "aber",
        "als",
        "auch",
        "auf",
        "aus",
        "bei",
        "bewerbung",
        "das",
        "der",
        "die",
        "eine",
        "einem",
        "einen",
        "einer",
        "für",
        "ihre",
        "ihren",
        "ist",
        "mit",
        "oder",
        "sind",
        "stelle",
        "und",
        "unser",
        "unsere",
        "von",
        "wir",
        "werden",
        "zu",
    },
    "en": {
        "and",
        "application",
        "are",
        "as",
        "at",
        "be",
        "for",
        "from",
        "in",
        "is",
        "job",
        "of",
        "on",
        "or",
        "our",
        "position",
        "the",
        "their",
        "to",
        "we",
        "will",
        "with",
        "you",
        "your",
    },
}

COMPANY_PATTERNS = (
    re.compile(
        r"(?im)^\s*(?:>\s*)?"
        r"(?:Arbeitgeber|Unternehmen|Company|Employer)\s*:\s*(.+?)\s*$"
    ),
    re.compile(
        r"(?im)^\s*(?:>\s*)?"
        r"\[([^\]\r\n]+)\]\(https?://[^)\r\n]*/cmp/[^)\r\n]*\)\s*$"
    ),
)
PUBLISHED_TEXT_PATTERNS = (
    re.compile(
        r"(?im)^\s*(?:>\s*)?"
        r"(?:Veröffentlichungsdatum|Published)\s*:\s*(.+?)\s*$"
    ),
)


def first_metadata_match(
    content: str,
    patterns: tuple[re.Pattern, ...],
) -> str | None:
    for pattern in patterns:
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
    return None


def detect_job_language(content: str) -> str | None:
    """Detect German or English from the advertisement text."""
    words = re.findall(r"[^\W\d_]+", content.casefold(), flags=re.UNICODE)
    scores = {
        language: sum(word in markers for word in words)
        for language, markers in LANGUAGE_MARKERS.items()
    }
    if any(character in content.casefold() for character in ("ä", "ö", "ü", "ß")):
        scores["de"] += 2
    best = max(scores, key=scores.get)
    other = "en" if best == "de" else "de"
    if scores[best] < 3 or scores[best] < scores[other] * 1.5:
        return None
    return best


def _clean_line(line: str) -> str:
    value = re.sub(r"^\s*>\s?", "", line).strip()
    value = re.sub(r"^\s*[-*]\s+", "", value)
    value = re.sub(r"^:\s*", "", value)
    value = re.sub(r"^(?:!\[[^\]]*\]\([^)]+\)\s*)+", "", value).strip()
    markdown_link = re.fullmatch(r"\[([^\]]+)\]\([^)]+\)", value)
    return markdown_link.group(1).strip() if markdown_link else value


def _clean_title(title: str | None) -> str | None:
    if not title:
        return None
    value = _clean_line(title).lstrip("#").strip()
    if any(marker in value for marker in ("Ã", "Â", "â")):
        try:
            value = value.encode("latin1").decode("utf-8")
        except UnicodeError:
            pass
    value = re.sub(
        r"^Al(?=\s+(?:Engineer|Scientist|Developer|Researcher)\b)",
        "AI",
        value,
        flags=re.IGNORECASE,
    )
    # Portal badge, not part of the actual job title. Only strip it at the
    # title boundaries so a legitimate internal word remains untouched.
    value = re.sub(
        r"^(?:\[?NEU\]?\s*[-|·:]?\s+)|(?:\s*[-|·:]?\s*\[?NEU\]?)$", "", value, flags=re.IGNORECASE
    )
    return value or None


def _main_heading(content: str) -> str | None:
    match = re.search(r"(?m)^\s*#\s+(.+?)\s*$", content)
    title = _clean_title(match.group(1)) if match else None
    return None if title and title.casefold() in {"einleitung", "introduction"} else title


def _title_from_job_intro(content: str) -> str | None:
    """Extract a title from the job-opening sentence when the page starts with chrome."""
    patterns = (
        r"(?:für|fÃ¼r)\s+(?:einen\s+)?einsatz\s+als\s+(.+?)\s+"
        r"(?:\([wmd/]+\)|am\s+standort|in\s+[A-ZÄÖÜ])",
        r"(?:suchen\s+wir\s+(?:dich|sie)|we\s+are\s+looking\s+for\s+you)\s+als\s+"
        r"(.+?)\s+(?:\([wmd/]+\)|am\s+standort|in\s+[A-ZÄÖÜ])",
    )
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return _clean_title(match.group(1))
    return None


def _join_company(content: str, source_url: str | None) -> str | None:
    if not source_url or not re.search(
        r"https?://(?:www\.)?join\.com/",
        source_url,
        re.IGNORECASE,
    ):
        return None
    match = re.search(
        r"(?is)\[\s*(?:!\[[^\]]*\]\([^)]+\)\s*)*"
        r"([^\[\]\r\n]{2,200}?)\s*\]"
        r"\(https?://(?:www\.)?join\.com/companies/[^)]+\)",
        content,
    )
    return _clean_line(match.group(1)) if match else None


def _normalized_heading(line: str) -> str:
    value = _clean_line(line).lstrip("#").strip().strip("*_").strip()
    value = re.sub(r"^[^\w]+", "", value, flags=re.UNICODE)
    return value.casefold()


def _is_portal_chrome(line: str) -> bool:
    return _normalized_heading(line) in {"arbeit", "job", "stelle", "stellenangebot"}


def _section_value(content: str, headings: set[str]) -> str | None:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        heading = _normalized_heading(line)
        if heading not in headings:
            continue
        for candidate in lines[index + 1 : index + 6]:
            value = _clean_line(candidate)
            if value and not value.startswith("#") and value != "&nbsp;":
                return value
    return None


def _inline_value(content: str, headings: set[str]) -> str | None:
    heading_pattern = "|".join(
        re.escape(heading) for heading in sorted(headings, key=len, reverse=True)
    )
    match = re.search(
        rf"(?im)^[ \t]*(?:>[ \t]*)?(?:{heading_pattern})"
        rf"[ \t]*[:\-–]?[ \t]+(.+?)[ \t]*$",
        content,
    )
    return _clean_line(match.group(1)) if match else None


def _value_before_heading(content: str, headings: set[str]) -> str | None:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if _normalized_heading(line) not in headings:
            continue
        for candidate in reversed(lines[max(0, index - 3) : index]):
            value = _clean_line(candidate)
            if value and not value.startswith("#") and value != "&nbsp;":
                return value
    return None


def _map_link_location(content: str) -> str | None:
    """Extract a location label from job portals' Google Maps links."""
    match = re.search(
        r"\[([^\]\r\n]{2,150})\]\(https?://(?:www\.)?google\.[^/\s]+/maps/[^)\r\n]+\)",
        content,
        re.IGNORECASE,
    )
    return _clean_line(match.group(1)) if match else None


def _location_section_value(content: str, headings: set[str]) -> str | None:
    """Return the useful location from a portal's stacked location fields."""
    country_only = {
        "deutschland",
        "germany",
        "österreich",
        "austria",
        "schweiz",
        "switzerland",
        "usa",
        "united states",
        "vereinigte staaten",
    }
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if _normalized_heading(line) not in headings:
            continue
        values: list[str] = []
        for candidate in lines[index + 1 : index + 8]:
            value = _clean_line(candidate)
            if not value or value == "&nbsp;":
                continue
            if value.startswith("#"):
                break
            if _normalized_heading(value) not in headings:
                values.append(value)
        specific = [value for value in values if value.casefold() not in country_only]
        if specific:
            return specific[0]
        if values:
            return values[0]
    return None


def _plain_pdf_header(content: str) -> tuple[str | None, str | None]:
    lines = [_clean_line(line) for line in content.splitlines()]
    lines = [line for line in lines if line and line != "&nbsp;"][:15]
    company_pattern = re.compile(
        r"\b(?:GmbH|UG|AG|SE|KG|OHG|GbR|Ltd\.?|Limited|Inc\.?|"
        r"Corporation|Corp\.?|LLC)\b",
        re.IGNORECASE,
    )
    for index, line in enumerate(lines):
        if not company_pattern.search(line):
            continue
        title_parts = [
            part.lstrip("#").strip()
            for part in lines[:index]
            if (not part.startswith("[") and not _is_portal_chrome(part) and len(part) <= 100)
        ]
        return " ".join(title_parts).strip() or None, line
    return None, None


def _standalone_legal_company(content: str) -> str | None:
    legal_suffix = (
        r"(?:GmbH(?:\s*&\s*Co\.\s*KG)?|UG|AG|SE|KG|OHG|GbR|"
        r"Ltd\.?|Limited|Inc\.?|Corporation|Corp\.?|LLC)"
    )
    pattern = re.compile(rf"(?im)^\s*(?:>\s*)?([^\r\n]{{2,180}}\b{legal_suffix})\s*$")
    candidates = [_clean_line(match.group(1)) for match in pattern.finditer(content)]
    return candidates[-1] if candidates else None


def _legal_company_from_prose(content: str) -> str | None:
    legal_suffix = (
        r"(?:GmbH(?:\s*&\s*Co\.\s*KG)?|UG|AG|SE|KG|OHG|GbR|"
        r"Ltd\.?|Limited|Inc\.?|Corporation|Corp\.?|LLC)"
    )
    match = re.search(
        rf"(?im)^\s*(?:Die|Bei)\s+"
        rf"([A-ZÄÖÜ][^\r\n.!?]{{1,160}}?\b{legal_suffix})\b",
        content,
    )
    return _clean_line(match.group(1)) if match else None


def _compact_header_metadata(content: str) -> dict[str, str | None]:
    lines = [_clean_line(line) for line in content.splitlines()]
    lines = [line for line in lines if line and line != "&nbsp;"][:15]
    for index, line in enumerate(lines):
        parts = [part.strip() for part in re.split(r"\s+[·•|]\s+", line)]
        if len(parts) < 2 or not re.search(
            r"\((?:hybrid|remote|on-?site)\)",
            line,
            re.IGNORECASE,
        ):
            continue
        title = lines[index - 1].lstrip("#").strip() if index else None
        location = re.sub(
            r"\s*\((?:hybrid|remote|on-?site)\)\s*$",
            "",
            parts[1],
            flags=re.IGNORECASE,
        )
        work_match = re.search(
            r"\((hybrid|remote|on-?site)\)",
            line,
            re.IGNORECASE,
        )
        return {
            "title": title,
            "company": parts[0],
            "location": location.strip() or None,
            "work_model": work_match.group(1).title() if work_match else None,
        }
    return {"title": None, "company": None, "location": None, "work_model": None}


def _split_employment_contract(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    employment_parts: list[str] = []
    contract_parts: list[str] = []
    for part in re.split(r"\s*[,;|]\s*", value):
        if re.search(
            r"\b(?:unbefristet|befristet|permanent|fixed[- ]term|temporary)\b",
            part,
            re.IGNORECASE,
        ):
            contract_parts.append(part.strip())
        elif part.strip():
            employment_parts.append(part.strip())
    return (
        ", ".join(employment_parts) or None,
        ", ".join(contract_parts) or None,
    )


def _contract_term_from_role_scope(content: str) -> str | None:
    """Find a fixed duration stated in prose or a role-scope section."""
    lines = content.splitlines()
    scope_start = next(
        (
            index
            for index, line in enumerate(lines)
            if _normalized_heading(line)
            in {
                "scope of the role",
                "role scope",
                "contract details",
            }
        ),
        None,
    )
    candidates = lines[scope_start + 1 : scope_start + 6] if scope_start is not None else lines
    duration = r"\d+\s*(?:years?|months?|weeks?|jahre?|monate?|wochen?)"
    patterns = (
        re.compile(
            rf"\b(?:temporary|fixed[- ]term)\b\s*(?:\(\s*)?(?:for|für)?\s*{duration}\s*\)?",
            re.IGNORECASE,
        ),
        re.compile(
            rf"\bbefristet\b\s*(?:für|for)?\s*{duration}",
            re.IGNORECASE,
        ),
    )
    for line in candidates:
        value = re.sub(r"[*_]", "", _clean_line(line))
        for pattern in patterns:
            match = pattern.search(value)
            if match:
                return match.group(0).strip().rstrip(",;:.")
    return None


def _company_below_main_title(content: str) -> str | None:
    lines = content.splitlines()
    non_company_values = {
        "apply",
        "apply now",
        "bewerben",
        "jetzt bewerben",
        "kontakt",
        "contact",
        "info",
    }
    for index, line in enumerate(lines):
        if not re.match(r"^\s*(?:>\s*)?#\s+\S", line):
            continue
        for candidate in lines[index + 1 : index + 5]:
            value = _clean_line(candidate)
            if not value:
                continue
            if value.startswith("#") or value == "&nbsp;":
                break
            if _normalized_heading(value) in non_company_values:
                continue
            if (
                "," in value
                or re.fullmatch(r"[A-Z][A-Za-z .'-]{2,40}", value)
                and value.casefold()
                in {"berlin", "munich", "münchen", "hamburg", "cologne", "köln"}
            ):
                continue
            if len(value) <= 200 and not re.match(r"^(https?://|www\.)", value):
                return value
        break
    return None


def _company_from_brand_link(content: str) -> str | None:
    """Extract a company name from a logo/brand link near the job header."""
    match = re.search(
        r"(?im)^\s*\[!\[([^\]\r\n]+?)\]\([^)]*\)\]\([^)]*\)\s*$",
        content,
    )
    if not match:
        return None
    label = re.sub(r"\s+logo\s*$", "", match.group(1), flags=re.IGNORECASE).strip()
    return label if label and len(label) <= 120 else None


def _personio_company_from_role_section(
    content: str, source_url: str | None
) -> str | None:
    """Read the employer introduced in the opening role section on Personio."""
    if not source_url or not re.search(r"https?://[^/]*personio\.de/", source_url, re.I):
        return None
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if _normalized_heading(line) != "deine rolle bei uns":
            continue
        for candidate in lines[index + 1 : index + 12]:
            match = re.match(
                r"\s*Bei\s+([A-Z0-9][A-Z0-9&.-]*(?:\s+[A-Z0-9&.-]+)*)\s+(?=[a-z])",
                candidate,
            )
            if not match:
                continue
            company = match.group(1).strip()
            if company.casefold() not in {"uns", "unsere", "unserem"}:
                return company
    return None


def _instaffo_metadata(content: str) -> dict[str, str | None]:
    title_match = re.search(r"(?m)^#\s+([^#\r\n]+?)\s*$", content)
    company_match = re.search(
        r"(?ims)^##\s+\**(?:Firmendetails|Company details)\**\s*$"
        r"\s*^#{1,3}\s+([^#\r\n]+?)\s*$",
        content,
    )
    location_match = re.search(
        r"(?im)^\s*([^\r\n]{2,100}?)\s+Bürostandorte\s*$",
        content,
    )
    employment_match = re.search(
        r"(?im)^\s*[^A-Za-z\r\n]{0,3}"
        r"(Vollzeit|Teilzeit|Full[- ]time|Part[- ]time)\b",
        content,
    )
    return {
        "title": _clean_line(title_match.group(1)) if title_match else None,
        "company": _clean_line(company_match.group(1)) if company_match else None,
        "location": location_match.group(1).strip() if location_match else None,
        "employment_type": employment_match.group(1) if employment_match else None,
    }


def _source_portal(
    *,
    source_filename: str | None,
    source_url: str | None = None,
) -> str | None:
    source = f"{source_filename or ''} {source_url or ''}".casefold()
    portals = (
        ("personio", "Personio"),
        ("indeed", "Indeed"),
        ("instaffo", "Instaffo"),
        ("linkedin", "LinkedIn"),
        ("stepstone", "StepStone"),
        ("xing", "XING"),
        ("jobsuche der ba", "Bundesagentur für Arbeit"),
        ("arbeitsagentur", "Bundesagentur für Arbeit"),
    )
    return next((label for marker, label in portals if marker in source), None)


def extract_job_metadata(
    content: str,
    *,
    source_filename: str | None = None,
    source_url: str | None = None,
) -> dict[str, str | None]:
    lowered = content.casefold()
    instaffo = (
        _instaffo_metadata(content)
        if source_filename and "instaffo" in source_filename.casefold()
        else {}
    )
    compact = _compact_header_metadata(content)
    if re.search(
        r"\b(100\s*%\s*remote|fully remote|vollständig remote|"
        r"remote in (?:de|germany|deutschland))\b",
        lowered,
    ):
        work_model = "Remote"
    elif re.search(r"\b(hybrid|hybrides arbeiten)\b", lowered):
        work_model = "Hybrid"
    elif re.search(r"\b(homeoffice|remote work|work remotely|remotely)\b", lowered):
        work_model = "Remote möglich"
    else:
        work_model = None
    profile_work_model = _inline_value(content, {"work model", "arbeitsmodell"})
    plain_title, plain_company = _plain_pdf_header(content)
    company = (
        instaffo.get("company")
        or _join_company(content, source_url)
        or _personio_company_from_role_section(content, source_url)
        or (
            first_metadata_match(content, COMPANY_PATTERNS)
            or _company_from_brand_link(content)
            or _company_below_main_title(content)
            or _section_value(content, {"informationen", "information", "company information"})
            or compact["company"]
            or _legal_company_from_prose(content)
            or plain_company
            or _standalone_legal_company(content)
        )
    )
    location_headings = {
        "arbeitsort",
        "arbeitsorte",
        "standort",
        "standorte",
        "location",
        "locations",
    }
    location = (
        instaffo.get("location")
        or _inline_value(
            content,
            location_headings,
        )
        or _location_section_value(
            content,
            location_headings,
        )
        or _value_before_heading(
            content,
            {"bürostandorte", "standorte", "office locations"},
        )
        or compact["location"]
        or _map_link_location(content)
    )
    if location and re.match(
        r"^\d+\s*(?:min(?:ute)?n?|stunden?|hours?)\s+ab\b",
        location,
        re.IGNORECASE,
    ):
        location = _inline_value(
            content,
            {"job address", "adresse", "anschrift"},
        ) or _section_value(
            content,
            {"job address", "adresse", "anschrift"},
        )
    inline_employment_type = _inline_value(
        content,
        {"anstellungsart", "beschäftigungsart", "employment type"},
    )
    employment_type = (
        instaffo.get("employment_type")
        or inline_employment_type
        or _section_value(
            content,
            {"anstellungsart", "beschäftigungsart", "employment type"},
        )
    )
    if employment_type is None:
        employment_type = first_metadata_match(
            "\n".join(content.splitlines()[:40]),
            (
                re.compile(
                    r"(?im)^\s*((?:Teilzeit,\s*)?Vollzeit|Teilzeit|"
                    r"Full[- ]time|Part[- ]time)\s*$"
                ),
            ),
        )
    employment_type, inferred_contract_term = _split_employment_contract(employment_type)
    contract_term = _inline_value(
        content,
        {"befristung", "vertragsdauer", "contract term", "contract duration"},
    ) or _section_value(
        content,
        {"befristung", "vertragsdauer", "contract term", "contract duration"},
    )
    contract_term = contract_term or _contract_term_from_role_scope(content)
    return {
        "title": _clean_title(
            _main_heading(content)
            or _title_from_job_intro(content)
            or instaffo.get("title")
            or compact["title"]
            or plain_title
            or _main_heading(content)
        ),
        "company": company,
        "published_text": first_metadata_match(content, PUBLISHED_TEXT_PATTERNS),
        "location": location,
        "employment_type": employment_type,
        "contract_term": contract_term or inferred_contract_term,
        "work_model": work_model or profile_work_model or compact["work_model"],
        "source_portal": _source_portal(
            source_filename=source_filename,
            source_url=source_url,
        ),
        "language": detect_job_language(content),
    }
