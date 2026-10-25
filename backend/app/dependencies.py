"""FastAPI dependency providers for request context and role-based access control (D-05)."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.database import get_db_session
from app.schemas.common import APIException, RoleEnum
from app.utils.logging import get_current_request_id

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

__all__ = [
    "APIException",
    "DbSessionDep",
    "get_active_role",
    "get_request_id",
    "require_admin_role",
]



async def get_request_id(request: Request) -> str:
    """Resolve the active request ID from request state or context var."""
    state_id = getattr(request.state, "request_id", None)
    if isinstance(state_id, str) and state_id:
        return state_id
    return get_current_request_id()


async def get_active_role(
    x_app_role: Annotated[str | None, Header(alias="X-App-Role")] = None,
) -> RoleEnum:
    """Resolve the caller's role header (defaults to researcher per API.md Section 2.1)."""
    if x_app_role is None or x_app_role.strip() == "":
        return RoleEnum.RESEARCHER
    normalized = x_app_role.strip().lower()
    if normalized == RoleEnum.ADMIN.value:
        return RoleEnum.ADMIN
    if normalized == RoleEnum.RESEARCHER.value:
        return RoleEnum.RESEARCHER
    raise APIException(
        status_code=400,
        code="VALIDATION_ERROR",
        message="Invalid X-App-Role header. Allowed values: 'researcher', 'admin'.",
        details={"header": "X-App-Role"},
    )


async def require_admin_role(
    role: Annotated[RoleEnum, Depends(get_active_role)],
    settings: Annotated[Settings, Depends(get_settings)],
    x_admin_api_key: Annotated[str | None, Header(alias="X-Admin-Api-Key")] = None,
) -> RoleEnum:
    """Enforce Knowledge Admin role and constant-time X-Admin-Api-Key verification (D-05)."""
    if role != RoleEnum.ADMIN:
        raise APIException(
            status_code=403,
            code="FORBIDDEN_ADMIN_REQUIRED",
            message="This action requires Knowledge Admin role ('X-App-Role: admin').",
        )

    configured_key = settings.ADMIN_API_KEY.strip()
    if not configured_key:
        return RoleEnum.ADMIN

    provided_key = (x_admin_api_key or "").strip()
    if not provided_key or not secrets.compare_digest(
        provided_key.encode("utf-8"),
        configured_key.encode("utf-8"),
    ):
        raise APIException(
            status_code=403,
            code="FORBIDDEN_ADMIN_REQUIRED",
            message="Missing or invalid X-Admin-Api-Key header for Knowledge Admin action.",
        )

    return RoleEnum.ADMIN

