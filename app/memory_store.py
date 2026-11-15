import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from google.adk.events import Event
from google.adk.memory import BaseMemoryService
from google.adk.memory.base_memory_service import MemoryEntry, SearchMemoryResponse
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse
from google.genai import types
from pydantic import BaseModel, Field

import app.config as config
from app.database import get_db_connection
from app.embeddings import embed_text, embed_texts, get_genai_client

logger = logging.getLogger(__name__)

MEMORY_DEDUP_SIMILARITY_THRESHOLD = 0.88


class _ExtractedMemoryItem(BaseModel):
    memory_type: str = Field(
        description="Category of memory: 'preference', 'fact', or 'summary'."
    )
    content: str = Field(
        description="Concise, standalone 1-sentence statement worth remembering across sessions."
    )


class _ExtractedMemoryList(BaseModel):
    memories: list[_ExtractedMemoryItem] = Field(default_factory=list)


def _extract_event_text(event: Event) -> str:
    """Extract plain text parts from an ADK Event."""
    if not event.content or not event.content.parts:
        return ""
    texts = [p.text.strip() for p in event.content.parts if getattr(p, "text", None)]
    return "\n".join(t for t in texts if t)


def _derive_session_title(text: str) -> str:
    """Derive a concise single-line session title from the first user prompt."""
    clean = " ".join((text or "").split())
    if not clean:
        return "New Conversation"
    return clean if len(clean) <= 56 else clean[:53].rstrip() + "..."


# ---------------------------------------------------------------------------
# Short-Term Persistent Session Service (Neon PostgreSQL)
# ---------------------------------------------------------------------------


