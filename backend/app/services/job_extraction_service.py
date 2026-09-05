"""LLM fallback for complete job extraction, grounded in source evidence."""

import json
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.semantic_metadata_service import (
    SemanticMetadataResult,
    _accepted_metadata,
    _parse_outputs,
    _sanitize_metadata,
    _workflow_url,
    metadata_needs_semantic_fallback,
    enrich_job_metadata,
)


@dataclass(frozen=True)
class JobExtractionResult:
    metadata: dict[str, str | None]
    activities: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    metadata_details: dict[str, dict[str, Any]]
    warnings: list[str]


def needs_llm_extraction(
    metadata: dict[str, str | None], activities: list[dict[str, Any]], requirements: list[dict[str, Any]]
) -> bool:
    return metadata_needs_semantic_fallback(metadata) or len(activities) <= 2 or len(requirements) <= 2


def is_job_extraction_llm_configured() -> bool:
    key = get_settings().dify_job_extraction_workflow_api_key
    return bool(key and key.get_secret_value().strip())


def _source_backed_items(value: object, key: str, content: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized = " ".join(content.casefold().split())
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict) or not isinstance(raw.get(key), str):
            continue
        text = raw[key].strip()
        evidence = raw.get("evidence") if isinstance(raw.get("evidence"), str) else text
        if not text or " ".join(evidence.casefold().split()) not in normalized:
            continue
        identity = " ".join(text.casefold().split())
        if identity in seen:
            continue
        seen.add(identity)
        item = {key: text, "category": raw.get("category") or ("responsibility" if key == "activity" else "other"), "keywords": raw.get("keywords") if isinstance(raw.get("keywords"), list) else [], "evidence": evidence}
        if key == "requirement":
            item["priority"] = raw.get("priority") if raw.get("priority") in {"must", "should", "nice_to_have"} else "should"
        result.append(item)
    return result


def _merge_source_backed_items(
    extracted: list[dict[str, Any]], fallback: list[dict[str, Any]], key: str
) -> list[dict[str, Any]]:
    """Retain parser findings when an LLM extraction omits source-backed items.

    A workflow result is useful for categorisation, but it is not allowed to
    silently shrink a requirement or activity list that has already been
    grounded in the advert.  Evidence is the best de-duplication key because
    the LLM may paraphrase the item text while keeping the original quote.
    """
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in [*extracted, *fallback]:
        text = item.get(key)
        if not isinstance(text, str) or not text.strip():
            continue
        evidence = item.get("evidence")
        identity = evidence if isinstance(evidence, str) and evidence.strip() else text
        normalized = " ".join(identity.casefold().split())
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)
    return result


async def enrich_job_extraction(
    *, content: str, metadata: dict[str, str | None], activities: list[dict[str, Any]], requirements: list[dict[str, Any]], source_filename: str | None = None, source_url: str | None = None, retry_instructions: list[str] | None = None,
) -> JobExtractionResult:
    rules = _sanitize_metadata(metadata)
    if not needs_llm_extraction(rules, activities, requirements) and not retry_instructions:
        return JobExtractionResult(rules, activities, requirements, {}, [])
    settings = get_settings()
    key = settings.dify_job_extraction_workflow_api_key
    token = key.get_secret_value().strip() if key else ""
    if not token:
        legacy = await enrich_job_metadata(
            content, source_filename=source_filename, source_url=source_url
        )
        return JobExtractionResult(
            legacy.metadata,
            activities,
            requirements,
            legacy.details,
            [*legacy.warnings, "job_extraction_llm_not_configured"],
        )
    inputs = {"job_content": content[: settings.job_extraction_max_characters], "source_filename": source_filename or "", "source_url": source_url or "", "rule_metadata_json": json.dumps(rules, ensure_ascii=False), "rule_activities_json": json.dumps(activities, ensure_ascii=False), "rule_requirements_json": json.dumps(requirements, ensure_ascii=False), "retry_instructions_json": json.dumps(retry_instructions or [], ensure_ascii=False)}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.dify_job_extraction_workflow_timeout_seconds)) as client:
            response = await client.post(_workflow_url(), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"inputs": inputs, "response_mode": "blocking", "user": "job-extraction"})
        response.raise_for_status()
        data = response.json().get("data") or {}
        if data.get("status") != "succeeded":
            raise ValueError(data.get("error") or "workflow failed")
        outputs = data.get("outputs") or {}
        extracted = outputs.get("extraction_json", outputs)
        if isinstance(extracted, str):
            extracted = json.loads(extracted)
        if not isinstance(extracted, dict):
            extracted = _parse_outputs(outputs)
        semantic_metadata = extracted.get("metadata") if isinstance(extracted.get("metadata"), dict) else extracted
        merged_metadata, details = _accepted_metadata(rules, semantic_metadata, content=content)
        llm_activities = _source_backed_items(extracted.get("activities"), "activity", content)
        llm_requirements = _source_backed_items(extracted.get("requirements"), "requirement", content)
        return JobExtractionResult(
            merged_metadata,
            _merge_source_backed_items(llm_activities, activities, "activity"),
            _merge_source_backed_items(llm_requirements, requirements, "requirement"),
            details,
            ["job_extraction_llm_used"],
        )
    except (httpx.HTTPError, ValueError, json.JSONDecodeError):
        legacy = await enrich_job_metadata(
            content, source_filename=source_filename, source_url=source_url
        )
        return JobExtractionResult(
            legacy.metadata,
            activities,
            requirements,
            legacy.details,
            [*legacy.warnings, "job_extraction_llm_failed"],
        )
