"""Provider-neutral embedding interface for hybrid requirement retrieval."""

from collections.abc import Sequence
from typing import Protocol

import httpx

from app.core.config import Settings


def build_evidence_embedding_text(*, label: str, evidence_text: str, source_name: str | None = None) -> str:
    """Build stable, contextual text for evidence embeddings."""
    parts = [f"Evidence: {evidence_text.strip()}", f"Type: {label.strip()}"]
    if source_name and source_name.strip():
        parts.append(f"Source: {source_name.strip()}")
    return "\n".join(parts)


def build_requirement_embedding_text(requirement: str) -> str:
    return f"Job requirement: {requirement.strip()}"


def create_embedding_provider(settings: Settings):
    if settings.embedding_provider.casefold() in {"", "disabled", "none"}:
        return None
    if settings.embedding_provider.casefold() not in {"openai", "openai_compatible"}:
        raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
    if settings.embedding_api_key is None:
        raise ValueError("Embedding provider is enabled but EMBEDDING_API_KEY is missing")
    return OpenAICompatibleEmbeddingProvider(
        base_url=str(settings.embedding_base_url),
        api_key=settings.embedding_api_key.get_secret_value(),
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
    )


class EmbeddingProvider(Protocol):
    model: str
    dimension: int

    def embed_text(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]: ...


def validate_embedding(vector: Sequence[float], *, dimension: int) -> list[float]:
    """Validate provider output before it is persisted or used for search."""
    values = [float(value) for value in vector]
    if len(values) != dimension:
        raise ValueError(f"Expected embedding dimension {dimension}, got {len(values)}")
    return values


def validate_batch(
    vectors: Sequence[Sequence[float]], *, expected_count: int, dimension: int
) -> list[list[float]]:
    if len(vectors) != expected_count:
        raise ValueError(f"Expected {expected_count} embeddings, got {len(vectors)}")
    return [validate_embedding(vector, dimension=dimension) for vector in vectors]


class OpenAICompatibleEmbeddingProvider:
    """Embedding provider for OpenAI-compatible ``/embeddings`` APIs."""

    def __init__(self, *, base_url: str, api_key: str, model: str, dimension: int, client: httpx.Client | None = None) -> None:
        self.model = model
        self.dimension = dimension
        self._client = client or httpx.Client(base_url=base_url.rstrip("/"), timeout=60.0)
        self._api_key = api_key

    def embed_text(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.post(
            "/embeddings",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self.model, "input": list(texts)},
        )
        response.raise_for_status()
        payload = response.json()
        data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
        return validate_batch(
            [item["embedding"] for item in data],
            expected_count=len(texts),
            dimension=self.dimension,
        )
