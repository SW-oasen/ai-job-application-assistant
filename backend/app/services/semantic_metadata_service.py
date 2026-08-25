import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.parsers.job_metadata import extract_job_metadata

REQUIRED_FIELDS = ("title", "company", "location", "language")
SUPPORTED_FIELDS = (
    "title",
    "company",
    "location",
    "work_model",
    "employment_type",
    "contract_term",
    "language",
)
AUTO_ACCEPT_CONFIDENCE = 0.85
MAX_METADATA_LENGTHS = {
    "company": 300,
}


def _normalized_evidence_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _has_verifiable_evidence(
    *,
    field: str,
    value: str,
    evidence: str | None,
    content: str,
) -> bool:
    if not content:
        return bool(evidence)
    normalized_content = _normalized_evidence_text(content)
    if evidence and _normalized_evidence_text(evidence) in normalized_content:
        return True
    # Company descriptions from career portals are often reformatted or
    # truncated during HTML-to-Markdown conversion. The company name itself
    # remains a concise, source-verifiable identifier in those cases.
    return field == "company" and _normalized_evidence_text(value) in normalized_content


def _is_usable_metadata_value(field: str, value: str | None) -> bool:
    if not value or not value.strip():
        return False
    maximum_length = MAX_METADATA_LENGTHS.get(field)
    return maximum_length is None or len(value.strip()) <= maximum_length


def _sanitize_metadata(metadata: dict[str, str | None]) -> dict[str, str | None]:
    return {
        field: value if _is_usable_metadata_value(field, value) else None
        for field, value in metadata.items()
    }


@dataclass(frozen=True)
class SemanticMetadataResult:
    metadata: dict[str, str | None]
    details: dict[str, dict[str, Any]]
    warnings: list[str]


def metadata_needs_semantic_fallback(metadata: dict[str, str | None]) -> bool:
    if any(not _is_usable_metadata_value(field, metadata.get(field)) for field in REQUIRED_FIELDS):
        return True
    location = metadata.get("location") or ""
    return len(location) > 120 or len(location.split()) > 12


def _workflow_url() -> str:
    base = str(get_settings().dify_base_url).rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/workflows/run"


def _parse_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    candidate = outputs.get("metadata_json", outputs.get("metadata", outputs))
    if isinstance(candidate, str):
        candidate = json.loads(candidate)
    return candidate if isinstance(candidate, dict) else {}


def _accepted_metadata(
    rules: dict[str, str | None],
    semantic: dict[str, Any],
    *,
    content: str = "",
) -> tuple[dict[str, str | None], dict[str, dict[str, Any]]]:
    merged = dict(rules)
    details: dict[str, dict[str, Any]] = {}
    for field in SUPPORTED_FIELDS:
        item = semantic.get(field)
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        confidence = item.get("confidence", 0)
        evidence = item.get("evidence")
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        if field == "language":
            value = value.casefold()
            if value not in {"de", "en"}:
                continue
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0
        details[field] = {
            "value": value,
            "confidence": max(0.0, min(confidence, 1.0)),
            "evidence": evidence if isinstance(evidence, str) else None,
        }
        evidence_is_verifiable = _has_verifiable_evidence(
            field=field,
            value=value,
            evidence=evidence if isinstance(evidence, str) else None,
            content=content,
        )
        evidence_is_benefit = field == "work_model" and any(
            marker in (evidence or "").casefold()
            for marker in (
                "work-life balance",
                "benefit",
                "leistung",
                "top-angebot",
                "wir bieten",
            )
        )
        if (
            not _is_usable_metadata_value(field, merged.get(field))
            and confidence >= AUTO_ACCEPT_CONFIDENCE
            and evidence_is_verifiable
            and not evidence_is_benefit
        ):
            merged[field] = value
    return merged, details


async def enrich_job_metadata(
    content: str,
    *,
    source_filename: str | None = None,
    source_url: str | None = None,
) -> SemanticMetadataResult:
    rules = _sanitize_metadata(
        extract_job_metadata(
            content,
            source_filename=source_filename,
            source_url=source_url,
        )
    )
    if not metadata_needs_semantic_fallback(rules):
        return SemanticMetadataResult(rules, {}, [])

    settings = get_settings()
    key = settings.dify_metadata_workflow_api_key
    token = key.get_secret_value().strip() if key else ""
    if not token:
        return SemanticMetadataResult(
            rules,
            {},
            ["semantic_metadata_fallback_not_configured"],
        )

    inputs = {
        "job_content": content[: settings.semantic_metadata_max_characters],
        "source_filename": source_filename or "",
        "source_url": source_url or "",
        "rule_metadata_json": json.dumps(rules, ensure_ascii=False),
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.dify_metadata_workflow_timeout_seconds)
        ) as client:
            response = await client.post(
                _workflow_url(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": inputs,
                    "response_mode": "blocking",
                    "user": "job-metadata-import",
                },
            )
        response.raise_for_status()
        data = response.json().get("data") or {}
        if data.get("status") != "succeeded":
            raise ValueError(data.get("error") or "workflow failed")
        semantic = _parse_outputs(data.get("outputs") or {})
        merged, details = _accepted_metadata(rules, semantic, content=content)
        warnings = ["semantic_metadata_fallback_used"]
        if metadata_needs_semantic_fallback(merged):
            warnings.append("semantic_metadata_incomplete")
        return SemanticMetadataResult(merged, details, warnings)
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        return SemanticMetadataResult(
            rules,
            {},
            ["semantic_metadata_fallback_failed"],
        )
