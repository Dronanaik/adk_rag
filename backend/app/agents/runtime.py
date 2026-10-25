"""Google ADK 5-agent hierarchy and SSE turn execution runtime (ARCHITECTURE.md Section 5)."""

import re
import time
from collections.abc import AsyncIterator
from uuid import UUID

import structlog
from google.adk.agents import LlmAgent
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.citation_verifier import CitationVerificationResult
from app.agents.prompts import (
    KG_RETRIEVER_INSTRUCTION,
    MEMORY_AGENT_INSTRUCTION,
    ORCHESTRATOR_INSTRUCTION,
    SYNTHESIS_VERIFIER_INSTRUCTION,
    VECTOR_RETRIEVER_INSTRUCTION,
    format_sandboxed_evidence,
)
from app.agents.state import AgentTraceEntryState, TurnWorkingState
from app.agents.tools import (
    TurnToolRuntimeContext,
    build_adk_function_tools,
    execute_consolidate_verified_memory,
    execute_recall_centralized_memory,
    execute_search_document_chunks,
    execute_traverse_knowledge_graph,
    execute_verify_and_format_citations,
)
from app.config import Settings, get_settings
from app.repositories.session_repo import SessionRepository
from app.repositories.settings_repo import SettingsRepository
from app.schemas.common import AgentNameEnum, GroundingStatusEnum, TraceStatusEnum
from app.schemas.sessions import (
    AgentExecutionTraceItem,
    AgentStepCounts,
    AgentStepSseEvent,
    ErrorSseEvent,
    TokenSseEvent,
    TurnCompleteSseEvent,
    TurnCreateRequest,
)
from app.services.gemini_service import GeminiService

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_STOPWORDS: frozenset[str] = frozenset(
    {
        "What",
        "Which",
        "Where",
        "When",
        "Who",
        "How",
        "Why",
        "Does",
        "Do",
        "Is",
        "Are",
        "Can",
        "Could",
        "Should",
        "Would",
        "The",
        "This",
        "That",
        "These",
        "Those",
        "Tell",
        "Explain",
        "Describe",
        "List",
        "Show",
        "Give",
        "Find",
    }
)


def build_adk_agent_hierarchy(
    ctx: TurnToolRuntimeContext,
    model_name: str = "gemini-2.5-flash",
) -> LlmAgent:
    """Construct the Google ADK 5-agent hierarchy bound to the turn tool context."""
    tools = build_adk_function_tools(ctx)
    memory_agent = LlmAgent(
        name="MemoryAgent",
        model=model_name,
        description="Manages Centralized Memory recall and verified post-turn fact consolidation.",
        instruction=MEMORY_AGENT_INSTRUCTION,
        tools=[tools["recall_centralized_memory"]],
    )
    vector_agent = LlmAgent(
        name="VectorRetriever",
        model=model_name,
        description="Executes hybrid pgvector + PostgreSQL full-text search with RRF.",
        instruction=VECTOR_RETRIEVER_INSTRUCTION,
        tools=[tools["search_document_chunks"]],
    )
    kg_agent = LlmAgent(
        name="KGRetriever",
        model=model_name,
        description="Resolves seed entities and traverses 1-2 hop Knowledge Graph subgraphs.",
        instruction=KG_RETRIEVER_INSTRUCTION,
        tools=[tools["traverse_knowledge_graph"]],
    )
    synthesis_agent = LlmAgent(
        name="SynthesisVerifier",
        model=model_name,
        description="Synthesizes grounded responses with inline [Doc:N], [KG:N], [Mem:N] badges.",
        instruction=SYNTHESIS_VERIFIER_INSTRUCTION,
        tools=[tools["verify_and_format_citations"]],
    )
    return LlmAgent(
        name="Orchestrator",
        model=model_name,
        description="Root coordinator decomposing queries and routing across specialist agents.",
        instruction=ORCHESTRATOR_INSTRUCTION,
        sub_agents=[memory_agent, vector_agent, kg_agent, synthesis_agent],
    )


