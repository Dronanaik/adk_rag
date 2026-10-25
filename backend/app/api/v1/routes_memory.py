"""Centralized Memory Explorer REST endpoints (/api/v1/memories, API.md Section 3.4)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from app.config import Settings, get_settings
from app.dependencies import DbSessionDep, get_active_role, require_admin_role
from app.schemas.common import MemoryTierEnum, RoleEnum
from app.schemas.memory import (
    MemoryDeleteResponse,
    MemoryEntryItem,
    MemoryListResponse,
    MemoryUpdateRequest,
)
from app.services.memory_service import MemoryService

router = APIRouter(tags=["centralized-memory"])


def get_memory_service(
    session: DbSessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> MemoryService:
    """Provide a request-scoped MemoryService instance."""
    return MemoryService(session=session, settings=settings)


@router.get(
    "/memories",
    response_model=MemoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search and filter Centralized Memory records across tiers",
)
@router.get(
    "/memory-entries",
    response_model=MemoryListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_memories(
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    service: Annotated[MemoryService, Depends(get_memory_service)],
    memory_tier: Annotated[MemoryTierEnum | None, Query()] = None,
    memory_scope: Annotated[MemoryTierEnum | None, Query(include_in_schema=False)] = None,
    session_id: Annotated[UUID | None, Query()] = None,
    include_superseded: Annotated[bool, Query()] = False,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MemoryListResponse:
    """List Centralized Memory entries with hydrated entity names and document titles."""
    effective_tier = memory_tier if memory_tier is not None else memory_scope
    return await service.list_memories(
        memory_tier=effective_tier,
        session_id=session_id,
        include_superseded=include_superseded,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/memories/{memory_id}",
    response_model=MemoryEntryItem,
    status_code=status.HTTP_200_OK,
    summary="Curate/update a Centralized Memory fact (Admin Only)",
)
@router.patch(
    "/memory-entries/{memory_id}",
    response_model=MemoryEntryItem,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_memory_entry(
    memory_id: UUID,
    payload: MemoryUpdateRequest,
    _admin: Annotated[RoleEnum, Depends(require_admin_role)],
    service: Annotated[MemoryService, Depends(get_memory_service)],
) -> MemoryEntryItem:
    """Update a memory entry's content and re-embed its vector (Admin Only, D-05)."""
    return await service.update_memory(memory_id=memory_id, content=payload.content)


@router.delete(
    "/memories/{memory_id}",
    response_model=MemoryDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete ('Forget') a Centralized Memory record (FR-11)",
)
@router.delete(
    "/memory-entries/{memory_id}",
    response_model=MemoryDeleteResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def delete_memory_entry(
    memory_id: UUID,
    role: Annotated[RoleEnum, Depends(get_active_role)],
    service: Annotated[MemoryService, Depends(get_memory_service)],
    x_admin_api_key: Annotated[str | None, Header(alias="X-Admin-Api-Key")] = None,
) -> MemoryDeleteResponse:
    """Delete a memory entry enforcing SESSION (Researcher/Admin) vs LONG_TERM (Admin) RBAC."""
    return await service.delete_memory_authorized(
        memory_id=memory_id,
        role=role,
        admin_api_key=x_admin_api_key,
    )

