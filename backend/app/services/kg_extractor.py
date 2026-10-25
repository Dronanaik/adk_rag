"""Schema-guided Knowledge Graph entity and relationship extraction service (Decision D-03)."""

from dataclasses import dataclass
from uuid import UUID

import structlog

from app.models.entities import DocumentChunk, KgEntity
from app.repositories.kg_repo import KnowledgeGraphRepository, normalize_lookup_key
from app.schemas.common import EntityTypeEnum, RelationTypeEnum
from app.schemas.documents import ExtractedEntityRef, ExtractedRelationshipRef
from app.schemas.kg import (
    ChunkKgExtractionResult,
    ExtractedEntityCandidate,
    ExtractedRelationshipCandidate,
)
from app.services.gemini_service import GeminiService

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DocumentKgExtractionStats:
    """Summary counts of unique entities and relationships extracted for a document."""

    entity_count: int
    relation_count: int


class KnowledgeGraphExtractionService:
    """Orchestrates per-chunk Gemini KG extraction, entity resolution, and provenance linking."""

    def __init__(
        self,
        kg_repo: KnowledgeGraphRepository,
        gemini_service: GeminiService,
    ) -> None:
        self._kg_repo = kg_repo
        self._gemini = gemini_service

    async def extract_and_persist_for_chunks(
        self,
        *,
        document_id: UUID,
        document_title: str,
        chunks: list[DocumentChunk],
    ) -> DocumentKgExtractionStats:
        """Extract KG triples for each chunk, upsert into PostgreSQL, and enrich chunk metadata."""
        unique_entity_ids: set[UUID] = set()
        unique_edge_ids: set[UUID] = set()

        for chunk in chunks:
            extraction = await self._gemini.extract_chunk_kg(
                chunk_text=chunk.content,
                document_title=document_title,
            )
            entity_map, entity_refs = await self._resolve_chunk_entities(
                candidates=extraction.entities,
                chunk_id=chunk.chunk_id,
                document_id=document_id,
            )
            for ref in entity_refs:
                unique_entity_ids.add(ref.entity_id)

            rel_refs, implicit_ids = await self._resolve_chunk_relationships(
                extraction=extraction,
                entity_map=entity_map,
                chunk_id=chunk.chunk_id,
                document_id=document_id,
                document_title=document_title,
            )
            unique_entity_ids.update(implicit_ids)
            for rel_ref in rel_refs:
                unique_edge_ids.add(rel_ref.edge_id)

            updated_metadata = dict(chunk.chunk_metadata or {})
            updated_metadata["extracted_entities"] = [
                item.model_dump(mode="json") for item in entity_refs
            ]
            updated_metadata["extracted_relationships"] = [
                item.model_dump(mode="json") for item in rel_refs
            ]
            chunk.chunk_metadata = updated_metadata

        logger.info(
            "document_kg_extraction_completed",
            document_id=str(document_id),
            chunks_processed=len(chunks),
            entity_count=len(unique_entity_ids),
            relation_count=len(unique_edge_ids),
        )
        return DocumentKgExtractionStats(
            entity_count=len(unique_entity_ids),
            relation_count=len(unique_edge_ids),
        )

    async def _resolve_chunk_entities(
        self,
        *,
        candidates: list[ExtractedEntityCandidate],
        chunk_id: UUID,
        document_id: UUID,
    ) -> tuple[dict[str, KgEntity], list[ExtractedEntityRef]]:
        """Embed and upsert extracted entity candidates for a single chunk."""
        if not candidates:
            return {}, []

        embed_inputs = [
            f"{cand.canonical_name} ({cand.entity_type.value}): {cand.description}".strip()
            for cand in candidates
        ]
        embeddings = await self._gemini.embed_texts(embed_inputs)

        entity_map: dict[str, KgEntity] = {}
        entity_refs: list[ExtractedEntityRef] = []
        seen_entity_ids: set[UUID] = set()

        for candidate, vector in zip(candidates, embeddings, strict=True):
            entity = await self._kg_repo.upsert_entity(
                canonical_name=candidate.canonical_name,
                entity_type=candidate.entity_type,
                aliases=candidate.aliases,
                description=candidate.description,
                embedding=vector,
                source_chunk_id=chunk_id,
                source_document_id=document_id,
            )
            entity_map[normalize_lookup_key(candidate.canonical_name)] = entity
            entity_map[normalize_lookup_key(entity.canonical_name)] = entity
            for alias in candidate.aliases:
                entity_map[normalize_lookup_key(alias)] = entity

            if entity.entity_id not in seen_entity_ids:
                seen_entity_ids.add(entity.entity_id)
                entity_refs.append(
                    ExtractedEntityRef(
                        entity_id=entity.entity_id,
                        canonical_name=entity.canonical_name,
                        entity_type=EntityTypeEnum(entity.entity_type),
                    )
                )

        return entity_map, entity_refs

    async def _get_or_create_endpoint_entity(
        self,
        *,
        name: str,
        entity_map: dict[str, KgEntity],
        chunk_id: UUID,
        document_id: UUID,
        document_title: str,
    ) -> tuple[KgEntity, bool]:
        """Resolve a relationship endpoint from the chunk map or upsert a fallback entity."""
        key = normalize_lookup_key(name)
        existing = entity_map.get(key)
        if existing is not None:
            return existing, False

        vector = await self._gemini.embed_query(f"{name} (CONCEPT): Referenced in {document_title}")
        created = await self._kg_repo.upsert_entity(
            canonical_name=name,
            entity_type=EntityTypeEnum.CONCEPT,
            aliases=[],
            description=f"Referenced in '{document_title}'.",
            embedding=vector,
            source_chunk_id=chunk_id,
            source_document_id=document_id,
        )
        entity_map[key] = created
        entity_map[normalize_lookup_key(created.canonical_name)] = created
        return created, True

    async def _resolve_chunk_relationships(
        self,
        *,
        extraction: ChunkKgExtractionResult,
        entity_map: dict[str, KgEntity],
        chunk_id: UUID,
        document_id: UUID,
        document_title: str,
    ) -> tuple[list[ExtractedRelationshipRef], set[UUID]]:
        """Upsert directed relationship triples and return refs plus implicit entity IDs."""
        rel_refs: list[ExtractedRelationshipRef] = []
        implicit_entity_ids: set[UUID] = set()
        seen_edge_ids: set[UUID] = set()

        for rel in extraction.relationships:
            edge_ref, new_ids = await self._persist_single_relationship(
                rel=rel,
                entity_map=entity_map,
                chunk_id=chunk_id,
                document_id=document_id,
                document_title=document_title,
            )
            implicit_entity_ids.update(new_ids)
            if edge_ref is not None and edge_ref.edge_id not in seen_edge_ids:
                seen_edge_ids.add(edge_ref.edge_id)
                rel_refs.append(edge_ref)

        return rel_refs, implicit_entity_ids

    async def _persist_single_relationship(
        self,
        *,
        rel: ExtractedRelationshipCandidate,
        entity_map: dict[str, KgEntity],
        chunk_id: UUID,
        document_id: UUID,
        document_title: str,
    ) -> tuple[ExtractedRelationshipRef | None, set[UUID]]:
        """Resolve endpoints and persist a single relationship triple if non-self-referential."""
        new_ids: set[UUID] = set()
        source_entity, src_created = await self._get_or_create_endpoint_entity(
            name=rel.source_entity_name,
            entity_map=entity_map,
            chunk_id=chunk_id,
            document_id=document_id,
            document_title=document_title,
        )
        if src_created:
            new_ids.add(source_entity.entity_id)

        target_entity, tgt_created = await self._get_or_create_endpoint_entity(
            name=rel.target_entity_name,
            entity_map=entity_map,
            chunk_id=chunk_id,
            document_id=document_id,
            document_title=document_title,
        )
        if tgt_created:
            new_ids.add(target_entity.entity_id)

        if source_entity.entity_id == target_entity.entity_id:
            return None, new_ids

        edge = await self._kg_repo.upsert_relationship(
            source_entity_id=source_entity.entity_id,
            target_entity_id=target_entity.entity_id,
            relation_type=rel.relation_type,
            evidence_snippet=rel.evidence_snippet,
            confidence=rel.confidence,
            source_chunk_id=chunk_id,
            document_id=document_id,
        )
        return (
            ExtractedRelationshipRef(
                edge_id=edge.edge_id,
                source_entity_name=source_entity.canonical_name,
                relation_type=RelationTypeEnum(edge.relation_type),
                target_entity_name=target_entity.canonical_name,
                confidence=float(edge.confidence),
            ),
            new_ids,
        )
