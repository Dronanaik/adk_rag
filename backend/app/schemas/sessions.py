"""Pydantic v2 schemas for conversation sessions, message turns, citations, and SSE events."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import (
    AgentNameEnum,
    GroundingStatusEnum,
    MemoryTierEnum,
    OffsetPaginationMeta,
    RelationTypeEnum,
    StrictSchema,
    TraceStatusEnum,
)
from app.schemas.documents import ExtractedEntityRef
from app.schemas.kg import KgEntitySummary, KgRelationshipItem


class SessionCreateRequest(StrictSchema):
    """Request body for POST /api/v1/sessions."""

    title: str = Field(default="New Research Session", min_length=1, max_length=200)
    use_shared_memory: bool = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """Normalize session title whitespace."""
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Session title cannot be empty.")
        return cleaned


class SessionUpdateRequest(StrictSchema):
    """Request body for PATCH /api/v1/sessions/{session_id}."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    use_shared_memory: bool | None = None

    @field_validator("title")
    @classmethod
    def validate_optional_title(cls, value: str | None) -> str | None:
        """Normalize optional title when provided."""
        if value is None:
            return None
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Session title cannot be empty.")
        return cleaned


class SessionResponse(StrictSchema):
    """Session metadata returned by POST/PATCH /api/v1/sessions."""

    session_id: UUID
    title: str
    use_shared_memory: bool
    created_at: datetime
    updated_at: datetime


class SessionSummaryItem(StrictSchema):
    """Session list item returned by GET /api/v1/sessions."""

    session_id: UUID
    title: str
    use_shared_memory: bool
    turn_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class SessionListResponse(StrictSchema):
    """Paginated response for GET /api/v1/sessions."""

    items: list[SessionSummaryItem]
    pagination: OffsetPaginationMeta


class CitedChunkItem(StrictSchema):
    """Hydrated document chunk citation item in turn provenance."""

    citation_key: str
    chunk_id: UUID
    document_id: UUID
    document_title: str
    chunk_index: int = Field(ge=0)
    content: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    page_number: int | None = None
    section_heading: str | None = None
    extracted_entities: list[ExtractedEntityRef] = Field(default_factory=list)


class CitedKgPathItem(StrictSchema):
    """Hydrated Knowledge Graph relationship triple citation item in turn provenance."""

    citation_key: str
    edge_id: UUID
    source_entity: str
    relation_type: RelationTypeEnum
    target_entity: str
    evidence_snippet: str
    confidence: float = Field(ge=0.0, le=1.0)
    source_chunk_id: UUID
    document_title: str


class CitedMemoryItem(StrictSchema):
    """Hydrated Centralized Memory citation item in turn provenance."""

    citation_key: str
    memory_id: UUID
    memory_tier: MemoryTierEnum
    content: str
    source_turn_id: UUID | None = None
    supporting_chunk_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime


class TurnCitationsEnvelope(StrictSchema):
    """Grouped tri-pillar citations persisted on message_turns and emitted in turn_complete."""

    chunks: list[CitedChunkItem] = Field(default_factory=list)
    kg_paths: list[CitedKgPathItem] = Field(default_factory=list)
    memories: list[CitedMemoryItem] = Field(default_factory=list)


class AgentExecutionTraceItem(StrictSchema):
    """Persisted step telemetry record from agent_execution_traces."""

    trace_id: UUID
    turn_id: UUID
    step_order: int = Field(ge=1)
    agent_name: AgentNameEnum
    action_or_tool: str
    input_payload: dict[str, object] = Field(default_factory=dict)
    output_summary: dict[str, object] = Field(default_factory=dict)
    latency_ms: int = Field(default=0, ge=0)
    status: TraceStatusEnum
    created_at: datetime


class AbstentionDiagnostics(StrictSchema):
    """Structured explanation emitted when grounding_status is INSUFFICIENT_EVIDENCE."""

    reason: str
    searched_entities: list[str] = Field(default_factory=list)
    searched_queries: list[str] = Field(default_factory=list)
    recommended_action: str


class TurnSubgraphEnvelope(StrictSchema):
    """Bounded 1-2 hop local neighborhood retrieved during a turn."""

    nodes: list[KgEntitySummary] = Field(default_factory=list)
    edges: list[KgRelationshipItem] = Field(default_factory=list)


class MessageTurnResponse(StrictSchema):
    """Full turn record returned inside GET /api/v1/sessions/{session_id}."""

    turn_id: UUID
    session_id: UUID
    turn_index: int = Field(ge=0)
    user_query: str
    assistant_response: str
    grounding_status: GroundingStatusEnum
    citations: TurnCitationsEnvelope
    agent_execution_traces: list[AgentExecutionTraceItem] = Field(default_factory=list)
    total_latency_ms: int = Field(default=0, ge=0)
    created_at: datetime


class SessionDetailResponse(StrictSchema):
    """Response for GET /api/v1/sessions/{session_id}."""

    session: SessionResponse
    turns: list[MessageTurnResponse]


class TurnCreateRequest(StrictSchema):
    """Request body for POST /api/v1/sessions/{session_id}/turns."""

    user_query: str = Field(min_length=1, max_length=4000)
    use_shared_memory: bool | None = None

    @field_validator("user_query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        """Ensure user_query is non-empty after stripping whitespace."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("user_query cannot be empty or whitespace only.")
        return cleaned


class AgentStepCounts(StrictSchema):
    """Evidence counts emitted in SSE agent_step events."""

    chunks: int = Field(default=0, ge=0)
    kg_edges: int = Field(default=0, ge=0)
    memories: int = Field(default=0, ge=0)


class AgentStepSseEvent(StrictSchema):
    """Payload for SSE `event: agent_step`."""

    step_order: int = Field(ge=1)
    agent_name: AgentNameEnum
    action_or_tool: str
    status: TraceStatusEnum
    summary: str
    counts: AgentStepCounts = Field(default_factory=AgentStepCounts)
    latency_ms: int = Field(default=0, ge=0)


class TokenSseEvent(StrictSchema):
    """Payload for SSE `event: token`."""

    delta: str


class TurnCompleteSseEvent(StrictSchema):
    """Payload for SSE `event: turn_complete`."""

    turn_id: UUID
    turn_index: int = Field(ge=0)
    assistant_response: str
    grounding_status: GroundingStatusEnum
    fallback_warning: str | None = None
    abstention_diagnostics: AbstentionDiagnostics | None = None
    citations: TurnCitationsEnvelope
    subgraph: TurnSubgraphEnvelope = Field(default_factory=TurnSubgraphEnvelope)
    agent_execution_traces: list[AgentExecutionTraceItem] = Field(default_factory=list)
    total_latency_ms: int = Field(default=0, ge=0)


class ErrorSseEvent(StrictSchema):
    """Payload for SSE `event: error`."""

    code: str
    message: str
    retryable: bool = False
    request_id: str

