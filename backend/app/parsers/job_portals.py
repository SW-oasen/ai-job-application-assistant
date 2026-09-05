"""Portal profiles that normalize captured job pages before extraction.

Profiles intentionally only handle portal presentation and noise.  The common
metadata and structure parsers continue to own the canonical job document.
"""

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class NormalizedJobDocument:
    markdown: str
    title: str | None
    profile_name: str | None


@dataclass(frozen=True)
class JobPortalProfile:
    name: str
    url_pattern: re.Pattern[str]

    def matches(self, source_url: str | None) -> bool:
        return bool(source_url and self.url_pattern.search(source_url))

    def normalize(self, markdown: str, title: str | None, raw_html: str | None = None) -> NormalizedJobDocument:
        return NormalizedJobDocument(markdown=markdown, title=title, profile_name=self.name)


class LinkedInProfile(JobPortalProfile):
    """Normalize LinkedIn's captured job-details layout.

    LinkedIn currently renders the title and metadata as ordinary header lines,
    while the actual advertisement starts below ``Details zum Jobangebot``.
    """

    _DETAILS = re.compile(r"(?im)^##\s+(?:Details zum Jobangebot|About the job)\s*$")
    _END = re.compile(
        r"(?im)^##\s+(?:Benachrichtigung f(?:Ã¼|ü)r .*Jobangebote einrichten|"
        r"Weitere Jobs|Similar jobs|Set alert|About the company|"
        r"Interested in working with us in the future\?|Trending employee content)\s*$"
    )
    _COMPANY = re.compile(
        r"\[([^\]\n]{2,160})\]\(https?://[^)\n]*linkedin\.com/company/[^)\n]*\)",
        re.IGNORECASE,
    )
    _LOCATION = re.compile(
        r"(?m)^([^\n]+?)\s+(?:Â·|·)\s+(?:\*\*Vor|Reposted|Posted)\b",
        re.IGNORECASE,
    )

    def normalize(
        self, markdown: str, title: str | None, raw_html: str | None = None
    ) -> NormalizedJobDocument:
        details = self._DETAILS.search(markdown)
        if not details:
            return super().normalize(markdown, title)

        header = markdown[: details.start()]
        body = markdown[details.end() :]
        end = self._END.search(body)
        if end:
            body = body[: end.start()]

        company_match = self._COMPANY.search(header)
        company = company_match.group(1).strip() if company_match else None
        location_match = self._LOCATION.search(header)
        location = location_match.group(1).strip() if location_match else None
        extracted_title = _linkedin_title(header) or title
        work_model = _linked_header_value(header, "Remote", "Hybrid")
        employment_type = _linked_header_value(
            header, "Vollzeit", "Teilzeit", "Full-time", "Part-time"
        )
        canonical_header = [f"# {extracted_title}"] if extracted_title else []
        canonical_header.extend(f"{key}: {value}" for key, value in (("Company", company), ("Location", location), ("Work model", work_model), ("Employment type", employment_type)) if value)
        for pattern, replacement in ((r"(?im)^\*\*Focus\*\*\s*$", "## Activities"), (r"(?im)^\*\*Tech Stack\*\*\s*$", "## Requirements"), (r"(?im)^\*\*Ideal Experience\*\*\s*$", "## Requirements"), (r"(?im)^\*\*Was du bei uns bewegen kannst\*\*\s*$", "## Activities"), (r"(?im)^In unseren Projekten verwenden wir h(?:ÃƒÆ’Ã‚Â¤|ÃƒÂ¤|Ã¤)ufig folgende Technologien:\s*$", "## Requirements"), (r"(?im)^\*\*Wer gut zu uns passen w(?:ÃƒÆ’Ã‚Â¼|ÃƒÂ¼|Ã¼)rde\*\*\s*$", "## Requirements"), (r"(?im)^\*\*Was wir dir bieten\*\*\s*$", "## Benefits")):
            body = re.sub(pattern, replacement, body)
        return NormalizedJobDocument("\n\n".join([*canonical_header, body.strip()]).strip(), extracted_title, self.name)


class InovexProfile(JobPortalProfile):
    """Expose the TL;DR sidebar that is outside Inovex's article element."""

    def normalize(self, markdown: str, title: str | None, raw_html: str | None = None) -> NormalizedJobDocument:
        if not raw_html:
            return super().normalize(markdown, title, raw_html)
        labels = [item.get_text(" ", strip=True) for item in BeautifulSoup(raw_html, "html.parser").select(".information .info-item")]
        employment = next((value for value in labels if re.search(r"\b(?:Vollzeit|Teilzeit)\b", value, re.I)), None)
        location = next((re.sub(r"^Standorte:\s*", "", value, flags=re.I) for value in labels if value.casefold().startswith("standorte:")), None)
        work_model = next(("Remote möglich" for value in labels if re.search(r"mobiles arbeiten", value, re.I)), None)
        header = [f"# {title}"] if title and not markdown.startswith("# ") else []
        header.extend(f"{key}: {value}" for key, value in (("Employment type", employment), ("Location", location), ("Work model", work_model)) if value)
        return NormalizedJobDocument("\n\n".join([*header, markdown]).strip(), title, self.name)


