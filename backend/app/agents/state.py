"""Typed Google ADK shared session state contract matching ARCHITECTURE.md Section 5.3."""

from pydantic import Field

from app.schemas.common import (
    GroundingStatusEnum,
    ProvenanceModalityEnum,
    StrictSchema,
    TraceStatusEnum,
)


class RetrievedChunkStateItem(StrictSchema):
    """Document chunk candidate stored in TurnWorkingState during a turn."""

    badge_index: int = Field(ge=1)
    chunk_id: str
    document_id: str
    document_title: str
    section_title: str | None = None
    page_number: int | None = None
    excerpt: str
    rrf_score: float
    vector_similarity: float


class RetrievedGraphPathStateItem(StrictSchema):
    """Knowledge Graph path candidate stored in TurnWorkingState during a turn."""

    badge_index: int = Field(ge=1)
    edge_ids: list[str]
    node_ids: list[str]
    path_summary: str
    evidence_snippet: str = ""
    hop_depth: int = Field(ge=1, le=3)
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_chunk_ids: list[str] = Field(default_factory=list)


class RetrievedMemoryStateItem(StrictSchema):
    """Memory entry candidate stored in TurnWorkingState during a turn."""

    badge_index: int = Field(ge=1)
    memory_id: str
    memory_tier: str
    key_name: str
    content: str
    confidence: float = Field(ge=0.0, le=1.0)


class CitationMappingItem(StrictSchema):
    """Unified citation badge mapping item."""

    badge_id: str
    modality: ProvenanceModalityEnum
    badge_index: int = Field(ge=1)
    target_id: str
    display_label: str


class AgentTraceEntryState(StrictSchema):
    """Agent execution step recorded in TurnWorkingState."""

    step_order: int = Field(ge=1)
    agent_name: str
    tool_name: str
    status: TraceStatusEnum
    duration_ms: int = Field(ge=0)
    summary: str


class TurnWorkingState(StrictSchema):
    """Shared ADK InvocationContext.session.state contract across the 5-agent hierarchy."""

    turn_id: str
    session_id: str
    user_query: str
    active_role: str = "researcher"
    query_intent: str = "SEMANTIC_LOOKUP"
    sub_queries: list[str] = Field(default_factory=list)
    entity_candidates: list[str] = Field(default_factory=list)
    intent_plan: list[str] = Field(default_factory=list)
    active_modalities: list[str] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunkStateItem] = Field(default_factory=list)
    retrieved_kg_paths: list[RetrievedGraphPathStateItem] = Field(default_factory=list)
    retrieved_memories: list[RetrievedMemoryStateItem] = Field(default_factory=list)
    citation_map: list[CitationMappingItem] = Field(default_factory=list)
    agent_trace_steps: list[AgentTraceEntryState] = Field(default_factory=list)
    draft_answer: str = ""
    grounding_status: GroundingStatusEnum = GroundingStatusEnum.GROUNDED
    grounding_score: float = Field(default=1.0, ge=0.0, le=1.0)
    unsupported_claims: list[str] = Field(default_factory=list)
