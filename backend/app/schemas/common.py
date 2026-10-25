"""Canonical Pydantic v2 domain enums, pagination metadata, and error envelopes."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    """Base Pydantic v2 model enforcing strict extra-field rejection and ORM compatibility."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class RoleEnum(StrEnum):
    """Application role modes (Decision D-05)."""

    RESEARCHER = "researcher"
    ADMIN = "admin"


class DocumentStatusEnum(StrEnum):
    """Document ingestion lifecycle states (DATABASE.md & DESIGN.md)."""

    QUEUED = "QUEUED"
    PARSING = "PARSING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    EXTRACTING_KG = "EXTRACTING_KG"
    INDEXED = "INDEXED"
    FAILED = "FAILED"


class GroundingStatusEnum(StrEnum):
    """SynthesisVerifierAgent grounding verdicts."""

    GROUNDED = "GROUNDED"
    PARTIAL = "PARTIAL"
    ABSTAINED = "ABSTAINED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EntityTypeEnum(StrEnum):
    """Curated Knowledge Graph entity types (Decision D-03)."""

    SYSTEM = "System"
    COMPONENT = "Component"
    ORGANIZATION = "Organization"
    PERSON = "Person"
    CONCEPT = "Concept"
    PROCESS = "Process"
    POLICY = "Policy"
    LOCATION = "Location"
    EVENT = "Event"


class RelationTypeEnum(StrEnum):
    """Curated Knowledge Graph relationship types (Decision D-03)."""

    DEPENDS_ON = "DEPENDS_ON"
    PART_OF = "PART_OF"
    MANAGED_BY = "MANAGED_BY"
    AUTHORED_BY = "AUTHORED_BY"
    CAUSES = "CAUSES"
    MITIGATES = "MITIGATES"
    COMMUNICATES_WITH = "COMMUNICATES_WITH"
    GOVERNED_BY = "GOVERNED_BY"
    LOCATED_IN = "LOCATED_IN"
    RELATED_TO = "RELATED_TO"


class MemoryTierEnum(StrEnum):
    """Centralized memory scopes (Decision D-04 & DATABASE.md)."""

    SESSION = "SESSION"
    SHORT_TERM = "SHORT_TERM"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    LONG_TERM_EPISODIC = "LONG_TERM_EPISODIC"
    LONG_TERM_SEMANTIC = "LONG_TERM_SEMANTIC"


class AgentNameEnum(StrEnum):
    """Google ADK 5-agent hierarchy names (DATABASE.md Table 9 & API.md Section 3.2)."""

    ORCHESTRATOR = "Orchestrator"
    MEMORY_AGENT = "MemoryAgent"
    VECTOR_RETRIEVER = "VectorRetriever"
    KG_RETRIEVER = "KGRetriever"
    SYNTHESIS_VERIFIER = "SynthesisVerifier"


class TraceStatusEnum(StrEnum):
    """Execution step status values for agent_execution_traces and SSE events."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FALLBACK = "FALLBACK"
    ERROR = "ERROR"


class ProvenanceModalityEnum(StrEnum):
    """Tri-pillar provenance badge modalities."""

    DOC = "Doc"
    KG = "KG"
    MEM = "Mem"


class PaginationMeta(StrictSchema):
    """Cursor pagination metadata for bounded list endpoints."""

    next_cursor: str | None = None
    has_more: bool = False
    limit: int = Field(default=20, ge=1, le=100)


class OffsetPaginationMeta(StrictSchema):
    """Offset pagination metadata matching API.md Section 6."""

    total: int = Field(default=0, ge=0)
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    has_more: bool = False


class ErrorDetail(StrictSchema):
    """Inner error structure matching API.md Section 5.1."""

    code: str
    message: str
    details: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)
    request_id: str


class ErrorEnvelope(StrictSchema):
    """Canonical non-2xx HTTP error response envelope."""

    error: ErrorDetail


class DependencyStatus(StrictSchema):
    """Readiness status for individual infrastructure dependencies."""

    database_pgvector: str
    gemini_api: str


class ModelConfigSummary(StrictSchema):
    """Configured Gemini models surfaced by the health/settings endpoints."""

    fast_model: str
    reasoning_model: str
    embedding_model: str
    embedding_dimension: int


class HealthData(StrictSchema):
    """Payload returned inside GET /api/v1/health."""

    status: str
    version: str
    dependencies: DependencyStatus
    models: ModelConfigSummary


class HealthResponse(StrictSchema):
    """Envelope for GET /api/v1/health."""

    data: HealthData
    request_id: str
