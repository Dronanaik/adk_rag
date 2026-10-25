"""Knowledge Graph Explorer REST endpoints (/api/v1/kg, API.md Section 3.3)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import DbSessionDep, get_active_role
from app.schemas.common import EntityTypeEnum, RoleEnum
from app.schemas.kg import KgEntityListResponse, KgSubgraphResponse
from app.services.kg_explorer_service import KnowledgeGraphExplorerService

router = APIRouter(prefix="/kg", tags=["knowledge-graph"])


def get_kg_explorer_service(session: DbSessionDep) -> KnowledgeGraphExplorerService:
    """Provide a request-scoped KnowledgeGraphExplorerService instance."""
    return KnowledgeGraphExplorerService(session=session)


@router.get(
    "/entities",
    response_model=KgEntityListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search and filter canonical Knowledge Graph nodes",
)
@router.get(
    "/nodes",
    response_model=KgEntityListResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_kg_entities(
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    service: Annotated[KnowledgeGraphExplorerService, Depends(get_kg_explorer_service)],
    search: Annotated[str | None, Query(max_length=200)] = None,
    entity_type: Annotated[EntityTypeEnum | None, Query()] = None,
    document_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> KgEntityListResponse:
    """List canonical Knowledge Graph nodes with incident degree counts and pagination."""
    return await service.list_entities(
        search=search,
        entity_type=entity_type,
        document_id=document_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/entities/{entity_id}/subgraph",
    response_model=KgSubgraphResponse,
    status_code=status.HTTP_200_OK,
    summary="Traverse 1-2 hop Knowledge Graph neighborhood around a canonical entity",
)
async def get_kg_entity_subgraph(
    entity_id: UUID,
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    service: Annotated[KnowledgeGraphExplorerService, Depends(get_kg_explorer_service)],
    hops: Annotated[int, Query(ge=1, le=2)] = 1,
) -> KgSubgraphResponse:
    """Execute bounded 1-2 hop subgraph traversal and return nodes, edges, and backing chunks."""
    return await service.get_entity_subgraph(entity_id=entity_id, hops=hops)


@router.get(
    "/subgraph",
    response_model=KgSubgraphResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_kg_subgraph_by_query(
    entity_id: Annotated[UUID, Query(description="Seed canonical entity UUID")],
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    service: Annotated[KnowledgeGraphExplorerService, Depends(get_kg_explorer_service)],
    hops: Annotated[int, Query(ge=1, le=2)] = 1,
) -> KgSubgraphResponse:
    """Query-parameter alias (/api/v1/kg/subgraph?entity_id=...) for subgraph inspection."""
    return await service.get_entity_subgraph(entity_id=entity_id, hops=hops)

