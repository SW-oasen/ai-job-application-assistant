"""Deterministic extraction of a job role separately from seniority."""

import re

_LEVEL = re.compile(r"\b(entry[- ]level|junior|mid[- ]level|senior|staff|principal|lead|manager|head of)\b", re.I)
_ROLE_SUFFIX = re.compile(r"\b(engineer|developer|scientist|analyst|architect|designer|manager|consultant|researcher|specialist|officer)\b", re.I)
_ROLE_CONTEXT = re.compile(r"\b(your role|the role|position|we are looking for|you will be|mission|responsibilit(?:y|ies))\b", re.I)


def extract_job_role(title: str | None, content: str = "") -> str | None:
    """Return the role from title, using description lines as a fallback.

    Seniority words are removed so role and level remain independent. Description
    lines are preferred when they contain a clearer role-like phrase.
    """
    candidates = [line.strip(" #-*\t") for line in content.splitlines() if line.strip()]
    title_value = (title or "").strip()
    candidates = [title_value, *candidates[:80]]
    role_candidates = [line for line in candidates if _ROLE_SUFFIX.search(line) and len(line) <= 140]
    contextual = [line for line in role_candidates if _ROLE_CONTEXT.search(line)]
    value = (contextual[0] if contextual else role_candidates[0] if role_candidates else title_value).strip()
    if contextual:
        value = re.sub(r"^.*?(?:your role|the role|position|we are looking for|you will be|mission|responsibilities)\s*[:\-]?\s*", "", value, flags=re.I)
        value = re.split(r"[.!?]", value, maxsplit=1)[0].strip()
    value = re.sub(r"\s+", " ", value)
    value = _LEVEL.sub("", value)
    value = re.sub(r"\s{2,}", " ", value).strip(" -,:;")
    return value or None