def extract_query_entity_candidates(user_query: str) -> list[str]:
    """Extract candidate entity names and technical identifiers from a user query."""
    candidates: list[str] = []
    capitalized_matches = re.findall(
        r"\b([A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*)*)\b",
        user_query,
    )
    for phrase in capitalized_matches:
        cleaned = " ".join(w for w in phrase.split() if w not in _STOPWORDS).strip()
        if len(cleaned) >= 2 and cleaned not in candidates:
            candidates.append(cleaned)

    hyphenated_matches = re.findall(r"\b([a-zA-Z0-9]+-[a-zA-Z0-9-]+)\b", user_query)
    for token in hyphenated_matches:
        if len(token) >= 3 and token not in candidates:
            candidates.append(token)

    if not candidates:
        words = [
            w.strip(".,?!:;\"'()[]{}")
            for w in user_query.split()
            if len(w.strip(".,?!:;\"'()[]{}")) >= 4
        ]
        for word in words[:4]:
            if word.capitalize() not in _STOPWORDS and word not in candidates:
                candidates.append(word)
    return candidates[:8]


def format_sse_event(event_name: str, payload: BaseModel) -> str:
    """Serialize a Pydantic SSE event model into a wire-compliant text/event-stream frame."""
    return f"event: {event_name}\ndata: {payload.model_dump_json()}\n\n"


def _build_deterministic_synthesis(ctx: TurnToolRuntimeContext) -> str:
    """Synthesize a deterministic grounded Markdown answer from retrieved evidence pools."""
    sections: list[str] = []
    if ctx.state.retrieved_chunks:
        chunk_lines: list[str] = []
        for chunk in ctx.state.retrieved_chunks[:3]:
            snippet = " ".join(chunk.excerpt.strip().split())
            if len(snippet) > 220:
                snippet = f"{snippet[:217]}..."
            chunk_lines.append(
                f"- **{chunk.document_title}**: {snippet} [Doc:{chunk.badge_index}]"
            )
        sections.append("### Document Evidence\n" + "\n".join(chunk_lines))

    if ctx.state.retrieved_kg_paths:
        kg_lines = [
            f"- **{p.path_summary}**: {p.evidence_snippet} [KG:{p.badge_index}]"
            for p in ctx.state.retrieved_kg_paths[:4]
        ]
        sections.append("### Knowledge Graph Relationships\n" + "\n".join(kg_lines))

    if ctx.state.retrieved_memories:
        mem_lines = [
            f"- {m.content} [Mem:{m.badge_index}]"
            for m in ctx.state.retrieved_memories[:2]
        ]
        sections.append("### Recalled Centralized Memory\n" + "\n".join(mem_lines))

    return "\n\n".join(sections)


def _extract_verified_facts_for_memory(ctx: TurnToolRuntimeContext) -> list[str]:
    """Extract concise verified atomic statements from cited evidence for D-04 consolidation."""
    facts: list[str] = []
    for path in ctx.state.retrieved_kg_paths[:3]:
        fact = f"{path.path_summary} ({path.evidence_snippet})"
        if len(fact) <= 450:
            facts.append(fact)
    if not facts and ctx.state.retrieved_chunks:
        first_chunk = ctx.state.retrieved_chunks[0]
        first_sentence = first_chunk.excerpt.strip().split(".")[0].strip()
        if len(first_sentence) >= 15:
            facts.append(f"{first_chunk.document_title}: {first_sentence}.")
    return facts[:3]


def _chunk_markdown_tokens(markdown_text: str, chunk_size: int = 48) -> list[str]:
    """Split verified Markdown into streaming token chunks preserving exact characters."""
    if not markdown_text:
        return []
    return [
        markdown_text[idx : idx + chunk_size]
        for idx in range(0, len(markdown_text), chunk_size)
    ]


