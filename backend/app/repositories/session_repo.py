"""Async repository for conversation sessions, message turns, and agent execution traces."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AgentExecutionTrace, ConversationSession, MessageTurn
from app.schemas.common import AgentNameEnum, GroundingStatusEnum, TraceStatusEnum

DEFAULT_SESSION_TITLE = "New Research Session"


class SessionRepository:
    """Data access layer for Table 6, Table 7, and Table 9."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self,
        title: str | None = None,
        use_shared_memory: bool = True,
    ) -> ConversationSession:
        """Insert a new conversation session."""
        resolved_title = title.strip() if title and title.strip() else DEFAULT_SESSION_TITLE
        conv_session = ConversationSession(
            title=resolved_title,
            use_shared_memory=use_shared_memory,
        )
        self._session.add(conv_session)
        await self._session.flush()
        await self._session.refresh(conv_session)
        return conv_session

    async def get_session(self, session_id: uuid.UUID) -> ConversationSession | None:
        """Fetch a single conversation session by UUID."""
        stmt = select(ConversationSession).where(ConversationSession.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_turn_count(self, session_id: uuid.UUID) -> int:
        """Count the number of message turns in a session."""
        stmt = (
            select(func.count(MessageTurn.turn_id))
            .where(MessageTurn.session_id == session_id)
        )
        return int((await self._session.scalar(stmt)) or 0)

    async def update_session(
        self,
        session_id: uuid.UUID,
        *,
        title: str | None = None,
        use_shared_memory: bool | None = None,
    ) -> tuple[ConversationSession, int] | None:
        """Update mutable session fields and return `(session, turn_count)`."""
        conv_session = await self.get_session(session_id)
        if conv_session is None:
            return None

        if title is not None:
            conv_session.title = title.strip()
        if use_shared_memory is not None:
            conv_session.use_shared_memory = use_shared_memory
        conv_session.updated_at = datetime.now(UTC)

        await self._session.flush()
        await self._session.refresh(conv_session)
        turn_count = await self.get_turn_count(session_id)
        return conv_session, turn_count

    async def list_sessions(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[tuple[ConversationSession, int]], int]:
        """Return paginated `(ConversationSession, turn_count)` tuples and total count."""
        clamped_limit = max(1, min(limit, 100))
        clamped_offset = max(0, offset)

        count_stmt = select(func.count(ConversationSession.session_id))
        total = int((await self._session.scalar(count_stmt)) or 0)

        turn_count_subq = (
            select(func.count(MessageTurn.turn_id))
            .where(MessageTurn.session_id == ConversationSession.session_id)
            .correlate(ConversationSession)
            .scalar_subquery()
        )
        stmt = (
            select(ConversationSession, turn_count_subq.label("turn_count"))
            .order_by(ConversationSession.updated_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        rows = (await self._session.execute(stmt)).all()
        items = [(row[0], int(row[1] or 0)) for row in rows]
        return items, total

    async def get_next_turn_index(self, session_id: uuid.UUID) -> int:
        """Compute the next sequential 0-based `turn_index` for a session."""
        stmt = select(func.coalesce(func.max(MessageTurn.turn_index) + 1, 0)).where(
            MessageTurn.session_id == session_id
        )
        return int((await self._session.scalar(stmt)) or 0)

    async def create_message_turn(
        self,
        *,
        session_id: uuid.UUID,
        user_query: str,
        assistant_response: str,
        grounding_status: GroundingStatusEnum,
        citations: dict[str, object],
        total_latency_ms: int,
        turn_index: int | None = None,
    ) -> MessageTurn:
        """Persist a completed message turn and bump the parent session's timestamp."""
        resolved_query = user_query.strip()
        resolved_index = (
            turn_index
            if turn_index is not None
            else await self.get_next_turn_index(session_id)
        )
        turn = MessageTurn(
            session_id=session_id,
            turn_index=resolved_index,
            user_query=resolved_query,
            assistant_response=assistant_response,
            grounding_status=grounding_status.value,
            citations=citations,
            total_latency_ms=max(0, total_latency_ms),
        )
        self._session.add(turn)

        conv_session = await self.get_session(session_id)
        if conv_session is not None:
            if (
                resolved_index == 0
                and conv_session.title == DEFAULT_SESSION_TITLE
                and resolved_query
            ):
                conv_session.title = resolved_query[:120]
            conv_session.updated_at = datetime.now(UTC)

        await self._session.flush()
        await self._session.refresh(turn)
        return turn

    async def create_execution_trace(
        self,
        *,
        turn_id: uuid.UUID,
        step_order: int,
        agent_name: AgentNameEnum,
        action_or_tool: str,
        status: TraceStatusEnum,
        latency_ms: int,
        input_payload: dict[str, object] | None = None,
        output_summary: dict[str, object] | None = None,
    ) -> AgentExecutionTrace:
        """Insert a single agent execution trace step row."""
        trace = AgentExecutionTrace(
            turn_id=turn_id,
            step_order=step_order,
            agent_name=agent_name.value,
            action_or_tool=action_or_tool,
            status=status.value,
            input_payload=input_payload or {},
            output_summary=output_summary or {},
            latency_ms=max(0, latency_ms),
        )
        self._session.add(trace)
        await self._session.flush()
        await self._session.refresh(trace)
        return trace

    async def list_turns_with_traces(
        self,
        session_id: uuid.UUID,
    ) -> list[tuple[MessageTurn, list[AgentExecutionTrace]]]:
        """Fetch all chronological turns for a session along with ordered execution traces."""
        turn_stmt = (
            select(MessageTurn)
            .where(MessageTurn.session_id == session_id)
            .order_by(MessageTurn.turn_index.asc())
        )
        turns = list((await self._session.execute(turn_stmt)).scalars().all())
        if not turns:
            return []

        turn_ids = [t.turn_id for t in turns]
        trace_stmt = (
            select(AgentExecutionTrace)
            .where(AgentExecutionTrace.turn_id.in_(turn_ids))
            .order_by(AgentExecutionTrace.turn_id, AgentExecutionTrace.step_order.asc())
        )
        traces = list((await self._session.execute(trace_stmt)).scalars().all())

        traces_by_turn: dict[uuid.UUID, list[AgentExecutionTrace]] = {tid: [] for tid in turn_ids}
        for trace in traces:
            if trace.turn_id in traces_by_turn:
                traces_by_turn[trace.turn_id].append(trace)

        return [(turn, traces_by_turn.get(turn.turn_id, [])) for turn in turns]

    async def get_recent_session_turns(
        self,
        session_id: uuid.UUID,
        max_turns: int = 6,
    ) -> list[MessageTurn]:
        """Return the most recent `max_turns` turns ordered chronologically for working memory."""
        clamped = max(1, min(max_turns, 20))
        stmt = (
            select(MessageTurn)
            .where(MessageTurn.session_id == session_id)
            .order_by(MessageTurn.turn_index.desc())
            .limit(clamped)
        )
        recent_desc = list((await self._session.execute(stmt)).scalars().all())
        recent_desc.reverse()
        return recent_desc

