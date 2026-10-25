"""Pydantic v2 schemas for Knowledge Graph extraction (D-03) and explorer endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import (
    EntityTypeEnum,
    OffsetPaginationMeta,
    RelationTypeEnum,
    StrictSchema,
)


class ExtractedEntityCandidate(StrictSchema):
    """Structured entity extracted from a document chunk by Gemini (Decision D-03)."""

    canonical_name: str = Field(min_length=1, max_length=200)
    entity_type: EntityTypeEnum
    aliases: list[str] = Field(default_factory=list)
    description: str = Field(default="", max_length=1000)

    @field_validator("canonical_name")
    @classmethod
    def strip_canonical_name(cls, value: str) -> str:
        """Ensure canonical_name is non-empty after whitespace normalization."""
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("canonical_name cannot be empty or whitespace only.")
        return cleaned

    @model_validator(mode="after")
    def clean_aliases(self) -> "ExtractedEntityCandidate":
        """Normalize, deduplicate, and exclude canonical_name from aliases."""
        normalized: list[str] = []
        for raw in self.aliases:
            cleaned = " ".join(raw.split())
            if cleaned and cleaned != self.canonical_name and cleaned not in normalized:
                normalized.append(cleaned)
        self.aliases = normalized
        return self


class ExtractedRelationshipCandidate(StrictSchema):
    """Structured directed triple extracted from a document chunk by Gemini (Decision D-03)."""

    source_entity_name: str = Field(min_length=1, max_length=200)
    target_entity_name: str = Field(min_length=1, max_length=200)
    relation_type: RelationTypeEnum
    evidence_snippet: str = Field(min_length=1, max_length=500)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)

    @field_validator("source_entity_name", "target_entity_name", "evidence_snippet")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        """Normalize whitespace on entity names and evidence snippets."""
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only.")
        return cleaned


class ChunkKgExtractionResult(StrictSchema):
    """Schema bound to Gemini response_schema for deterministic KG triple extraction."""

    entities: list[ExtractedEntityCandidate] = Field(default_factory=list)
    relationships: list[ExtractedRelationshipCandidate] = Field(default_factory=list)


class KgEntitySummary(StrictSchema):
    """Knowledge Graph entity node returned by GET /api/v1/kg/entities."""

    entity_id: UUID
    canonical_name: str
    lookup_key: str
    entity_type: EntityTypeEnum
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    source_chunk_ids: list[UUID] = Field(default_factory=list)
    source_document_ids: list[UUID] = Field(default_factory=list)
    degree_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class KgEntityListResponse(StrictSchema):
    """Paginated response for GET /api/v1/kg/entities."""

    items: list[KgEntitySummary]
    pagination: OffsetPaginationMeta


class KgRelationshipItem(StrictSchema):
    """Directed Knowledge Graph relationship edge."""

    edge_id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: RelationTypeEnum
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_chunk_id: UUID
    document_id: UUID
    hop_depth: int = Field(default=1, ge=1, le=3)
    created_at: datetime | None = None


class SubgraphSupportingChunk(StrictSchema):
    """Verbatim backing document chunk returned alongside a Knowledge Graph subgraph."""

    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int = Field(ge=0)
    content: str


class KgSubgraphResponse(StrictSchema):
    """Response for GET /api/v1/kg/entities/{entity_id}/subgraph."""

    center_entity: KgEntitySummary
    nodes: list[KgEntitySummary]
    edges: list[KgRelationshipItem]
    supporting_chunks: list[SubgraphSupportingChunk]


class SubgraphEdgeRow(StrictSchema):
    """Typed row returned by the PostgreSQL traverse_kg_subgraph recursive CTE."""

    edge_id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: RelationTypeEnum
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_chunk_id: UUID
    document_id: UUID
    hop_depth: int = Field(ge=1, le=3)
