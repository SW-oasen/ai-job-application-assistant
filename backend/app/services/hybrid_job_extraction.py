"""Semantic fallback for job-structure extraction."""

import asyncio
import math

from app.core.config import get_settings
from app.parsers.job_structure import LIST_ITEM_PATTERN, extract_job_structure
from app.services.embedding_service import EmbeddingProvider, create_embedding_provider

_PROTOTYPES = {
    "activity": "Job responsibility or task: develop, operate, coordinate, implement, analyze or maintain something.",
    "requirement": "Job qualification or requirement: skills, experience, education, language or capability the candidate must have.",
    "benefit": "Employer benefit or working condition offered by the organization.",
}


def _cosine(left: list[float], right: list[float]) -> float:
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 0.0


async def extract_job_structure_hybrid(content: str):
    structure = extract_job_structure(content)
    provider: EmbeddingProvider | None = create_embedding_provider(get_settings())
    if provider is None:
        return structure

    # A missing or suspiciously small core section usually means that the
    # deterministic heading parser missed a section boundary. In that case
    # semantic extraction must reconsider the complete list-item corpus, not
    # merely the few items left over by the parser.
    needs_full_semantic_pass = len(structure.activities) <= 2 or len(structure.requirements) <= 2
    known = {
        item.get("evidence") or item.get("activity") or item.get("requirement") or item.get("benefit")
        for items in (structure.activities, structure.requirements, structure.benefits)
        for item in items
    }
    candidates = [
        match.group(1).strip()
        for line in content.splitlines()
        if (match := LIST_ITEM_PATTERN.match(line))
        and (
            needs_full_semantic_pass
            or match.group(1).strip() not in known
        )
    ]
    if not candidates:
        return structure
    texts = [*candidates, *_PROTOTYPES.values()]
    vectors = await asyncio.to_thread(provider.embed_batch, texts)
    candidate_vectors = vectors[: len(candidates)]
    prototype_vectors = vectors[len(candidates) :]
    additions = {"activity": [], "requirement": [], "benefit": []}
    for text, vector in zip(candidates, candidate_vectors, strict=True):
        scores = {name: _cosine(vector, prototype) for name, prototype in zip(_PROTOTYPES, prototype_vectors, strict=True)}
        category, score = max(scores.items(), key=lambda item: item[1])
        if score < 0.70:
            continue
        if category == "activity":
            additions[category].append({"activity": text, "category": "responsibility", "keywords": [], "confidence": round(score, 2), "evidence": text})
        elif category == "requirement":
            additions[category].append({"requirement": text, "category": "other", "priority": "should", "keywords": [], "confidence": round(score, 2), "evidence": text})
        else:
            additions[category].append({"benefit": text, "evidence": text, "confidence": round(score, 2)})
    def merge(kind: str, existing: list[dict], added: list[dict], key: str) -> list[dict]:
        result = []
        seen: set[str] = set()
        for item in [*existing, *added]:
            value = str(item.get(key) or item.get("evidence") or "").strip().casefold()
            if value and value not in seen:
                seen.add(value)
                result.append(item)
        return result

    return type(structure)(
        activities=merge("activity", structure.activities, additions["activity"], "activity")[:100],
        requirements=merge("requirement", structure.requirements, additions["requirement"], "requirement")[:200],
        benefits=merge("benefit", structure.benefits, additions["benefit"], "benefit")[:100],
    )
