"""Centralized Memory curation, recall, and Decision D-04 verified consolidation service."""

import secrets
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.entities import MemoryEntry
from app.repositories.document_repo import DocumentRepository
from app.repositories.kg_repo import KnowledgeGraphRepository
from app.repositories.memory_repo import MemoryRepository
from app.schemas.common import (
    APIException,
    GroundingStatusEnum,
    MemoryTierEnum,
    OffsetPaginationMeta,
    RoleEnum,
)
from app.schemas.memory import (
    MemoryConsolidationResult,
    MemoryDeleteResponse,
    MemoryEntryItem,
    MemoryListResponse,
    VerifiedFactCandidate,
)
from app.services.gemini_service import GeminiService

logger = structlog.get_logger(__name__)

LONG_TERM_TIERS: frozenset[str] = frozenset(
    {
        MemoryTierEnum.LONG_TERM_SEMANTIC.value,
        MemoryTierEnum.LONG_TERM_EPISODIC.value,
    }
)


def _verify_admin_api_key(settings: Settings, provided_key: str | None) -> None:
    """Verify X-Admin-Api-Key using constant-time comparison (Decision D-05)."""
    configured_key = settings.ADMIN_API_KEY.strip()
    if not configured_key:
        return

    candidate = (provided_key or "").strip()
    if not candidate or not secrets.compare_digest(
        candidate.encode("utf-8"),
        configured_key.encode("utf-8"),
    ):
        raise APIException(
            status_code=403,
            code="FORBIDDEN_ADMIN_REQUIRED",
            message="Missing or invalid X-Admin-Api-Key header for Knowledge Admin action.",
        )


