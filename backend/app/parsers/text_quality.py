from dataclasses import dataclass

BLOCK_PAGE_MARKERS = (
    "access denied",
    "captcha",
    "verify you are human",
    "enable javascript",
    "sign in to continue",
)
JOB_CONTENT_MARKERS = (
    "aufgaben",
    "anforderungen",
    "qualifikationen",
    "dein profil",
    "ihr profil",
    "was du mitbringst",
    "was wir bieten",
    "responsibilities",
    "requirements",
    "qualifications",
    "your profile",
    "what you bring",
    "what we offer",
)
BLOCK_PAGE_TITLES = {
    "access denied",
    "just a moment",
    "verify you are human",
    "security check",
}


@dataclass(frozen=True)
class QualityResult:
    sufficient: bool
    text_length: int
    warnings: list[str]


def assess_text_quality(
    text: str,
    *,
    title: str | None,
    minimum_length: int,
) -> QualityResult:
    normalized = " ".join(text.split())
    lowered = normalized.lower()
    warnings: list[str] = []
    blocking = False

    if len(normalized) < minimum_length:
        warnings.append("content_below_minimum_length")
        blocking = True
    if not title:
        warnings.append("title_not_detected")
        blocking = True
    block_marker_found = any(marker in lowered for marker in BLOCK_PAGE_MARKERS)
    if block_marker_found:
        warnings.append("possible_login_or_bot_protection")
        job_marker_count = sum(marker in lowered for marker in JOB_CONTENT_MARKERS)
        normalized_title = " ".join((title or "").lower().split())
        if normalized_title in BLOCK_PAGE_TITLES or job_marker_count < 2:
            blocking = True

    return QualityResult(
        sufficient=not blocking,
        text_length=len(normalized),
        warnings=warnings,
    )