class NeonSessionService(BaseSessionService):
    """
    Persistent Google ADK SessionService backed by Neon PostgreSQL
    (`chat_sessions` and `chat_events` tables), strictly scoped by `user_id`.
    """

    def _create_session_sync(
        self,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]],
        session_id: Optional[str],
    ) -> Session:
        sid = session_id or str(uuid.uuid4())
        now = time.time()
        initial_state = state or {}

        with get_db_connection(register_pgvector=False) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_sessions (id, app_name, user_id, title, state, last_update_time)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (app_name, user_id, id) DO UPDATE
                    SET last_update_time = EXCLUDED.last_update_time
                    RETURNING state, last_update_time;
                    """,
                    (
                        sid,
                        app_name,
                        user_id,
                        "New Conversation",
                        json.dumps(initial_state),
                        now,
                    ),
                )
                row = cur.fetchone()
        return Session(
            id=sid,
            app_name=app_name,
            user_id=user_id,
            state=row[0] if row else initial_state,
            events=[],
            last_update_time=row[1] if row else now,
        )

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        return await asyncio.to_thread(
            self._create_session_sync, app_name, user_id, state, session_id
        )

    def _get_session_sync(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        config_obj: Optional[GetSessionConfig],
    ) -> Optional[Session]:
        with get_db_connection(register_pgvector=False) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT state, last_update_time
                    FROM chat_sessions
                    WHERE app_name = %s AND user_id = %s AND id = %s;
                    """,
                    (app_name, user_id, session_id),
                )
                s_row = cur.fetchone()
                if not s_row:
                    return None

                if config_obj and config_obj.after_timestamp:
                    cur.execute(
                        """
                        SELECT event_data
                        FROM chat_events
                        WHERE app_name = %s AND user_id = %s AND session_id = %s
                          AND timestamp >= %s
                        ORDER BY timestamp ASC;
                        """,
                        (app_name, user_id, session_id, config_obj.after_timestamp),
                    )
                else:
                    cur.execute(
                        """
                        SELECT event_data
                        FROM chat_events
                        WHERE app_name = %s AND user_id = %s AND session_id = %s
                        ORDER BY timestamp ASC;
                        """,
                        (app_name, user_id, session_id),
                    )
                event_rows = cur.fetchall()

        events = [Event.model_validate(r[0]) for r in event_rows]
        if config_obj and config_obj.num_recent_events:
            events = events[-config_obj.num_recent_events :]

        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=s_row[0] or {},
            events=events,
            last_update_time=s_row[1],
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        return await asyncio.to_thread(
            self._get_session_sync, app_name, user_id, session_id, config
        )

    def _list_sessions_sync(
        self, app_name: str, user_id: Optional[str]
    ) -> ListSessionsResponse:
        with get_db_connection(register_pgvector=False) as conn:
            with conn.cursor() as cur:
                if user_id:
                    cur.execute(
                        """
                        SELECT id, user_id, state, last_update_time
                        FROM chat_sessions
                        WHERE app_name = %s AND user_id = %s
                        ORDER BY last_update_time DESC;
                        """,
                        (app_name, user_id),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, user_id, state, last_update_time
                        FROM chat_sessions
                        WHERE app_name = %s
                        ORDER BY last_update_time DESC;
                        """,
                        (app_name,),
                    )
                rows = cur.fetchall()

        sessions = [
            Session(
                id=r[0],
                app_name=app_name,
                user_id=r[1],
                state=r[2] or {},
                events=[],
                last_update_time=r[3],
            )
            for r in rows
        ]
        return ListSessionsResponse(sessions=sessions)

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        return await asyncio.to_thread(self._list_sessions_sync, app_name, user_id)

    def _delete_session_sync(
        self, app_name: str, user_id: str, session_id: str
    ) -> None:
        with get_db_connection(register_pgvector=False) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM chat_sessions
                    WHERE app_name = %s AND user_id = %s AND id = %s;
                    """,
                    (app_name, user_id, session_id),
                )

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        await asyncio.to_thread(
            self._delete_session_sync, app_name, user_id, session_id
        )

    def _append_event_sync(self, session: Session, event: Event) -> Event:
        event_id = event.id or str(uuid.uuid4())
        ts = event.timestamp or time.time()
        payload = event.model_dump(mode="json", exclude_none=True)

        # Apply state delta if present
        if event.actions and event.actions.state_delta:
            session.state.update(event.actions.state_delta)
        session.last_update_time = ts

        user_text = _extract_event_text(event) if event.author == "user" else ""
        derived_title = _derive_session_title(user_text) if user_text else None

        with get_db_connection(register_pgvector=False) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO chat_events
                        (id, session_id, app_name, user_id, author, invocation_id, timestamp, event_data)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    (
                        event_id,
                        session.id,
                        session.app_name,
                        session.user_id,
                        event.author,
                        event.invocation_id,
                        ts,
                        json.dumps(payload),
                    ),
                )
                if derived_title:
                    cur.execute(
                        """
                        UPDATE chat_sessions
                        SET state = %s::jsonb,
                            last_update_time = %s,
                            title = CASE
                                WHEN title = 'New Conversation' THEN %s
                                ELSE title
                            END
                        WHERE app_name = %s AND user_id = %s AND id = %s;
                        """,
                        (
                            json.dumps(session.state),
                            ts,
                            derived_title,
                            session.app_name,
                            session.user_id,
                            session.id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE chat_sessions
                        SET state = %s::jsonb,
                            last_update_time = %s
                        WHERE app_name = %s AND user_id = %s AND id = %s;
                        """,
                        (
                            json.dumps(session.state),
                            ts,
                            session.app_name,
                            session.user_id,
                            session.id,
                        ),
                    )
        return event

    async def append_event(self, session: Session, event: Event) -> Event:
        await super().append_event(session, event)
        return await asyncio.to_thread(self._append_event_sync, session, event)


# ---------------------------------------------------------------------------
# Long-Term Semantic Memory Service (Neon PostgreSQL + pgvector)
# ---------------------------------------------------------------------------


class NeonMemoryService(BaseMemoryService):
    """
    Long-term semantic memory service backed by Neon PostgreSQL (`user_memories`
    with 768-dim `gemini-embedding-001` HNSW + GIN full-text search).
    """

    def _distill_and_store_sync(self, session: Session) -> int:
        if not config.GOOGLE_API_KEY:
            return 0

        transcript_lines: list[str] = []
        for ev in session.events:
            txt = _extract_event_text(ev)
            if not txt:
                continue
            speaker = "User" if ev.author == "user" else "Assistant"
            transcript_lines.append(f"{speaker}: {txt[:800]}")

        if len(transcript_lines) < 2:
            return 0

        transcript = "\n".join(transcript_lines[-12:])
        prompt = (
            "You are a long-term memory distillation engine for an AI assistant. "
            "Extract up to 3 durable, non-trivial memories about the USER from this conversation "
            "(user preferences, formatting instructions, ongoing project context, or key personal/domain facts). "
            "Do NOT extract generic greetings, one-off factual Q&A answers from documents, or trivial chatter. "
            "If nothing is worth remembering long-term, return an empty list.\n\n"
            f"Conversation:\n{transcript}"
        )

        try:
            client = get_genai_client()
            resp = client.models.generate_content(
                model=config.GRAPH_EXTRACTION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_ExtractedMemoryList,
                    temperature=0.1,
                ),
            )
            parsed = _ExtractedMemoryList.model_validate_json(resp.text or "{}")
        except Exception:
            logger.debug("Memory distillation skipped/failed", exc_info=True)
            return 0

        items = [m for m in parsed.memories if m.content and m.content.strip()]
        if not items:
            return 0

        texts = [m.content.strip() for m in items]
        embeddings = embed_texts(texts)

        inserted = 0
        with get_db_connection(register_pgvector=True) as conn:
            with conn.cursor() as cur:
                for item, emb in zip(items, embeddings):
                    mtype = item.memory_type.lower().strip()
                    if mtype not in {"fact", "preference", "summary"}:
                        mtype = "fact"
                    content = item.content.strip()

                    # Deduplicate against existing user memories via cosine similarity
                    cur.execute(
                        """
                        SELECT 1 - (embedding <=> %s::vector) AS sim
                        FROM user_memories
                        WHERE user_id = %s
                        ORDER BY embedding <=> %s::vector ASC
                        LIMIT 1;
                        """,
                        (emb, session.user_id, emb),
                    )
                    top = cur.fetchone()
                    if top and float(top[0]) >= MEMORY_DEDUP_SIMILARITY_THRESHOLD:
                        continue

                    cur.execute(
                        """
                        INSERT INTO user_memories (id, user_id, session_id, memory_type, content, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (str(uuid.uuid4()), session.user_id, session.id, mtype, content, emb),
                    )
                    inserted += 1
        return inserted

    async def add_session_to_memory(self, session: Session) -> None:
        await asyncio.to_thread(self._distill_and_store_sync, session)

    def _search_memory_sync(self, user_id: str, query: str) -> SearchMemoryResponse:
        if not query or not query.strip():
            return SearchMemoryResponse(memories=[])

        q_emb = embed_text(query)
        with get_db_connection(register_pgvector=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        id::text,
                        memory_type,
                        content,
                        created_at,
                        (0.7 * (1 - (embedding <=> %s::vector)))
                        + (0.3 * LEAST(
                            ts_rank_cd(to_tsvector('english', content), plainto_tsquery('english', %s)),
                            1.0
                        )) AS score
                    FROM user_memories
                    WHERE user_id = %s
                    ORDER BY score DESC, created_at DESC
                    LIMIT 5;
                    """,
                    (q_emb, query, user_id),
                )
                rows = cur.fetchall()

        entries: list[MemoryEntry] = []
        for row_id, mtype, content, created_at, score in rows:
            ts_str = (
                created_at.astimezone(timezone.utc).isoformat()
                if isinstance(created_at, datetime)
                else None
            )
            entries.append(
                MemoryEntry(
                    id=row_id,
                    author="user",
                    timestamp=ts_str,
                    custom_metadata={"memory_type": mtype, "score": round(float(score or 0.0), 4)},
                    content=types.Content(
                        role="user",
                        parts=[types.Part(text=f"[{mtype}] {content}")],
                    ),
                )
            )
        return SearchMemoryResponse(memories=entries)

    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        _ = app_name
        return await asyncio.to_thread(self._search_memory_sync, user_id, query)


# ---------------------------------------------------------------------------
# REST API Helpers for Chat History & Memory Governance
# ---------------------------------------------------------------------------


def list_user_chat_sessions(user_id: str, app_name: str = "adk_agentic_rag") -> list[dict[str, Any]]:
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    s.id,
                    s.title,
                    s.last_update_time,
                    s.created_at,
                    COUNT(e.id) FILTER (WHERE e.author = 'user') AS message_count
                FROM chat_sessions s
                LEFT JOIN chat_events e
                  ON e.app_name = s.app_name AND e.user_id = s.user_id AND e.session_id = s.id
                WHERE s.app_name = %s AND s.user_id = %s
                GROUP BY s.id, s.title, s.last_update_time, s.created_at
                ORDER BY s.last_update_time DESC
                LIMIT 50;
                """,
                (app_name, user_id),
            )
            rows = cur.fetchall()

    return [
        {
            "session_id": r[0],
            "title": r[1] or "New Conversation",
            "last_update_time": r[2],
            "created_at": r[3].isoformat() if r[3] else None,
            "message_count": int(r[4] or 0),
        }
        for r in rows
    ]


def get_user_chat_messages(
    user_id: str, session_id: str, app_name: str = "adk_agentic_rag"
) -> list[dict[str, Any]]:
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT author, timestamp, event_data
                FROM chat_events
                WHERE app_name = %s AND user_id = %s AND session_id = %s
                ORDER BY timestamp ASC;
                """,
                (app_name, user_id, session_id),
            )
            rows = cur.fetchall()

    messages: list[dict[str, Any]] = []
    pending_tools: list[str] = []

    for author, ts, data in rows:
        content = data.get("content") or {}
        parts = content.get("parts") or []

        # Collect tool calls made during agent reasoning
        for p in parts:
            fc = p.get("function_call") or p.get("functionCall")
            if fc and fc.get("name"):
                tname = fc["name"]
                if tname not in pending_tools:
                    pending_tools.append(tname)

        text_chunks = [p.get("text", "").strip() for p in parts if p.get("text")]
        full_text = "\n".join(t for t in text_chunks if t)
        if not full_text:
            continue

        if author == "user":
            pending_tools = []
            messages.append({"role": "user", "text": full_text, "timestamp": ts})
        else:
            messages.append(
                {
                    "role": "assistant",
                    "text": full_text,
                    "tools": list(pending_tools),
                    "timestamp": ts,
                }
            )
            pending_tools = []

    return messages


def delete_user_chat_session(
    user_id: str, session_id: str, app_name: str = "adk_agentic_rag"
) -> bool:
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM chat_sessions
                WHERE app_name = %s AND user_id = %s AND id = %s;
                """,
                (app_name, user_id, session_id),
            )
            return cur.rowcount > 0


def list_user_memories(user_id: str) -> list[dict[str, Any]]:
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id::text, memory_type, content, session_id, created_at
                FROM user_memories
                WHERE user_id = %s
                ORDER BY created_at DESC;
                """,
                (user_id,),
            )
            rows = cur.fetchall()

    return [
        {
            "memory_id": r[0],
            "memory_type": r[1],
            "content": r[2],
            "session_id": r[3],
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]


def add_manual_memory(
    user_id: str, content: str, memory_type: str = "preference"
) -> dict[str, Any]:
    clean_content = content.strip()
    if not clean_content:
        raise ValueError("Memory content cannot be empty.")

    mtype = memory_type.lower().strip()
    if mtype not in {"fact", "preference", "summary"}:
        mtype = "preference"

    emb = embed_text(clean_content)
    mem_id = str(uuid.uuid4())
    with get_db_connection(register_pgvector=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_memories (id, user_id, session_id, memory_type, content, embedding)
                VALUES (%s, %s, NULL, %s, %s, %s)
                RETURNING created_at;
                """,
                (mem_id, user_id, mtype, clean_content, emb),
            )
            created_at = cur.fetchone()[0]

    return {
        "memory_id": mem_id,
        "memory_type": mtype,
        "content": clean_content,
        "session_id": None,
        "created_at": created_at.isoformat() if created_at else None,
    }


def delete_user_memory(user_id: str, memory_id: str) -> bool:
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM user_memories
                WHERE id = %s::uuid AND user_id = %s;
                """,
                (memory_id, user_id),
            )
            return cur.rowcount > 0


def delete_all_user_memories(user_id: str) -> int:
    with get_db_connection(register_pgvector=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_memories WHERE user_id = %s;",
                (user_id,),
            )
            return cur.rowcount
