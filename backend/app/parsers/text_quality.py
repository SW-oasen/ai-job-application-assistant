from dataclasses import dataclass

BLOCK_PAGE_MARKERS = (
    "access denied",
    "captcha",
    "verify you are human",
    "enable javascript",
    "sign in to continue",
)


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

    if len(normalized) < minimum_length:
        warnings.append("content_below_minimum_length")
    if not title:
        warnings.append("title_not_detected")
    if any(marker in lowered for marker in BLOCK_PAGE_MARKERS):
        warnings.append("possible_login_or_bot_protection")

    return QualityResult(
        sufficient=not warnings,
        text_length=len(normalized),
        warnings=warnings,
    )

