"""System Configuration and Integration Telemetry endpoints (/api/v1/settings, API.md 3.5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.config import Settings, get_settings
from app.dependencies import DbSessionDep, get_active_role, require_admin_role
from app.models.entities import SystemSetting
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import RoleEnum
from app.schemas.settings import (
    IntegrationTelemetrySchema,
    SettingsResponse,
    SystemSettingsSchema,
    SystemSettingsUpdateRequest,
)

router = APIRouter(prefix="/settings", tags=["settings"])


def _to_settings_schema(row: SystemSetting) -> SystemSettingsSchema:
    """Convert a SQLAlchemy SystemSetting singleton row into a validated SystemSettingsSchema."""
    return SystemSettingsSchema(
        top_k_chunks=row.top_k_chunks,
        similarity_threshold=float(row.similarity_threshold),
        max_kg_hops=row.max_kg_hops,
        max_agent_steps=row.max_agent_steps,
        turn_timeout_seconds=row.turn_timeout_seconds,
        auto_consolidate_memory=row.auto_consolidate_memory,
        strict_abstention_mode=row.strict_abstention_mode,
        updated_at=row.updated_at,
    )


@router.get(
    "",
    response_model=SettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch runtime retrieval settings and live integration telemetry",
)
async def get_system_settings(
    session: DbSessionDep,
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    config: Annotated[Settings, Depends(get_settings)],
) -> SettingsResponse:
    """Fetch singleton runtime settings and live database/Gemini integration telemetry."""
    repo = SettingsRepository(session)
    setting_row = await repo.get_settings()
    db_latency_ms = await repo.measure_db_latency_ms()

    gemini_status = "CONNECTED" if bool(config.GOOGLE_API_KEY.strip()) else "UNCONFIGURED"
    telemetry = IntegrationTelemetrySchema(
        adk_runtime_status="READY",
        gemini_api_status=gemini_status,
        supabase_db_status="CONNECTED",
        db_latency_ms=db_latency_ms,
        embedding_model=config.GEMINI_EMBEDDING_MODEL,
        llm_model=config.GEMINI_FAST_MODEL,
    )
    return SettingsResponse(
        settings=_to_settings_schema(setting_row),
        telemetry=telemetry,
    )


@router.put(
    "",
    response_model=SystemSettingsSchema,
    status_code=status.HTTP_200_OK,
    summary="Update runtime retrieval thresholds and orchestrator bounds (Admin Only)",
)
async def update_system_settings(
    payload: SystemSettingsUpdateRequest,
    session: DbSessionDep,
    _admin: Annotated[RoleEnum, Depends(require_admin_role)],
) -> SystemSettingsSchema:
    """Apply partial or full updates to runtime retrieval and orchestrator settings."""
    repo = SettingsRepository(session)
    updated_row = await repo.update_settings(payload)
    return _to_settings_schema(updated_row)