class _ResolvedTurnConfig:
    """Resolved per-turn retrieval parameters merging DB settings and request overrides."""

    def __init__(
        self,
        *,
        top_k_chunks: int,
        max_kg_hops: int,
        include_shared_memory: bool,
        similarity_threshold: float,
        memory_Floor: float,
        strict_abstention: bool,
        auto_consolidate_memory: bool,
    ) -> None:
        self.top_k_chunks = top_k_chunks
        self.max_kg_hops = max_kg_hops
        self.include_shared_memory = include_shared_memory
        self.similarity_threshold = similarity_threshold
        self.memory_Floor = memory_Floor
        self.strict_abstention = strict_abstention
        self.auto_consolidate_memory = auto_consolidate_memory


class _PendingTraceRecord:
    """In-memory trace record awaiting persistence after the MessageTurn is created."""

    def __init__(
        self,
        *,
        step_order: int,
        agent_name: AgentNameEnum,
        action_or_tool: str,
        status: TraceStatusEnum,
        latency_ms: int,
        input_payload: dict[str, object],
        output_summary: dict[str, object],
    ) -> None:
        self.step_order = step_order
        self.agent_name = agent_name
        self.action_or_tool = action_or_tool
        self.status = status
        self.latency_ms = latency_ms
        self.input_payload = input_payload
        self.output_summary = output_summary


