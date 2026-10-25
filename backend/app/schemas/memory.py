"""Pydantic v2 schemas for Centralized Memory entries, curation, and consolidation (D-04)."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.schemas.common import MemoryTierEnum, OffsetPaginationMeta, StrictSchema


class MemoryEntryItem(StrictSchema):
    """Hydrated memory entry returned by GET /api/v1/memories."""

    memory_id: UUID
    memory_tier: MemoryTierEnum
    session_id: UUID | None = None
    content: str
    related_entity_ids: list[UUID] = Field(default_factory=list)
    related_entity_names: list[str] = Field(default_factory=list)
    source_turn_id: UUID | None = None
    supporting_chunk_ids: list[UUID] = Field(default_factory=list)
    supporting_document_titles: list[str] = Field(default_factory=list)
    superseded_by_id: UUID | None = None
    similarity_score: float | None = None
    created_at: datetime


class MemoryListResponse(StrictSchema):
    """Paginated response for GET /api/v1/memories."""

    items: list[MemoryEntryItem]
    pagination: OffsetPaginationMeta


class MemoryDeleteResponse(StrictSchema):
    """Response returned by DELETE /api/v1/memories/{memory_id}."""

    deleted_memory_id: UUID
    memory_tier: MemoryTierEnum


class MemoryUpdateRequest(StrictSchema):
    """Request body for PATCH /api/v1/memories/{memory_id} (Admin Only)."""

    content: str = Field(min_length=5, max_length=1500)

    @field_validator("content")
    @classmethod
    def normalize_updated_content(cls, value: str) -> str:
        """Trim and normalize whitespace on edited memory content."""
        cleaned = " ".join(value.split())
        if len(cleaned) < 5:
            raise ValueError("Memory fact content must be at least 5 non-whitespace characters.")
        return cleaned



class VerifiedFactCandidate(StrictSchema):
    """Verified fact proposed for Centralized Memory consolidation (Decision D-04)."""

    content: str = Field(min_length=5, max_length=1500)
    memory_tier: MemoryTierEnum = MemoryTierEnum.LONG_TERM_SEMANTIC
    related_entity_ids: list[UUID] = Field(default_factory=list)
    supporting_chunk_ids: list[UUID] = Field(default_factory=list)
    supersedes_memory_ids: list[UUID] = Field(default_factory=list)

    @field_validator("content")
    @classmethod
    def normalize_fact_content(cls, value: str) -> str:
        """Trim and normalize whitespace on consolidated facts."""
        cleaned = " ".join(value.split())
        if len(cleaned) < 5:
            raise ValueError("Memory fact content must be at least 5 non-whitespace characters.")
        return cleaned

    @model_validator(mode="after")
    def require_provenance_for_long_term(self) -> "VerifiedFactCandidate":
        """Enforce Decision D-04: long-term shared memories require supporting chunk provenance."""
        if (
            self.memory_tier
            in (
                MemoryTierEnum.LONG_TERM_SEMANTIC,
                MemoryTierEnum.LONG_TERM_EPISODIC,
            )
            and not self.supporting_chunk_ids
        ):
            raise ValueError(
                "Decision D-04: Long-term memory facts require at least one supporting_chunk_id."
            )
        return self


class MemoryConsolidationResult(StrictSchema):
    """Summary of memory consolidation performed after SynthesisVerifier approval."""

    created_memory_ids: list[UUID] = Field(default_factory=list)
    superseded_memory_ids: list[UUID] = Field(default_factory=list)
    skipped_duplicate_count: int = Field(default=0, ge=0)
