"""Async SQLAlchemy repository for Knowledge Graph entities, relationships, and traversal."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import KgEntity, KgRelationship
from app.schemas.common import EntityTypeEnum, RelationTypeEnum
from app.schemas.kg import SubgraphEdgeRow


def normalize_lookup_key(name: str) -> str:
    """Normalize an entity name into a deterministic lowercase lookup_key (FR-14)."""
    return " ".join(name.lower().strip().split())


class KnowledgeGraphRepository:
    """Data access layer for Table 4 (kg_entities) and Table 5 (kg_relationships)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _find_matching_entity(
        self,
        lookup_key: str,
        entity_type: EntityTypeEnum,
        embedding: list[float],
    ) -> KgEntity | None:
        """Resolve an existing entity by exact lookup_key or >= 0.92 vector similarity."""
        exact_stmt = select(KgEntity).where(KgEntity.lookup_key == lookup_key)
        exact_match = (await self._session.execute(exact_stmt)).scalar_one_or_none()
        if exact_match is not None:
            return exact_match

        distance_expr = KgEntity.embedding.cosine_distance(embedding)
        sim_stmt = (
            select(KgEntity)
            .where(
                KgEntity.entity_type == entity_type.value,
                (1.0 - distance_expr) >= 0.92,
            )
            .order_by(distance_expr.asc())
            .limit(1)
        )
        return (await self._session.execute(sim_stmt)).scalar_one_or_none()

    async def upsert_entity(
        self,
        canonical_name: str,
        entity_type: EntityTypeEnum,
        aliases: list[str],
        description: str,
        embedding: list[float],
        source_chunk_id: UUID,
        source_document_id: UUID,
    ) -> KgEntity:
        """Idempotently resolve or insert a canonical Knowledge Graph entity (FR-14)."""
        clean_name = " ".join(canonical_name.split())
        lookup_key = normalize_lookup_key(clean_name)
        existing = await self._find_matching_entity(lookup_key, entity_type, embedding)

        if existing is not None:
            merged_aliases = list(dict.fromkeys([*existing.aliases, clean_name, *aliases]))
            existing.aliases = [a for a in merged_aliases if a and a != existing.canonical_name]
            if len(description.strip()) > len(existing.description):
                existing.description = description.strip()
            if source_chunk_id not in existing.source_chunk_ids:
                existing.source_chunk_ids = [*existing.source_chunk_ids, source_chunk_id]
            if source_document_id not in existing.source_document_ids:
                existing.source_document_ids = [*existing.source_document_ids, source_document_id]
            existing.updated_at = datetime.now(UTC)
            await self._session.flush()
            return existing

        dedup_aliases = [
            a.strip()
            for a in dict.fromkeys(aliases)
            if a.strip() and a.strip() != clean_name
        ]
        entity = KgEntity(
            canonical_name=clean_name,
            lookup_key=lookup_key,
            entity_type=entity_type.value,
            aliases=dedup_aliases,
            description=description.strip(),
            embedding=embedding,
            source_chunk_ids=[source_chunk_id],
            source_document_ids=[source_document_id],
        )
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def upsert_relationship(
        self,
        source_entity_id: UUID,
        target_entity_id: UUID,
        relation_type: RelationTypeEnum,
        evidence_snippet: str,
        confidence: float,
        source_chunk_id: UUID,
        document_id: UUID,
    ) -> KgRelationship:
        """Idempotently insert or update a directed Knowledge Graph relationship triple."""
        snippet = evidence_snippet.strip()[:500]
        conf_dec = Decimal(f"{min(max(confidence, 0.0), 1.0):.2f}")

        stmt = select(KgRelationship).where(
            KgRelationship.source_entity_id == source_entity_id,
            KgRelationship.target_entity_id == target_entity_id,
            KgRelationship.relation_type == relation_type.value,
            KgRelationship.source_chunk_id == source_chunk_id,
        )
        existing = (await self._session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            if conf_dec > existing.confidence:
                existing.confidence = conf_dec
            existing.evidence_snippet = snippet
            await self._session.flush()
            return existing

        edge = KgRelationship(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type.value,
            evidence_snippet=snippet,
            confidence=conf_dec,
            source_chunk_id=source_chunk_id,
            document_id=document_id,
        )
        self._session.add(edge)
        await self._session.flush()
        return edge

    async def get_entity_by_id(self, entity_id: UUID) -> KgEntity | None:
        """Fetch a canonical KG entity by primary key."""
        stmt = select(KgEntity).where(KgEntity.entity_id == entity_id)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_entities_by_ids(self, entity_ids: list[UUID]) -> list[KgEntity]:
        """Fetch all canonical KG entities matching the provided UUIDs."""
        if not entity_ids:
            return []
        stmt = select(KgEntity).where(KgEntity.entity_id.in_(entity_ids)).order_by(
            KgEntity.canonical_name.asc()
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def count_entity_degree(self, entity_id: UUID) -> int:
        """Count total incident (incoming + outgoing) relationships for an entity."""
        stmt = select(func.count(KgRelationship.edge_id)).where(
            or_(
                KgRelationship.source_entity_id == entity_id,
                KgRelationship.target_entity_id == entity_id,
            )
        )
        return int((await self._session.scalar(stmt)) or 0)

    async def list_entities(
        self,
        search: str | None = None,
        entity_type: EntityTypeEnum | None = None,
        document_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[tuple[KgEntity, int]], int]:
        """Search and filter KG entities with degree counts and bounded pagination."""
        clamped_limit = min(max(limit, 1), 100)
        clamped_offset = max(offset, 0)

        base_stmt = select(KgEntity)
        count_stmt = select(func.count(KgEntity.entity_id))

        if entity_type is not None:
            base_stmt = base_stmt.where(KgEntity.entity_type == entity_type.value)
            count_stmt = count_stmt.where(KgEntity.entity_type == entity_type.value)

        if document_id is not None:
            doc_cond = KgEntity.source_document_ids.contains([document_id])
            base_stmt = base_stmt.where(doc_cond)
            count_stmt = count_stmt.where(doc_cond)

        if search is not None and search.strip():
            q = f"%{search.strip()}%"
            search_cond = or_(
                KgEntity.canonical_name.ilike(q),
                KgEntity.description.ilike(q),
            )
            base_stmt = base_stmt.where(search_cond)
            count_stmt = count_stmt.where(search_cond)

        total_count = int((await self._session.scalar(count_stmt)) or 0)
        stmt = (
            base_stmt.order_by(KgEntity.canonical_name.asc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        entities = list((await self._session.execute(stmt)).scalars().all())

        results: list[tuple[KgEntity, int]] = []
        for ent in entities:
            deg = await self.count_entity_degree(ent.entity_id)
            results.append((ent, deg))
        return results, total_count

    async def resolve_candidate_entities(
        self,
        candidate_names: list[str],
        query_embedding: list[float] | None = None,
        limit: int = 10,
    ) -> list[KgEntity]:
        """Resolve query entity mentions via lookup_key/substring match and vector similarity."""
        clamped_limit = min(max(limit, 1), 25)
        matched: dict[UUID, KgEntity] = {}

        cleaned_keys = [normalize_lookup_key(n) for n in candidate_names if n.strip()]
        if cleaned_keys:
            like_clauses = [KgEntity.canonical_name.ilike(f"%{k}%") for k in cleaned_keys]
            name_stmt = (
                select(KgEntity)
                .where(or_(KgEntity.lookup_key.in_(cleaned_keys), *like_clauses))
                .limit(clamped_limit)
            )
            for ent in (await self._session.execute(name_stmt)).scalars().all():
                matched[ent.entity_id] = ent

        if query_embedding is not None and len(matched) < clamped_limit:
            distance_expr = KgEntity.embedding.cosine_distance(query_embedding)
            vec_stmt = (
                select(KgEntity)
                .where((1.0 - distance_expr) >= 0.55)
                .order_by(distance_expr.asc())
                .limit(clamped_limit)
            )
            for ent in (await self._session.execute(vec_stmt)).scalars().all():
                matched.setdefault(ent.entity_id, ent)

        return list(matched.values())[:clamped_limit]

    async def traverse_subgraph(
        self,
        seed_entity_ids: list[UUID],
        max_hops: int = 2,
    ) -> list[SubgraphEdgeRow]:
        """Execute the PostgreSQL traverse_kg_subgraph recursive CTE with cycle prevention."""
        if not seed_entity_ids:
            return []

        clamped_hops = min(max(max_hops, 1), 3)
        sql = text(
            """
            SELECT
                edge_id,
                source_entity_id,
                target_entity_id,
                relation_type,
                evidence_snippet,
                confidence,
                source_chunk_id,
                document_id,
                hop_depth
            FROM traverse_kg_subgraph(:seed_ids, :max_hops)
            """
        )
        result = await self._session.execute(
            sql,
            {"seed_ids": seed_entity_ids, "max_hops": clamped_hops},
        )
        edges: list[SubgraphEdgeRow] = []
        for row in result.mappings().all():
            edges.append(
                SubgraphEdgeRow(
                    edge_id=UUID(str(row["edge_id"])),
                    source_entity_id=UUID(str(row["source_entity_id"])),
                    target_entity_id=UUID(str(row["target_entity_id"])),
                    relation_type=RelationTypeEnum(str(row["relation_type"])),
                    evidence_snippet=str(row["evidence_snippet"]),
                    confidence=float(row["confidence"]),
                    source_chunk_id=UUID(str(row["source_chunk_id"])),
                    document_id=UUID(str(row["document_id"])),
                    hop_depth=int(row["hop_depth"]),
                )
            )
        return edges