class DeloitteProfile(JobPortalProfile):
    """Map Deloitte's candidate-facing section labels to the canonical schema."""

    _SECTION_REPLACEMENTS = (
        (r"(?im)^#{1,6}\s+Dein Impact\s*:?\s*$", "## Activities"),
        (r"(?im)^#{1,6}\s+Dein Skillset\s*:?\s*$", "## Requirements"),
        (r"(?im)^#{1,6}\s+Deine Chance\s*:?\s*$", "## Benefits"),
    )

    def normalize(
        self, markdown: str, title: str | None, raw_html: str | None = None
    ) -> NormalizedJobDocument:
        body = markdown
        for pattern, replacement in self._SECTION_REPLACEMENTS:
            body = re.sub(pattern, replacement, body)
        return NormalizedJobDocument(body, title, self.name)

        canonical_header = [f"# {extracted_title}"] if extracted_title else []
        canonical_header.extend(
            f"{label}: {value}"
            for label, value in (
                ("Company", company),
                ("Location", location),
                ("Work model", work_model),
                ("Employment type", employment_type),
            )
            if value
        )
        body = re.sub(r"(?im)^\*\*Focus\*\*\s*$", "## Activities", body)
        body = re.sub(r"(?im)^\*\*Tech Stack\*\*\s*$", "## Requirements", body)
        body = re.sub(r"(?im)^\*\*Ideal Experience\*\*\s*$", "## Requirements", body)
        body = re.sub(
            r"(?im)^\*\*Was du bei uns bewegen kannst\*\*\s*$", "## Activities", body
        )
        body = re.sub(
            r"(?im)^In unseren Projekten verwenden wir h(?:ÃƒÂ¤|Ã¤|ä)ufig folgende Technologien:\s*$",
            "## Requirements",
            body,
        )
        body = re.sub(
            r"(?im)^\*\*Wer gut zu uns passen w(?:ÃƒÂ¼|Ã¼|ü)rde\*\*\s*$",
            "## Requirements",
            body,
        )
        body = re.sub(r"(?im)^\*\*Was wir dir bieten\*\*\s*$", "## Benefits", body)
        return NormalizedJobDocument(
            markdown="\n\n".join([*canonical_header, body.strip()]).strip(),
            title=extracted_title,
            profile_name=self.name,
        )


def _linkedin_title(header: str) -> str | None:
    lines = [line.strip() for line in header.splitlines()]
    for index, line in enumerate(lines):
        if not re.search(r"linkedin\.com/company/", line, re.IGNORECASE):
            continue
        for candidate in lines[index + 1 :]:
            if not candidate:
                continue
            if candidate.startswith(("[", "#")) or "Â·" in candidate or "·" in candidate:
                continue
            if len(candidate) <= 160:
                return candidate.replace(r"\*", "*")
    return None


def _linked_header_value(header: str, *values: str) -> str | None:
    for value in values:
        if re.search(rf"\[{re.escape(value)}\]\(", header, re.IGNORECASE):
            return value
    return None


# These profiles establish deterministic URL routing now.  Portal-specific
# normalizers can be added independently without changing the import pipeline.
PORTAL_PROFILES: tuple[JobPortalProfile, ...] = (
    LinkedInProfile(
        "linkedin", re.compile(r"(?:^|//)(?:www\.)?linkedin\.com/jobs/", re.IGNORECASE)
    ),
    JobPortalProfile("indeed", re.compile(r"(?:^|//)(?:[^/]+\.)?indeed\.", re.IGNORECASE)),
    JobPortalProfile("instaffo", re.compile(r"(?:^|//)(?:www\.)?instaffo\.com/", re.IGNORECASE)),
    JobPortalProfile("stepstone", re.compile(r"(?:^|//)(?:www\.)?stepstone\.", re.IGNORECASE)),
    JobPortalProfile("xing", re.compile(r"(?:^|//)(?:www\.)?xing\.com/", re.IGNORECASE)),
    InovexProfile("inovex", re.compile(r"(?:^|//)(?:www\.)?inovex\.de/", re.IGNORECASE)),
    DeloitteProfile("deloitte", re.compile(r"(?:^|//)job\.deloitte\.com/", re.IGNORECASE)),
)


def normalize_job_document(
    markdown: str, *, title: str | None, source_url: str | None, raw_html: str | None = None
) -> NormalizedJobDocument:
    """Select a portal profile by URL; leave unknown portals untouched."""
    profile = next((item for item in PORTAL_PROFILES if item.matches(source_url)), None)
    if profile is None:
        return NormalizedJobDocument(markdown=markdown, title=title, profile_name=None)
    return profile.normalize(markdown, title, raw_html)