class AgentRuntimeService:
    """Service orchestrating the 5-agent Google ADK turn execution and SSE streaming."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
        gemini_service: GeminiService | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._gemini = gemini_service or GeminiService(self._settings)
        self._session_repo = SessionRepository(session)
        self._settings_repo = SettingsRepository(session)

    async def _resolve_turn_config(
        self,
        session_id: UUID,
        request: TurnCreateRequest,
    ) -> _ResolvedTurnConfig:
        """Merge persisted SystemSetting and ConversationSession with request overrides."""
        db_settings = await self._settings_repo.get_settings()
        conv_session = await self._session_repo.get_session(session_id)
        session_shared = conv_session.use_shared_memory if conv_session is not None else True
        include_shared = (
            request.use_shared_memory
            if request.use_shared_memory is not None
            else session_shared
        )
        return _ResolvedTurnConfig(
            top_k_chunks=db_settings.top_k_chunks,
            max_kg_hops=db_settings.max_kg_hops,
            include_shared_memory=include_shared,
            similarity_threshold=float(db_settings.similarity_threshold),
            memory_Floor=self._settings.MIN_SIMILARITY_THRESHOLD,
            strict_abstention=db_settings.strict_abstention_mode,
            auto_consolidate_memory=db_settings.auto_consolidate_memory,
        )

    def _record_trace_step(
        self,
        ctx: TurnToolRuntimeContext,
        *,
        step_order: int,
        agent_name: AgentNameEnum,
        action_or_tool: str,
        status: TraceStatusEnum,
        summary: str,
        latency_ms: int,
        input_payload: dict[str, object],
        output_payload: dict[str, object],
    ) -> tuple[AgentStepSseEvent, _PendingTraceRecord]:
        """Record a completed agent step in TurnWorkingState and return SSE + trace records."""
        ctx.state.agent_trace_steps.append(
            AgentTraceEntryState(
                step_order=step_order,
                agent_name=agent_name.value,
                tool_name=action_or_tool,
                status=status,
                duration_ms=max(latency_ms, 0),
                summary=summary,
            )
        )
        counts = AgentStepCounts(
            chunks=len(ctx.state.retrieved_chunks),
            kg_edges=len(ctx.state.retrieved_kg_paths),
            memories=len(ctx.state.retrieved_memories),
        )
        sse_ev = AgentStepSseEvent(
            step_order=step_order,
            agent_name=agent_name,
            action_or_tool=action_or_tool,
            status=status,
            summary=summary,
            counts=counts,
            latency_ms=max(latency_ms, 0),
        )
        trace_rec = _PendingTraceRecord(
            step_order=step_order,
            agent_name=agent_name,
            action_or_tool=action_or_tool,
            status=status,
            latency_ms=max(latency_ms, 0),
            input_payload=input_payload,
            output_summary={"summary": summary, **output_payload},
        )
        return sse_ev, trace_rec

    async def _run_memory_step(
        self,
        ctx: TurnToolRuntimeContext,
        session_id: UUID,
        cfg: _ResolvedTurnConfig,
    ) -> tuple[AgentStepSseEvent, _PendingTraceRecord, bool, str | None]:
        """Execute Step 2 (MemoryAgent recall) with fault-tolerant fallback."""
        t0 = time.perf_counter()
        action = "recall_centralized_memory"
        in_payload: dict[str, object] = {
            "query_text": ctx.state.user_query,
            "include_shared_memory": cfg.include_shared_memory,
        }
        try:
            mem_out = await execute_recall_centralized_memory(
                ctx,
                query_text=ctx.state.user_query,
                session_id=session_id,
                include_shared_memory=cfg.include_shared_memory,
                min_similarity=cfg.memory_Floor,
            )
            ms = int((time.perf_counter() - t0) * 1000)
            summary = f"Recalled {mem_out['recalled_count']} relevant memory entries."
            ev, rec = self._record_trace_step(
                ctx,
                step_order=2,
                agent_name=AgentNameEnum.MEMORY_AGENT,
                action_or_tool=action,
                status=TraceStatusEnum.SUCCESS,
                summary=summary,
                latency_ms=ms,
                input_payload=in_payload,
                output_payload={"recalled_count": mem_out["recalled_count"]},
            )
            return ev, rec, False, None
        except Exception as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            warn = "Centralized Memory recall degraded; continuing with document and KG retrieval."
            logger.warning("memory_recall_fallback", error=str(exc), session_id=str(session_id))
            ev, rec = self._record_trace_step(
                ctx,
                step_order=2,
                agent_name=AgentNameEnum.MEMORY_AGENT,
                action_or_tool=action,
                status=TraceStatusEnum.FALLBACK,
                summary=warn,
                latency_ms=ms,
                input_payload=in_payload,
                output_payload={"error": str(exc)},
            )
            return ev, rec, True, warn

    async def _run_vector_step(
        self,
        ctx: TurnToolRuntimeContext,
        cfg: _ResolvedTurnConfig,
    ) -> tuple[AgentStepSseEvent, _PendingTraceRecord, bool, str | None]:
        """Execute Step 3 (VectorRetriever hybrid search) with fault-tolerant fallback."""
        t0 = time.perf_counter()
        action = "search_document_chunks"
        in_payload: dict[str, object] = {
            "sub_query": ctx.state.user_query,
            "top_k": cfg.top_k_chunks,
            "min_similarity": cfg.similarity_threshold,
        }
        try:
            vec_out = await execute_search_document_chunks(
                ctx,
                sub_query=ctx.state.user_query,
                top_k=cfg.top_k_chunks,
                min_similarity=cfg.similarity_threshold,
            )
            ms = int((time.perf_counter() - t0) * 1000)
            summary = f"Retrieved {vec_out['retrieved_count']} ranked document chunks via RRF."
            ev, rec = self._record_trace_step(
                ctx,
                step_order=3,
                agent_name=AgentNameEnum.VECTOR_RETRIEVER,
                action_or_tool=action,
                status=TraceStatusEnum.SUCCESS,
                summary=summary,
                latency_ms=ms,
                input_payload=in_payload,
                output_payload={"retrieved_count": vec_out["retrieved_count"]},
            )
            return ev, rec, False, None
        except Exception as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            warn = (
                "Document vector search degraded; continuing with surviving retrieval modalities."
            )
            logger.warning("vector_search_fallback", error=str(exc))
            ev, rec = self._record_trace_step(
                ctx,
                step_order=3,
                agent_name=AgentNameEnum.VECTOR_RETRIEVER,
                action_or_tool=action,
                status=TraceStatusEnum.FALLBACK,
                summary=warn,
                latency_ms=ms,
                input_payload=in_payload,
                output_payload={"error": str(exc)},
            )
            return ev, rec, True, warn

    async def _run_kg_step(
        self,
        ctx: TurnToolRuntimeContext,
        cfg: _ResolvedTurnConfig,
    ) -> tuple[AgentStepSseEvent, _PendingTraceRecord, bool, str | None]:
        """Execute Step 4 (KGRetriever traversal) with fault-tolerant modality degradation."""
        t0 = time.perf_counter()
        action = "traverse_knowledge_graph"
        in_payload: dict[str, object] = {
            "candidate_entities": ctx.state.entity_candidates,
            "max_hops": cfg.max_kg_hops,
        }
        try:
            kg_out = await execute_traverse_knowledge_graph(
                ctx,
                candidate_entities=ctx.state.entity_candidates,
                max_hops=cfg.max_kg_hops,
            )
            ms = int((time.perf_counter() - t0) * 1000)
            summary = (
                f"Resolved {len(kg_out['resolved_entities'])} entities and "
                f"traversed {len(kg_out['kg_paths'])} KG relationship paths."
            )
            ev, rec = self._record_trace_step(
                ctx,
                step_order=4,
                agent_name=AgentNameEnum.KG_RETRIEVER,
                action_or_tool=action,
                status=TraceStatusEnum.SUCCESS,
                summary=summary,
                latency_ms=ms,
                input_payload=in_payload,
                output_payload={
                    "resolved_entity_count": len(kg_out["resolved_entities"]),
                    "kg_path_count": len(kg_out["kg_paths"]),
                },
            )
            return ev, rec, False, None
        except Exception as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            warn = (
                "Knowledge Graph traversal timed out or failed; synthesized answer using "
                "Document Vector Retrieval and Centralized Memory only."
            )
            logger.warning("kg_traversal_fallback", error=str(exc))
            ev, rec = self._record_trace_step(
                ctx,
                step_order=4,
                agent_name=AgentNameEnum.KG_RETRIEVER,
                action_or_tool=action,
                status=TraceStatusEnum.FALLBACK,
                summary=warn,
                latency_ms=ms,
                input_payload=in_payload,
                output_payload={"error": str(exc)},
            )
            return ev, rec, True, warn

    async def _generate_draft_markdown(self, ctx: TurnToolRuntimeContext) -> str:
        """Generate draft Markdown using live Gemini when configured, or deterministic fallback."""
        draft = _build_deterministic_synthesis(ctx)
        has_evidence = bool(
            ctx.state.retrieved_chunks
            or ctx.state.retrieved_kg_paths
            or ctx.state.retrieved_memories
        )
        if not self._gemini.is_live_configured or not has_evidence:
            return draft

        evidence_xml = format_sandboxed_evidence(
            chunks=[
                (f"Doc:{c.badge_index}", c.document_title, c.excerpt)
                for c in ctx.state.retrieved_chunks
            ],
            kg_paths=[
                (f"KG:{p.badge_index}", p.path_summary, p.evidence_snippet)
                for p in ctx.state.retrieved_kg_paths
            ],
            memories=[
                (f"Mem:{m.badge_index}", m.memory_tier, m.content)
                for m in ctx.state.retrieved_memories
            ],
        )
        prompt = f"User Query: {ctx.state.user_query}\n\nRetrieved Evidence:\n{evidence_xml}"
        try:
            live_text = await self._gemini.generate_grounded_synthesis(
                prompt=prompt,
                system_instruction=SYNTHESIS_VERIFIER_INSTRUCTION,
            )
            return live_text if live_text else draft
        except Exception as exc:
            logger.warning("live_synthesis_fallback_to_deterministic", error=str(exc))
            return draft

    async def _synthesize_and_verify(
        self,
        ctx: TurnToolRuntimeContext,
        cfg: _ResolvedTurnConfig,
        has_degradation: bool,
    ) -> tuple[CitationVerificationResult, AgentStepSseEvent, _PendingTraceRecord]:
        """Execute Step 5 (SynthesisVerifier) and return verified citation result + trace."""
        t0 = time.perf_counter()
        draft = await self._generate_draft_markdown(ctx)
        verification = execute_verify_and_format_citations(
            ctx,
            draft_markdown=draft,
            similarity_threshold=cfg.similarity_threshold,
            strict_abstention_mode=cfg.strict_abstention,
            has_modality_degradation=has_degradation,
            searched_entities=ctx.state.entity_candidates,
            searched_queries=ctx.state.sub_queries,
        )
        ms = int((time.perf_counter() - t0) * 1000)
        summary = (
            f"Verified response grounding: {verification.grounding_status.value} "
            f"(score={verification.grounding_score:.2f}, "
            f"citations={len(verification.valid_citation_keys)})."
        )
        ev, rec = self._record_trace_step(
            ctx,
            step_order=5,
            agent_name=AgentNameEnum.SYNTHESIS_VERIFIER,
            action_or_tool="verify_and_format_citations",
            status=TraceStatusEnum.SUCCESS,
            summary=summary,
            latency_ms=ms,
            input_payload={"strict_abstention_mode": cfg.strict_abstention},
            output_payload={
                "grounding_status": verification.grounding_status.value,
                "grounding_score": verification.grounding_score,
                "valid_citation_keys": verification.valid_citation_keys,
            },
        )
        return verification, ev, rec

    async def _persist_turn_and_traces(
        self,
        ctx: TurnToolRuntimeContext,
        session_id: UUID,
        user_query: str,
        cfg: _ResolvedTurnConfig,
        verification: CitationVerificationResult,
        trace_records: list[_PendingTraceRecord],
        total_latency_ms: int,
    ) -> tuple[UUID, int, list[AgentExecutionTraceItem]]:
        """Persist MessageTurn, D-04 memory consolidation, and AgentExecutionTrace rows."""
        turn = await self._session_repo.create_message_turn(
            session_id=session_id,
            user_query=user_query,
            assistant_response=verification.verified_markdown,
            grounding_status=verification.grounding_status,
            citations=verification.citations.model_dump(mode="json"),
            total_latency_ms=total_latency_ms,
        )

        cited_chunks = [c.chunk_id for c in verification.citations.chunks]
        supporting_chunks = cited_chunks or [
            UUID(c.chunk_id) for c in ctx.state.retrieved_chunks[:2]
        ]
        if (
            cfg.auto_consolidate_memory
            and verification.grounding_status == GroundingStatusEnum.GROUNDED
            and supporting_chunks
        ):
            verified_facts = _extract_verified_facts_for_memory(ctx)
            if verified_facts:
                await execute_consolidate_verified_memory(
                    ctx,
                    verified_facts=verified_facts,
                    turn_id=turn.turn_id,
                    supporting_chunk_ids=supporting_chunks,
                    entity_ids=[n.entity_id for n in ctx.subgraph.nodes[:5]],
                    grounding_status=verification.grounding_status,
                )

        trace_items: list[AgentExecutionTraceItem] = []
        for rec in trace_records:
            row = await self._session_repo.create_execution_trace(
                turn_id=turn.turn_id,
                step_order=rec.step_order,
                agent_name=rec.agent_name,
                action_or_tool=rec.action_or_tool,
                status=rec.status,
                latency_ms=rec.latency_ms,
                input_payload=rec.input_payload,
                output_summary=rec.output_summary,
            )
            trace_items.append(AgentExecutionTraceItem.model_validate(row))

        await self._session.commit()
        return turn.turn_id, turn.turn_index, trace_items

    async def _execute_retrieval_pipeline(
        self,
        ctx: TurnToolRuntimeContext,
        session_id: UUID,
        cfg: _ResolvedTurnConfig,
        turn_start: float,
    ) -> tuple[list[AgentStepSseEvent], list[_PendingTraceRecord], bool, str | None]:
        """Run Orchestrator, MemoryAgent, VectorRetriever, and KGRetriever steps."""
        entities = ctx.state.entity_candidates
        intent = ctx.state.query_intent
        orch_ev, orch_rec = self._record_trace_step(
            ctx,
            step_order=1,
            agent_name=AgentNameEnum.ORCHESTRATOR,
            action_or_tool="decompose_and_route_query",
            status=TraceStatusEnum.SUCCESS,
            summary=f"Intent: {intent} | Candidate entities: {', '.join(entities) or 'none'}",
            latency_ms=int((time.perf_counter() - turn_start) * 1000),
            input_payload={"user_query": ctx.state.user_query},
            output_payload={"intent": intent, "entity_candidates": entities},
        )
        mem_ev, mem_rec, mem_deg, mem_warn = await self._run_memory_step(ctx, session_id, cfg)
        vec_ev, vec_rec, vec_deg, vec_warn = await self._run_vector_step(ctx, cfg)
        kg_ev, kg_rec, kg_deg, kg_warn = await self._run_kg_step(ctx, cfg)

        has_deg = mem_deg or vec_deg or kg_deg
        fallback_warning = kg_warn or vec_warn or mem_warn
        return (
            [orch_ev, mem_ev, vec_ev, kg_ev],
            [orch_rec, mem_rec, vec_rec, kg_rec],
            has_deg,
            fallback_warning,
        )

    async def stream_turn_sse(
        self,
        session_id: UUID,
        request: TurnCreateRequest,
        *,
        request_id: str = "req_turn_stream",
    ) -> AsyncIterator[str]:
        """Execute a complete 5-agent turn and yield wire-formatted SSE event frames."""
        turn_start = time.perf_counter()
        try:
            cfg = await self._resolve_turn_config(session_id, request)
            entities = extract_query_entity_candidates(request.user_query)
            intent = "MULTI_HOP_ANALYTICAL" if entities else "SEMANTIC_LOOKUP"
            state = TurnWorkingState(
                session_id=str(session_id),
                turn_id="pending",
                user_query=request.user_query,
                query_intent=intent,
                sub_queries=[request.user_query],
                entity_candidates=entities,
            )
            ctx = TurnToolRuntimeContext(
                self._session, state, settings=self._settings, gemini_service=self._gemini
            )
            _ = build_adk_agent_hierarchy(ctx, self._settings.GEMINI_FAST_MODEL)

            events, records, has_deg, warn = await self._execute_retrieval_pipeline(
                ctx, session_id, cfg, turn_start
            )
            for ev in events:
                yield format_sse_event("agent_step", ev)

            verification, syn_ev, syn_rec = await self._synthesize_and_verify(ctx, cfg, has_deg)
            records.append(syn_rec)
            yield format_sse_event("agent_step", syn_ev)

            for chunk in _chunk_markdown_tokens(verification.verified_markdown):
                yield format_sse_event("token", TokenSseEvent(delta=chunk))

            total_ms = int((time.perf_counter() - turn_start) * 1000)
            turn_id, turn_index, trace_items = await self._persist_turn_and_traces(
                ctx, session_id, request.user_query, cfg, verification, records, total_ms
            )
            complete_ev = TurnCompleteSseEvent(
                turn_id=turn_id,
                turn_index=turn_index,
                assistant_response=verification.verified_markdown,
                grounding_status=verification.grounding_status,
                fallback_warning=warn,
                abstention_diagnostics=verification.abstention_diagnostics,
                citations=verification.citations,
                subgraph=ctx.subgraph,
                agent_execution_traces=trace_items,
                total_latency_ms=total_ms,
            )
            yield format_sse_event("turn_complete", complete_ev)
        except Exception as exc:
            logger.error("turn_stream_failed", error=str(exc), session_id=str(session_id))
            err_ev = ErrorSseEvent(
                code="INTERNAL_SERVER_ERROR",
                message=f"Turn execution failed: {exc}",
                retryable=True,
                request_id=request_id,
            )
            yield format_sse_event("error", err_ev)
