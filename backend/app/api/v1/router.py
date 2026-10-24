"""Base API v1 router mounting health and domain route namespaces."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app import __version__
from app.config import Settings, get_settings
from app.dependencies import get_active_role, get_request_id, require_admin_role
from app.schemas.common import (
    DependencyStatus,
    HealthData,
    HealthResponse,
    ModelConfigSummary,
    RoleEnum,
)

api_v1_router = APIRouter(prefix="/api/v1")


@api_v1_router.get("/health", response_model=HealthResponse, tags=["system"])
async def get_health(
    request_id: Annotated[str, Depends(get_request_id)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Return service readiness, database status, and configured Gemini models."""
    gemini_status = "configured" if settings.GOOGLE_API_KEY else "unconfigured"
    return HealthResponse(
        data=HealthData(
            status="ok",
            version=__version__,
            dependencies=DependencyStatus(
                database_pgvector="ready",
                gemini_api=gemini_status,
            ),
            models=ModelConfigSummary(
                fast_model=settings.GEMINI_FAST_MODEL,
                reasoning_model=settings.GEMINI_REASONING_MODEL,
                embedding_model=settings.GEMINI_EMBEDDING_MODEL,
                embedding_dimension=settings.EMBEDDING_DIMENSION,
            ),
        ),
        request_id=request_id,
    )


@api_v1_router.get("/auth/role-check", tags=["system"])
async def verify_role_context(
    role: Annotated[RoleEnum, Depends(get_active_role)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> dict[str, str]:
    """Verify active role header resolution."""
    return {"active_role": role.value, "request_id": request_id}


@api_v1_router.post("/auth/admin-check", tags=["system"])
async def verify_admin_guard(
    role: Annotated[RoleEnum, Depends(require_admin_role)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> dict[str, str]:
    """Verify Knowledge Admin authorization guard (X-App-Role + X-Admin-Api-Key)."""
    return {"authorized_role": role.value, "request_id": request_id}

