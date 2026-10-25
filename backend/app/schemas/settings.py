"""Pydantic v2 schemas for System Settings and Integration Telemetry (Screen 4)."""

from datetime import datetime

from pydantic import Field

from app.schemas.common import StrictSchema


class SystemSettingsSchema(StrictSchema):
    """Runtime retrieval thresholds and orchestrator bounds (system_settings table)."""

    top_k_chunks: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    max_kg_hops: int = Field(default=2, ge=1, le=2)
    max_agent_steps: int = Field(default=5, ge=3, le=8)
    turn_timeout_seconds: int = Field(default=30, ge=10, le=60)
    auto_consolidate_memory: bool = True
    strict_abstention_mode: bool = True
    updated_at: datetime


class SystemSettingsUpdateRequest(StrictSchema):
    """Request body for PUT /api/v1/settings (partial or full update)."""

    top_k_chunks: int | None = Field(default=None, ge=1, le=20)
    similarity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    max_kg_hops: int | None = Field(default=None, ge=1, le=2)
    max_agent_steps: int | None = Field(default=None, ge=3, le=8)
    turn_timeout_seconds: int | None = Field(default=None, ge=10, le=60)
    auto_consolidate_memory: bool | None = None
    strict_abstention_mode: bool | None = None


class IntegrationTelemetrySchema(StrictSchema):
    """Live connectivity and model configuration telemetry returned by GET /api/v1/settings."""

    adk_runtime_status: str
    gemini_api_status: str
    supabase_db_status: str
    db_latency_ms: float = Field(default=0.0, ge=0.0)
    embedding_model: str
    llm_model: str


class SettingsResponse(StrictSchema):
    """Envelope returned by GET /api/v1/settings."""

    settings: SystemSettingsSchema
    telemetry: IntegrationTelemetrySchema

