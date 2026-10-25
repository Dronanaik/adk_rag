"""Canonical Reciprocal Rank Fusion (RRF) scoring and hybrid chunk retrieval service."""

from dataclasses import dataclass
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import DocumentChunk
from app.repositories.document_repo import DocumentRepository
from app.schemas.common import EntityTypeEnum
from app.schemas.documents import ExtractedEntityRef
from app.services.gemini_service import GeminiService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Fused candidate result from dense vector search and PostgreSQL FTS."""

    item_id: str
    rrf_score: float
    vector_rank: int | None = None
    fts_rank: int | None = None


@dataclass(frozen=True, slots=True)
class HybridChunkMatch:
    """Hydrated chunk result from hybrid vector + full-text search."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int
    content: str
    vector_similarity: float
    rrf_score: float
    page_number: int | None
    section_heading: str | None
    extracted_entities: list[ExtractedEntityRef]


def compute_reciprocal_rank_fusion(
    vector_ordered_ids: list[str],
    fts_ordered_ids: list[str],
    k_constant: int = 60,
    top_k: int = 8,
) -> list[RankedCandidate]:
    """Fuse dense vector and full-text search rankings using RRF (k=60)."""
    if k_constant <= 0:
        raise ValueError("k_constant must be positive")
    if top_k <= 0:
        return []

    vector_ranks = {item_id: idx + 1 for idx, item_id in enumerate(vector_ordered_ids)}
    fts_ranks = {item_id: idx + 1 for idx, item_id in enumerate(fts_ordered_ids)}

    all_ids: list[str] = list(dict.fromkeys([*vector_ordered_ids, *fts_ordered_ids]))
    fused: list[RankedCandidate] = []

    for item_id in all_ids:
        v_rank = vector_ranks.get(item_id)
        f_rank = fts_ranks.get(item_id)
        score = 0.0
        if v_rank is not None:
            score += 1.0 / (k_constant + v_rank)
        if f_rank is not None:
            score += 1.0 / (k_constant + f_rank)
        fused.append(
            RankedCandidate(
                item_id=item_id,
                rrf_score=round(score, 6),
                vector_rank=v_rank,
                fts_rank=f_rank,
            )
        )

    fused.sort(key=lambda candidate: candidate.rrf_score, reverse=True)
    return fused[:top_k]


def _extract_chunk_metadata_fields(
    chunk: DocumentChunk,
) -> tuple[int | None, str | None, list[ExtractedEntityRef]]:
    """Parse optional page_number, section_heading, and extracted_entities from chunk_metadata."""
    raw_meta = chunk.chunk_metadata or {}
    raw_page = raw_meta.get("page_number")
    page_number = int(raw_page) if isinstance(raw_page, int) else None

    raw_section = raw_meta.get("section_heading")
    section_heading = str(raw_section) if isinstance(raw_section, str) and raw_section else None

    extracted_entities: list[ExtractedEntityRef] = []
    raw_entities = raw_meta.get("extracted_entities")
    if isinstance(raw_entities, list):
        for item in raw_entities:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("entity_id")
            raw_name = item.get("canonical_name")
            raw_type = item.get("entity_type")
            if not (
                isinstance(raw_id, str)
                and isinstance(raw_name, str)
                and isinstance(raw_type, str)
            ):
                continue
            try:
                extracted_entities.append(
                    ExtractedEntityRef(
                        entity_id=UUID(raw_id),
                        canonical_name=raw_name,
                        entity_type=EntityTypeEnum(raw_type),
                    )
                )
            except ValueError:
                continue

    return page_number, section_heading, extracted_entities


class HybridSearchService:
    """Executes hybrid dense vector + PostgreSQL full-text chunk retrieval with RRF fusion."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        gemini_service: GeminiService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._gemini = gemini_service or GeminiService(self._settings)
        self._doc_repo = DocumentRepository(session)

    async def search_chunks(
        self,
        *,
        query_text: str,
        top_k: int = 5,
        min_similarity: float = 0.65,
    ) -> list[HybridChunkMatch]:
        """Search indexed document chunks combining pgvector cosine similarity and FTS with RRF."""
        cleaned_query = query_text.strip()
        if not cleaned_query:
            return []

        clamped_k = min(max(top_k, 1), 20)
        query_embedding = await self._gemini.embed_query(cleaned_query)

        vector_rows = await self._doc_repo.search_chunks_by_vector(
            query_embedding=query_embedding,
            top_k=clamped_k * 2,
            min_similarity=min_similarity,
        )

        try:
            fts_rows = await self._doc_repo.search_chunks_by_keyword(
                query_text=cleaned_query,
                top_k=clamped_k * 2,
            )
        except Exception as exc:
            logger.warning("hybrid_search_fts_degraded", error=str(exc))
            fts_rows = []

        chunk_by_id: dict[str, tuple[DocumentChunk, str, float]] = {}
        vector_ids: list[str] = []
        for chunk, doc_title, similarity in vector_rows:
            cid = str(chunk.chunk_id)
            vector_ids.append(cid)
            chunk_by_id[cid] = (chunk, doc_title, similarity)

        fts_ids: list[str] = []
        for chunk, doc_title, _fts_rank in fts_rows:
            cid = str(chunk.chunk_id)
            fts_ids.append(cid)
            if cid not in chunk_by_id:
                chunk_by_id[cid] = (chunk, doc_title, max(min_similarity, 0.65))

        fused_candidates = compute_reciprocal_rank_fusion(
            vector_ordered_ids=vector_ids,
            fts_ordered_ids=fts_ids,
            k_constant=60,
            top_k=clamped_k,
        )

        matches: list[HybridChunkMatch] = []
        for candidate in fused_candidates:
            record = chunk_by_id.get(candidate.item_id)
            if record is None:
                continue
            chunk, doc_title, similarity = record
            page_num, section_heading, entities = _extract_chunk_metadata_fields(chunk)
            matches.append(
                HybridChunkMatch(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_title=doc_title,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    vector_similarity=round(min(max(similarity, 0.0), 1.0), 4),
                    rrf_score=candidate.rrf_score,
                    page_number=page_num,
                    section_heading=section_heading,
                    extracted_entities=entities,
                )
            )
        return matches
