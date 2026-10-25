"""Async SQLAlchemy repository for Three-Tier Centralized Memory and curation (D-04)."""

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.entities import MemoryEntry
from app.schemas.common import MemoryTierEnum


class MemoryRepository:
    """Data access layer for Table 8 (memory_entries)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, memory_id: UUID) -> MemoryEntry | None:
        """Fetch a single memory entry by primary key UUID."""
        stmt = select(MemoryEntry).where(MemoryEntry.memory_id == memory_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_ids(self, memory_ids: list[UUID]) -> list[MemoryEntry]:
        """Fetch multiple memory entries by UUID list."""
        if not memory_ids:
            return []
        stmt = select(MemoryEntry).where(MemoryEntry.memory_id.in_(memory_ids)).order_by(
            MemoryEntry.created_at.desc()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_memories(
        self,
        memory_tier: MemoryTierEnum | None = None,
        session_id: UUID | None = None,
        include_superseded: bool = False,
        search: str | None = None,
        query_embedding: list[float] | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[tuple[MemoryEntry, float | None]], int]:
        """Search and filter Centralized Memory entries with bounded pagination."""
        clamped_limit = min(max(limit, 1), 100)
        clamped_offset = max(offset, 0)

        filters: list[ColumnElement[bool]] = []
        if not include_superseded:
            filters.append(MemoryEntry.superseded_by_id.is_(None))
        if memory_tier is not None:
            filters.append(MemoryEntry.memory_tier == memory_tier.value)
        if session_id is not None:
            filters.append(MemoryEntry.session_id == session_id)
        if search is not None and search.strip() and query_embedding is None:
            filters.append(MemoryEntry.content.ilike(f"%{search.strip()}%"))

        count_stmt = select(func.count(MemoryEntry.memory_id)).where(*filters)
        total_count = int((await self._session.scalar(count_stmt)) or 0)

        if query_embedding is not None:
            dist = MemoryEntry.embedding.cosine_distance(query_embedding)
            sim = (1.0 - dist).label("similarity")
            vec_stmt = (
                select(MemoryEntry, sim)
                .where(*filters)
                .order_by(dist.asc(), MemoryEntry.created_at.desc())
                .limit(clamped_limit)
                .offset(clamped_offset)
            )
            vec_rows = (await self._session.execute(vec_stmt)).all()
            return [(row[0], float(row[1])) for row in vec_rows], total_count

        stmt = (
            select(MemoryEntry)
            .where(*filters)
            .order_by(MemoryEntry.created_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        entries = list((await self._session.execute(stmt)).scalars().all())
        return [(entry, None) for entry in entries], total_count

    async def recall_memories(
        self,
        query_embedding: list[float],
        session_id: UUID,
        include_shared: bool = True,
        min_similarity: float = 0.55,
        top_k: int = 5,
    ) -> list[tuple[MemoryEntry, float]]:
        """Recall active session and optional shared long-term memories by vector similarity."""
        clamped_k = min(max(top_k, 1), 20)
        dist = MemoryEntry.embedding.cosine_distance(query_embedding)
        sim_expr = (1.0 - dist).label("similarity")

        scope_filter = (
            or_(
                MemoryEntry.session_id == session_id,
                MemoryEntry.memory_tier.in_(
                    [
                        MemoryTierEnum.LONG_TERM_SEMANTIC.value,
                        MemoryTierEnum.LONG_TERM_EPISODIC.value,
                    ]
                ),
            )
            if include_shared
            else (MemoryEntry.session_id == session_id)
        )

        stmt = (
            select(MemoryEntry, sim_expr)
            .where(
                MemoryEntry.superseded_by_id.is_(None),
                scope_filter,
                (1.0 - dist) >= min_similarity,
            )
            .order_by(dist.asc())
            .limit(clamped_k)
        )
        rows = (await self._session.execute(stmt)).all()
        return [(row[0], float(row[1])) for row in rows]

    async def create_verified_memory(
        self,
        memory_tier: MemoryTierEnum,
        content: str,
        embedding: list[float],
        session_id: UUID | None,
        source_turn_id: UUID | None,
        supporting_chunk_ids: list[UUID],
        related_entity_ids: list[UUID],
        supersedes_memory_ids: list[UUID] | None = None,
    ) -> tuple[MemoryEntry, list[UUID], bool]:
        """Consolidate a verified fact into memory_entries with deduplication (D-04 & FR-09)."""
        if (
            memory_tier
            in (
                MemoryTierEnum.LONG_TERM_SEMANTIC,
                MemoryTierEnum.LONG_TERM_EPISODIC,
            )
            and not supporting_chunk_ids
            and source_turn_id is None
        ):
            raise ValueError(
                "Decision D-04 violation: Long-term shared memory requires verified provenance."
            )

        dist = MemoryEntry.embedding.cosine_distance(embedding)
        dup_stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.superseded_by_id.is_(None),
                MemoryEntry.memory_tier == memory_tier.value,
                (1.0 - dist) >= 0.94,
            )
            .order_by(dist.asc())
            .limit(1)
        )
        near_dup = (await self._session.execute(dup_stmt)).scalar_one_or_none()
        if near_dup is not None:
            return near_dup, [], True

        entry = MemoryEntry(
            memory_tier=memory_tier.value,
            session_id=session_id,
            content=content.strip(),
            embedding=embedding,
            related_entity_ids=list(dict.fromkeys(related_entity_ids)),
            source_turn_id=source_turn_id,
            supporting_chunk_ids=list(dict.fromkeys(supporting_chunk_ids)),
        )
        self._session.add(entry)
        await self._session.flush()

        superseded = list(dict.fromkeys(supersedes_memory_ids or []))
        if superseded:
            await self._session.execute(
                update(MemoryEntry)
                .where(
                    MemoryEntry.memory_id.in_(superseded),
                    MemoryEntry.memory_id != entry.memory_id,
                )
                .values(superseded_by_id=entry.memory_id)
            )
        await self._session.flush()
        return entry, superseded, False

    async def delete_memory(self, memory_id: UUID) -> MemoryEntry | None:
        """Delete a memory entry by ID and return the deleted record, or None if not found."""
        entry = await self.get_by_id(memory_id)
        if entry is None:
            return None
        await self._session.delete(entry)
        await self._session.commit()
        return entry
