"""Conversation Sessions & SSE Multi-Agent Chat Turn endpoints (/api/v1/sessions)."""

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.agents.runtime import AgentRuntimeService
from app.config import Settings, get_settings
from app.dependencies import DbSessionDep, get_active_role, get_request_id
from app.models.entities import AgentExecutionTrace, MessageTurn
from app.repositories.session_repo import SessionRepository
from app.schemas.common import (
    APIException,
    GroundingStatusEnum,
    OffsetPaginationMeta,
    RoleEnum,
)
from app.schemas.sessions import (
    AgentExecutionTraceItem,
    MessageTurnResponse,
    SessionCreateRequest,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    SessionSummaryItem,
    SessionUpdateRequest,
    TurnCitationsEnvelope,
    TurnCreateRequest,
)

router = APIRouter(tags=["sessions-and-turns"])

_ACTIVE_SESSION_STREAMS: set[UUID] = set()


def get_session_repository(session: DbSessionDep) -> SessionRepository:
    """FastAPI dependency returning a SessionRepository bound to the request DB session."""
    return SessionRepository(session)


def get_agent_runtime_service(
    session: DbSessionDep,
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentRuntimeService:
    """FastAPI dependency returning an AgentRuntimeService bound to the request DB session."""
    return AgentRuntimeService(session=session, settings=settings)


def acquire_session_turn_lock(session_id: UUID) -> None:
    """Acquire per-session active turn lock or raise 429 RATE_LIMIT_EXCEEDED (API.md 9.2)."""
    if session_id in _ACTIVE_SESSION_STREAMS:
        raise APIException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message="A turn is already streaming for this session. Please wait for completion.",
            details={"session_id": str(session_id)},
        )
    _ACTIVE_SESSION_STREAMS.add(session_id)


def release_session_turn_lock(session_id: UUID) -> None:
    """Release per-session active turn lock."""
    _ACTIVE_SESSION_STREAMS.discard(session_id)


def _to_turn_response(
    turn: MessageTurn,
    traces: list[AgentExecutionTrace],
) -> MessageTurnResponse:
    """Convert a MessageTurn ORM row and its ordered traces into MessageTurnResponse."""
    raw_citations = turn.citations if isinstance(turn.citations, dict) else {}
    citations_envelope = TurnCitationsEnvelope.model_validate(raw_citations)
    trace_items = [AgentExecutionTraceItem.model_validate(t) for t in traces]
    return MessageTurnResponse(
        turn_id=turn.turn_id,
        session_id=turn.session_id,
        turn_index=turn.turn_index,
        user_query=turn.user_query,
        assistant_response=turn.assistant_response,
        grounding_status=GroundingStatusEnum(turn.grounding_status),
        citations=citations_envelope,
        agent_execution_traces=trace_items,
        total_latency_ms=turn.total_latency_ms,
        created_at=turn.created_at,
    )


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
async def create_session(
    session: DbSessionDep,
    repo: Annotated[SessionRepository, Depends(get_session_repository)],
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    payload: Annotated[SessionCreateRequest | None, Body()] = None,
) -> SessionResponse:
    """Create and persist a new ConversationSession row."""
    req = payload or SessionCreateRequest()
    conv_session = await repo.create_session(
        title=req.title,
        use_shared_memory=req.use_shared_memory,
    )
    await session.commit()
    return SessionResponse.model_validate(conv_session)


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List conversation sessions ordered by most recently updated",
)
async def list_sessions(
    repo: Annotated[SessionRepository, Depends(get_session_repository)],
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SessionListResponse:
    """List paginated conversation sessions with turn counts."""
    rows, total = await repo.list_sessions(limit=limit, offset=offset)
    items = [
        SessionSummaryItem(
            session_id=conv.session_id,
            title=conv.title,
            use_shared_memory=conv.use_shared_memory,
            turn_count=turn_count,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
        for conv, turn_count in rows
    ]
    return SessionListResponse(
        items=items,
        pagination=OffsetPaginationMeta.create(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch full session history including turns, citations, and agent traces",
)
async def get_session_detail(
    session_id: UUID,
    repo: Annotated[SessionRepository, Depends(get_session_repository)],
    _role: Annotated[RoleEnum, Depends(get_active_role)],
) -> SessionDetailResponse:
    """Fetch a single conversation session with chronological turns and traces."""
    conv_session = await repo.get_session(session_id)
    if conv_session is None:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SESSION_NOT_FOUND",
            message=f"Conversation session '{session_id}' was not found.",
            details={"session_id": str(session_id)},
        )
    turns_with_traces = await repo.list_turns_with_traces(session_id)
    turns = [_to_turn_response(turn, traces) for turn, traces in turns_with_traces]
    return SessionDetailResponse(
        session=SessionResponse.model_validate(conv_session),
        turns=turns,
    )


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update session title or shared memory toggle",
)
async def update_session(
    session_id: UUID,
    payload: SessionUpdateRequest,
    session: DbSessionDep,
    repo: Annotated[SessionRepository, Depends(get_session_repository)],
    _role: Annotated[RoleEnum, Depends(get_active_role)],
) -> SessionResponse:
    """Update mutable session fields (title, use_shared_memory)."""
    updated = await repo.update_session(
        session_id,
        title=payload.title,
        use_shared_memory=payload.use_shared_memory,
    )
    if updated is None:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SESSION_NOT_FOUND",
            message=f"Conversation session '{session_id}' was not found.",
            details={"session_id": str(session_id)},
        )
    conv_session, _turn_count = updated
    await session.commit()
    return SessionResponse.model_validate(conv_session)


@router.post(
    "/sessions/{session_id}/turns",
    status_code=status.HTTP_200_OK,
    summary="Submit a user query and stream multi-agent execution & synthesis via SSE",
)
async def create_turn_stream(
    session_id: UUID,
    payload: TurnCreateRequest,
    repo: Annotated[SessionRepository, Depends(get_session_repository)],
    runtime: Annotated[AgentRuntimeService, Depends(get_agent_runtime_service)],
    _role: Annotated[RoleEnum, Depends(get_active_role)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> StreamingResponse:
    """Execute the Google ADK 5-agent workflow and stream SSE events."""
    conv_session = await repo.get_session(session_id)
    if conv_session is None:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="SESSION_NOT_FOUND",
            message=f"Conversation session '{session_id}' was not found.",
            details={"session_id": str(session_id)},
        )

    acquire_session_turn_lock(session_id)

    async def _guarded_event_generator() -> AsyncIterator[str]:
        try:
            async for frame in runtime.stream_turn_sse(
                session_id=session_id,
                request=payload,
                request_id=request_id,
            ):
                yield frame
        finally:
            release_session_turn_lock(session_id)

    return StreamingResponse(
        _guarded_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

