"""Knowledge Graph Explorer service for entity search and 1-2 hop subgraph inspection."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import KgEntity
from app.repositories.document_repo import DocumentRepository
from app.repositories.kg_repo import KnowledgeGraphRepository
from app.schemas.common import APIException, EntityTypeEnum, OffsetPaginationMeta
from app.schemas.kg import (
    KgEntityListResponse,
    KgEntitySummary,
    KgRelationshipItem,
    KgSubgraphResponse,
    SubgraphEdgeRow,
    SubgraphSupportingChunk,
)

MAX_SUBGRAPH_CONNECTED_NODES: int = 50


def to_kg_entity_summary(entity: KgEntity, *, degree_count: int = 0) -> KgEntitySummary:
    """Convert a SQLAlchemy KgEntity ORM row into a validated KgEntitySummary DTO."""
    return KgEntitySummary(
        entity_id=entity.entity_id,
        canonical_name=entity.canonical_name,
        lookup_key=entity.lookup_key,
        entity_type=EntityTypeEnum(entity.entity_type),
        aliases=list(entity.aliases or []),
        description=entity.description or "",
        source_chunk_ids=list(entity.source_chunk_ids or []),
        source_document_ids=list(entity.source_document_ids or []),
        degree_count=max(degree_count, 0),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _select_top_connected_node_ids(
    center_entity_id: UUID,
    edge_rows: list[SubgraphEdgeRow],
    max_connected_nodes: int = MAX_SUBGRAPH_CONNECTED_NODES,
) -> set[UUID]:
    """Select up to max_connected_nodes highest-confidence connected entity UUIDs (API.md 3.3)."""
    best_confidence_by_node: dict[UUID, float] = {}
    min_hop_by_node: dict[UUID, int] = {}

    for edge in edge_rows:
        for endpoint_id in (edge.source_entity_id, edge.target_entity_id):
            if endpoint_id == center_entity_id:
                continue
            prev_conf = best_confidence_by_node.get(endpoint_id, -1.0)
            if edge.confidence > prev_conf:
                best_confidence_by_node[endpoint_id] = edge.confidence
            prev_hop = min_hop_by_node.get(endpoint_id, 99)
            if edge.hop_depth < prev_hop:
                min_hop_by_node[endpoint_id] = edge.hop_depth

    ranked_node_ids = sorted(
        best_confidence_by_node.keys(),
        key=lambda nid: (min_hop_by_node.get(nid, 99), -best_confidence_by_node[nid], str(nid)),
    )
    return set(ranked_node_ids[:max_connected_nodes])


class KnowledgeGraphExplorerService:
    """Coordinates Knowledge Graph entity search and bounded 1-2 hop subgraph inspection."""

    def __init__(self, session: AsyncSession) -> None:
        self._kg_repo = KnowledgeGraphRepository(session)
        self._doc_repo = DocumentRepository(session)

    async def list_entities(
        self,
        *,
        search: str | None = None,
        entity_type: EntityTypeEnum | None = None,
        document_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> KgEntityListResponse:
        """Search and filter canonical KG entities with degree counts and offset pagination."""
        rows, total = await self._kg_repo.list_entities(
            search=search,
            entity_type=entity_type,
            document_id=document_id,
            limit=limit,
            offset=offset,
        )
        items = [
            to_kg_entity_summary(entity, degree_count=degree)
            for entity, degree in rows
        ]
        return KgEntityListResponse(
            items=items,
            pagination=OffsetPaginationMeta.create(total=total, limit=limit, offset=offset),
        )

    async def _hydrate_subgraph_chunks(
        self,
        edges: list[SubgraphEdgeRow],
    ) -> list[SubgraphSupportingChunk]:
        """Fetch verbatim backing DocumentChunk rows referenced by subgraph edges."""
        supporting_chunk_ids = list(dict.fromkeys(edge.source_chunk_id for edge in edges))
        chunks_with_titles = await self._doc_repo.get_chunks_by_ids(supporting_chunk_ids)
        return [
            SubgraphSupportingChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=doc_title,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
            )
            for chunk, doc_title in chunks_with_titles
        ]

    async def get_entity_subgraph(
        self,
        *,
        entity_id: UUID,
        hops: int = 1,
    ) -> KgSubgraphResponse:
        """Execute 1-2 hop KG traversal around entity_id and hydrate backing document chunks."""
        center_row = await self._kg_repo.get_entity_by_id(entity_id)
        if center_row is None:
            raise APIException(
                status_code=404,
                code="ENTITY_NOT_FOUND",
                message=f"Knowledge Graph entity '{entity_id}' was not found.",
                details={"entity_id": str(entity_id)},
            )

        clamped_hops = min(max(hops, 1), 2)
        center_degree = await self._kg_repo.count_entity_degree(entity_id)
        center_summary = to_kg_entity_summary(center_row, degree_count=center_degree)

        raw_edges = await self._kg_repo.traverse_subgraph(
            seed_entity_ids=[entity_id],
            max_hops=clamped_hops,
        )
        selected_connected_ids = _select_top_connected_node_ids(entity_id, raw_edges)
        allowed_node_ids = {entity_id, *selected_connected_ids}

        filtered_edges = [
            edge
            for edge in raw_edges
            if edge.source_entity_id in allowed_node_ids
            and edge.target_entity_id in allowed_node_ids
        ]

        connected_entities = await self._kg_repo.get_entities_by_ids(list(selected_connected_ids))
        node_summaries: list[KgEntitySummary] = []
        for ent in connected_entities:
            deg = await self._kg_repo.count_entity_degree(ent.entity_id)
            node_summaries.append(to_kg_entity_summary(ent, degree_count=deg))

        edge_items = [
            KgRelationshipItem(
                edge_id=edge.edge_id,
                source_entity_id=edge.source_entity_id,
                target_entity_id=edge.target_entity_id,
                relation_type=edge.relation_type,
                evidence_snippet=edge.evidence_snippet,
                confidence=edge.confidence,
                source_chunk_id=edge.source_chunk_id,
                document_id=edge.document_id,
                hop_depth=edge.hop_depth,
            )
            for edge in filtered_edges
        ]
        supporting_chunks = await self._hydrate_subgraph_chunks(filtered_edges)

        return KgSubgraphResponse(
            center_entity=center_summary,
            nodes=node_summaries,
            edges=edge_items,
            supporting_chunks=supporting_chunks,
        )
