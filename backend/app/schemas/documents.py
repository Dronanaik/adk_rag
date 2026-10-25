"""Pydantic v2 request and response schemas for Knowledge Base documents and chunks."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.common import (
    DocumentStatusEnum,
    EntityTypeEnum,
    OffsetPaginationMeta,
    RelationTypeEnum,
    StrictSchema,
)

AllowedMimeType = Literal["application/pdf", "text/markdown", "text/plain"]


class DocumentUploadItemResponse(StrictSchema):
    """Per-file upload result returned by POST /api/v1/documents/upload."""

    document_id: UUID
    title: str
    filename: str
    mime_type: AllowedMimeType
    content_hash: str = Field(min_length=64, max_length=64)
    file_size_bytes: int = Field(gt=0, le=26214400)
    status: DocumentStatusEnum
    deduplicated_hit: bool = False
    created_at: datetime


class DocumentUploadResponse(StrictSchema):
    """Envelope returned by POST /api/v1/documents/upload (202 Accepted)."""

    documents: list[DocumentUploadItemResponse]


class DocumentSummary(StrictSchema):
    """Document metadata and ingestion metrics returned by GET /api/v1/documents."""

    document_id: UUID
    title: str
    filename: str
    mime_type: AllowedMimeType
    content_hash: str = Field(min_length=64, max_length=64)
    file_size_bytes: int = Field(gt=0, le=26214400)
    status: DocumentStatusEnum
    error_message: str | None = None
    chunk_count: int = Field(default=0, ge=0)
    entity_count: int = Field(default=0, ge=0)
    relation_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class CorpusSummaryMetrics(StrictSchema):
    """Aggregate corpus metrics returned by GET /api/v1/documents."""

    total_documents: int = Field(default=0, ge=0)
    total_indexed_chunks: int = Field(default=0, ge=0)
    total_kg_entities: int = Field(default=0, ge=0)
    total_kg_relationships: int = Field(default=0, ge=0)


class DocumentListResponse(StrictSchema):
    """Paginated response for GET /api/v1/documents."""

    items: list[DocumentSummary]
    summary_metrics: CorpusSummaryMetrics
    pagination: OffsetPaginationMeta


class ExtractedEntityRef(StrictSchema):
    """Lightweight entity reference embedded in a chunk's metadata."""

    entity_id: UUID
    canonical_name: str
    entity_type: EntityTypeEnum


class ExtractedRelationshipRef(StrictSchema):
    """Lightweight relationship reference embedded in a chunk's metadata."""

    edge_id: UUID
    source_entity_name: str
    relation_type: RelationTypeEnum
    target_entity_name: str
    confidence: float = Field(ge=0.0, le=1.0)


class ChunkMetadataSchema(StrictSchema):
    """Structured metadata stored on document_chunks and returned by the Chunk Inspector."""

    page_number: int | None = None
    section_heading: str | None = None
    char_start: int = Field(default=0, ge=0)
    char_end: int = Field(default=0, ge=0)
    token_count: int = Field(default=0, ge=0)
    extracted_entities: list[ExtractedEntityRef] = Field(default_factory=list)
    extracted_relationships: list[ExtractedRelationshipRef] = Field(default_factory=list)


class DocumentChunkItem(StrictSchema):
    """Single deterministic chunk returned by GET /api/v1/documents/{document_id}/chunks."""

    chunk_id: UUID
    document_id: UUID
    chunk_index: int = Field(ge=0)
    content: str
    metadata: ChunkMetadataSchema
    created_at: datetime


class DocumentChunkListResponse(StrictSchema):
    """Paginated response for GET /api/v1/documents/{document_id}/chunks."""

    document: DocumentSummary
    items: list[DocumentChunkItem]
    pagination: OffsetPaginationMeta


class DocumentDeleteResponse(StrictSchema):
    """Cascading deletion report returned by DELETE /api/v1/documents/{document_id}."""

    deleted_document_id: UUID
    removed_chunks_count: int = Field(ge=0)
    removed_relationships_count: int = Field(ge=0)
    removed_orphaned_entities_count: int = Field(ge=0)

