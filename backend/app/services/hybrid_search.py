"""Candidate retrieval primitives backed by ChromaDB."""

from collections.abc import Iterable
from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class RetrievalCandidate:
    evidence_id: UUID
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    retrieval_sources: set[str] = field(default_factory=set)


def merge_candidates(lexical: Iterable[RetrievalCandidate], semantic: Iterable[RetrievalCandidate]) -> list[RetrievalCandidate]:
    merged: dict[UUID, RetrievalCandidate] = {}
    for candidate, source in [(item, "lexical") for item in lexical] + [(item, "semantic") for item in semantic]:
        current = merged.setdefault(candidate.evidence_id, RetrievalCandidate(candidate.evidence_id))
        current.lexical_score = max(current.lexical_score, candidate.lexical_score)
        current.semantic_score = max(current.semantic_score, candidate.semantic_score)
        current.retrieval_sources.add(source)
    return sorted(merged.values(), key=lambda item: (max(item.lexical_score, item.semantic_score), len(item.retrieval_sources)), reverse=True)


class ChromaEvidenceStore:
    def __init__(self, *, host: str, port: int, collection_name: str) -> None:
        import chromadb
        self._client = chromadb.HttpClient(host=host, port=port)
        self._collection = self._client.get_or_create_collection(collection_name, metadata={"hnsw:space": "cosine"})

    def upsert(self, *, evidence_id: str, profile_id: str, embedding: list[float], document: str, model: str) -> None:
        self._collection.upsert(ids=[evidence_id], embeddings=[embedding], documents=[document], metadatas=[{"profile_id": profile_id, "embedding_model": model}])

    def query(self, *, profile_id: str, embedding: list[float], top_k: int = 10) -> list[RetrievalCandidate]:
        result = self._collection.query(query_embeddings=[embedding], n_results=top_k, where={"profile_id": profile_id}, include=["distances"])
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [RetrievalCandidate(UUID(evidence_id), semantic_score=max(0.0, 1.0 - float(distance)), retrieval_sources={"semantic"}) for evidence_id, distance in zip(ids, distances, strict=False)]