class MemoryService:
    """Orchestrates three-tier Centralized Memory search, curation, and D-04 consolidation."""

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
        self._memory_repo = MemoryRepository(session)
        self._kg_repo = KnowledgeGraphRepository(session)
        self._doc_repo = DocumentRepository(session)

    async def hydrate_memory_entries(
        self,
        rows: list[tuple[MemoryEntry, float | None]],
    ) -> list[MemoryEntryItem]:
        """Batch-resolve entity names and document titles for a list of MemoryEntry rows."""
        if not rows:
            return []

        all_entity_ids: list[UUID] = []
        all_chunk_ids: list[UUID] = []
        for entry, _score in rows:
            all_entity_ids.extend(entry.related_entity_ids or [])
            all_chunk_ids.extend(entry.supporting_chunk_ids or [])

        unique_entity_ids = list(dict.fromkeys(all_entity_ids))
        unique_chunk_ids = list(dict.fromkeys(all_chunk_ids))

        entities = await self._kg_repo.get_entities_by_ids(unique_entity_ids)
        entity_name_by_id = {ent.entity_id: ent.canonical_name for ent in entities}

        chunks_with_titles = await self._doc_repo.get_chunks_by_ids(unique_chunk_ids)
        doc_title_by_chunk_id = {
            chunk.chunk_id: doc_title for chunk, doc_title in chunks_with_titles
        }

        items: list[MemoryEntryItem] = []
        for entry, similarity in rows:
            entity_names = [
                entity_name_by_id[eid]
                for eid in (entry.related_entity_ids or [])
                if eid in entity_name_by_id
            ]
            doc_titles = list(
                dict.fromkeys(
                    doc_title_by_chunk_id[cid]
                    for cid in (entry.supporting_chunk_ids or [])
                    if cid in doc_title_by_chunk_id
                )
            )
            items.append(
                MemoryEntryItem(
                    memory_id=entry.memory_id,
                    memory_tier=MemoryTierEnum(entry.memory_tier),
                    session_id=entry.session_id,
                    content=entry.content,
                    related_entity_ids=list(entry.related_entity_ids or []),
                    related_entity_names=entity_names,
                    source_turn_id=entry.source_turn_id,
                    supporting_chunk_ids=list(entry.supporting_chunk_ids or []),
                    supporting_document_titles=doc_titles,
                    superseded_by_id=entry.superseded_by_id,
                    similarity_score=(
                        round(similarity, 4) if similarity is not None else None
                    ),
                    created_at=entry.created_at,
                )
            )
        return items

    async def list_memories(
        self,
        *,
        memory_tier: MemoryTierEnum | None = None,
        session_id: UUID | None = None,
        include_superseded: bool = False,
        search: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> MemoryListResponse:
        """List and filter Centralized Memory entries with hydrated entity and document names."""
        rows, total = await self._memory_repo.list_memories(
            memory_tier=memory_tier,
            session_id=session_id,
            include_superseded=include_superseded,
            search=search,
            query_embedding=None,
            limit=limit,
            offset=offset,
        )
        items = await self.hydrate_memory_entries(rows)
        return MemoryListResponse(
            items=items,
            pagination=OffsetPaginationMeta.create(total=total, limit=limit, offset=offset),
        )

    async def recall_for_turn(
        self,
        *,
        query_text: str,
        session_id: UUID,
        include_shared: bool = True,
        min_similarity: float = 0.55,
        top_k: int = 5,
    ) -> list[MemoryEntryItem]:
        """Recall active session and optional shared long-term memories by vector similarity."""
        query_embedding = await self._gemini.embed_query(query_text)
        recalled_rows = await self._memory_repo.recall_memories(
            query_embedding=query_embedding,
            session_id=session_id,
            include_shared=include_shared,
            min_similarity=min_similarity,
            top_k=top_k,
        )
        rows_with_optional: list[tuple[MemoryEntry, float | None]] = [
            (entry, score) for entry, score in recalled_rows
        ]
        return await self.hydrate_memory_entries(rows_with_optional)

    async def consolidate_verified_facts(
        self,
        *,
        candidates: list[VerifiedFactCandidate],
        grounding_status: GroundingStatusEnum,
        session_id: UUID | None = None,
        source_turn_id: UUID | None = None,
    ) -> MemoryConsolidationResult:
        """Consolidate verified facts into Centralized Memory enforcing Decision D-04."""
        if not candidates:
            return MemoryConsolidationResult()

        has_long_term = any(cand.memory_tier.value in LONG_TERM_TIERS for cand in candidates)
        if has_long_term and grounding_status != GroundingStatusEnum.GROUNDED:
            raise APIException(
                status_code=400,
                code="UNVERIFIED_MEMORY_CONSOLIDATION",
                message=(
                    "Decision D-04 violation: Shared long-term memories can only be consolidated "
                    "when SynthesisVerifier confirms grounding_status == 'GROUNDED'."
                ),
                details={"grounding_status": grounding_status.value},
            )

        embeddings = await self._gemini.embed_texts([cand.content for cand in candidates])
        created_ids: list[UUID] = []
        superseded_ids: list[UUID] = []
        skipped_duplicates = 0

        for candidate, vector in zip(candidates, embeddings, strict=True):
            entry, newly_superseded, is_duplicate = await self._memory_repo.create_verified_memory(
                memory_tier=candidate.memory_tier,
                content=candidate.content,
                embedding=vector,
                session_id=session_id if candidate.memory_tier == MemoryTierEnum.SESSION else None,
                source_turn_id=source_turn_id,
                supporting_chunk_ids=candidate.supporting_chunk_ids,
                related_entity_ids=candidate.related_entity_ids,
                supersedes_memory_ids=candidate.supersedes_memory_ids,
            )
            if is_duplicate:
                skipped_duplicates += 1
            else:
                created_ids.append(entry.memory_id)
                superseded_ids.extend(newly_superseded)

        await self._session.commit()
        return MemoryConsolidationResult(
            created_memory_ids=created_ids,
            superseded_memory_ids=list(dict.fromkeys(superseded_ids)),
            skipped_duplicate_count=skipped_duplicates,
        )

    async def update_memory(
        self,
        *,
        memory_id: UUID,
        content: str,
    ) -> MemoryEntryItem:
        """Update a memory entry's content and re-compute its 768-dim embedding (Admin Only)."""
        existing = await self._memory_repo.get_by_id(memory_id)
        if existing is None:
            raise APIException(
                status_code=404,
                code="MEMORY_NOT_FOUND",
                message=f"Memory entry '{memory_id}' was not found.",
                details={"memory_id": str(memory_id)},
            )

        embedding = await self._gemini.embed_query(content)
        updated = await self._memory_repo.update_memory_content(
            memory_id=memory_id,
            content=content,
            embedding=embedding,
        )
        if updated is None:
            raise APIException(
                status_code=404,
                code="MEMORY_NOT_FOUND",
                message=f"Memory entry '{memory_id}' was not found.",
                details={"memory_id": str(memory_id)},
            )
        hydrated = await self.hydrate_memory_entries([(updated, None)])
        return hydrated[0]

    async def delete_memory_authorized(
        self,
        *,
        memory_id: UUID,
        role: RoleEnum,
        admin_api_key: str | None = None,
    ) -> MemoryDeleteResponse:
        """Delete a memory entry enforcing tier-scoped RBAC rules (API.md Section 2.2 & 3.4)."""
        entry = await self._memory_repo.get_by_id(memory_id)
        if entry is None:
            raise APIException(
                status_code=404,
                code="MEMORY_NOT_FOUND",
                message=f"Memory entry '{memory_id}' was not found.",
                details={"memory_id": str(memory_id)},
            )

        tier = MemoryTierEnum(entry.memory_tier)
        if tier.value in LONG_TERM_TIERS and role != RoleEnum.ADMIN:
            raise APIException(
                status_code=403,
                code="MEMORY_SCOPE_FORBIDDEN",
                message=(
                    "Researcher role can only delete SESSION-scoped memories. "
                    "Deleting shared LONG_TERM memories requires Knowledge Admin role."
                ),
                details={"memory_id": str(memory_id), "memory_tier": tier.value},
            )

        if role == RoleEnum.ADMIN:
            _verify_admin_api_key(self._settings, admin_api_key)

        await self._memory_repo.delete_memory(memory_id)
        return MemoryDeleteResponse(deleted_memory_id=memory_id, memory_tier=tier)

