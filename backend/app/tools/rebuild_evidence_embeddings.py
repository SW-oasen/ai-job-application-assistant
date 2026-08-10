"""Backfill missing or stale profile-evidence embeddings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProfileEvidence, ProfileSource
from app.services.embedding_service import EmbeddingProvider, build_evidence_embedding_text
from app.services.hybrid_search import ChromaEvidenceStore


async def rebuild_evidence_embeddings(
    session: AsyncSession,
    provider: EmbeddingProvider,
    *,
    batch_size: int = 32,
    force: bool = False,
    store: ChromaEvidenceStore,
) -> int:
    rows = (
        await session.execute(
            select(ProfileEvidence, ProfileSource)
            .join(ProfileSource, ProfileSource.id == ProfileEvidence.profile_source_id)
        )
    ).all()
    updated = 0
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        texts = [
            build_evidence_embedding_text(
                label=evidence.label,
                evidence_text=evidence.evidence_text,
                source_name=source.name,
            )
            for evidence, source in batch
        ]
        vectors = provider.embed_batch(texts)
        for (evidence_source, vector, text) in zip(batch, vectors, texts, strict=True):
            evidence, source = evidence_source
            profile_id = (source.source_metadata or {}).get("profile_id")
            if not profile_id:
                continue
            store.upsert(evidence_id=str(evidence.id), profile_id=str(profile_id), embedding=vector, document=text, model=provider.model)
            updated += 1
    await session.commit()
    return updated
