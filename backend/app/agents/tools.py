"""Typed Google ADK FunctionTool implementations for the 5-agent hierarchy (API.md Section 4)."""

from typing import TypedDict
from uuid import UUID

from google.adk.tools import FunctionTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.citation_verifier import (
    CitationVerificationResult,
    HydratedTurnEvidence,
    verify_synthesis_grounding,
)
from app.agents.state import (
    CitationMappingItem,
    RetrievedChunkStateItem,
    RetrievedGraphPathStateItem,
    RetrievedMemoryStateItem,
    TurnWorkingState,
)
from app.config import Settings, get_settings
from app.repositories.document_repo import DocumentRepository
from app.repositories.kg_repo import KnowledgeGraphRepository
from app.schemas.common import GroundingStatusEnum, MemoryTierEnum, ProvenanceModalityEnum
from app.schemas.kg import KgEntitySummary, KgRelationshipItem, SubgraphEdgeRow
from app.schemas.memory import MemoryEntryItem, VerifiedFactCandidate
from app.schemas.sessions import (
    CitedChunkItem,
    CitedKgPathItem,
    CitedMemoryItem,
    TurnSubgraphEnvelope,
)
from app.services.gemini_service import GeminiService
from app.services.hybrid_search_service import HybridChunkMatch, HybridSearchService
from app.services.kg_explorer_service import to_kg_entity_summary
from app.services.memory_service import MemoryService


class RecalledMemoryDict(TypedDict):
    """Serialized memory item returned by recall_centralized_memory."""

    citation_key: str
    memory_id: str
    memory_tier: str
    content: str
    confidence: float


class RecallMemoryToolOutput(TypedDict):
    """Structured dictionary returned by recall_centralized_memory."""

    recalled_count: int
    recalled_memories: list[RecalledMemoryDict]


class RetrievedChunkDict(TypedDict):
    """Serialized chunk item returned by search_document_chunks."""

    citation_key: str
    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    excerpt: str
    similarity_score: float
    rrf_score: float


class SearchChunksToolOutput(TypedDict):
    """Structured dictionary returned by search_document_chunks."""

    retrieved_count: int
    retrieved_chunks: list[RetrievedChunkDict]


class ResolvedEntityDict(TypedDict):
    """Serialized KG entity item returned by resolve_seed_entities."""

    entity_id: str
    canonical_name: str
    entity_type: str
    description: str


class KgPathDict(TypedDict):
    """Serialized KG triple path item returned by traverse_knowledge_graph."""

    citation_key: str
    edge_id: str
    source_entity: str
    relation_type: str
    target_entity: str
    evidence_snippet: str
    confidence: float
    source_chunk_id: str
    document_title: str


class TraverseKgToolOutput(TypedDict):
    """Structured dictionary returned by traverse_knowledge_graph."""

    resolved_entities: list[ResolvedEntityDict]
    kg_paths: list[KgPathDict]
    backing_chunk_ids: list[str]


class VerifyCitationsToolOutput(TypedDict):
    """Structured dictionary returned by verify_and_format_citations."""

    verified_markdown: str
    grounding_status: str
    grounding_score: float
    valid_citation_keys: list[str]
    stripped_phantom_keys: list[str]


class ConsolidateMemoryToolOutput(TypedDict):
    """Structured dictionary returned by consolidate_verified_memory."""

    created_memory_ids: list[str]
    superseded_memory_ids: list[str]
    skipped_duplicate_count: int


class TurnToolRuntimeContext:
    """Per-turn stateful tool execution context shared across the 5 ADK agents."""

    def __init__(
        self,
        session: AsyncSession,
        working_state: TurnWorkingState,
        *,
        settings: Settings | None = None,
        gemini_service: GeminiService | None = None,
    ) -> None:
        self.db_session = session
        self.state = working_state
        self.settings = settings or get_settings()
        self.gemini = gemini_service or GeminiService(self.settings)
        self.memory_service = MemoryService(
            session, settings=self.settings, gemini_service=self.gemini
        )
        self.hybrid_search = HybridSearchService(
            session, settings=self.settings, gemini_service=self.gemini
        )
        self.kg_repo = KnowledgeGraphRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.chunks_by_key: dict[str, CitedChunkItem] = {}
        self.kg_paths_by_key: dict[str, CitedKgPathItem] = {}
        self.memories_by_key: dict[str, CitedMemoryItem] = {}
        self.subgraph = TurnSubgraphEnvelope()

    def get_hydrated_evidence(self) -> HydratedTurnEvidence:
        """Return a snapshot of hydrated citation pools for verification."""
        return HydratedTurnEvidence(
            chunks_by_key=dict(self.chunks_by_key),
            kg_paths_by_key=dict(self.kg_paths_by_key),
            memories_by_key=dict(self.memories_by_key),
        )


def _register_memory_item(
    ctx: TurnToolRuntimeContext,
    item: MemoryEntryItem,
) -> RecalledMemoryDict:
    """Register a recalled memory entry in TurnWorkingState and return its tool dict."""
    badge_index = len(ctx.state.retrieved_memories) + 1
    citation_key = f"Mem:{badge_index}"
    raw_conf = float(item.similarity_score if item.similarity_score is not None else 0.85)
    conf = min(max(raw_conf, 0.0), 1.0)
    ctx.state.retrieved_memories.append(
        RetrievedMemoryStateItem(
            badge_index=badge_index,
            memory_id=str(item.memory_id),
            memory_tier=item.memory_tier.value,
            key_name=citation_key,
            content=item.content,
            confidence=conf,
        )
    )
    ctx.state.citation_map.append(
        CitationMappingItem(
            badge_id=citation_key,
            modality=ProvenanceModalityEnum.MEM,
            badge_index=badge_index,
            target_id=str(item.memory_id),
            display_label=f"#{str(item.memory_id)[:8]}",
        )
    )
    ctx.memories_by_key[citation_key] = CitedMemoryItem(
        citation_key=citation_key,
        memory_id=item.memory_id,
        memory_tier=item.memory_tier,
        content=item.content,
        source_turn_id=item.source_turn_id,
        supporting_chunk_ids=item.supporting_chunk_ids,
        created_at=item.created_at,
    )
    return RecalledMemoryDict(
        citation_key=citation_key,
        memory_id=str(item.memory_id),
        memory_tier=item.memory_tier.value,
        content=item.content,
        confidence=round(conf, 4),
    )


async def execute_recall_centralized_memory(
    ctx: TurnToolRuntimeContext,
    *,
    query_text: str,
    session_id: UUID,
    include_shared_memory: bool = True,
    min_similarity: float = 0.55,
    top_k: int = 5,
) -> RecallMemoryToolOutput:
    """Execute Centralized Memory recall and populate TurnWorkingState.retrieved_memories."""
    recalled_items = await ctx.memory_service.recall_for_turn(
        query_text=query_text,
        session_id=session_id,
        include_shared=include_shared_memory,
        min_similarity=min_similarity,
        top_k=top_k,
    )
    serialized = [_register_memory_item(ctx, item) for item in recalled_items]
    return RecallMemoryToolOutput(
        recalled_count=len(serialized),
        recalled_memories=serialized,
    )


def _register_chunk_match(
    ctx: TurnToolRuntimeContext,
    match: HybridChunkMatch,
) -> RetrievedChunkDict:
    """Register a retrieved document chunk in TurnWorkingState and return its tool dict."""
    cid_str = str(match.chunk_id)
    badge_index = len(ctx.state.retrieved_chunks) + 1
    citation_key = f"Doc:{badge_index}"
    ctx.state.retrieved_chunks.append(
        RetrievedChunkStateItem(
            badge_index=badge_index,
            chunk_id=cid_str,
            document_id=str(match.document_id),
            document_title=match.document_title,
            section_title=match.section_heading,
            page_number=match.page_number,
            excerpt=match.content,
            rrf_score=match.rrf_score,
            vector_similarity=match.vector_similarity,
        )
    )
    ctx.state.citation_map.append(
        CitationMappingItem(
            badge_id=citation_key,
            modality=ProvenanceModalityEnum.DOC,
            badge_index=badge_index,
            target_id=cid_str,
            display_label=f"{match.document_title} #{match.chunk_index}",
        )
    )
    ctx.chunks_by_key[citation_key] = CitedChunkItem(
        citation_key=citation_key,
        chunk_id=match.chunk_id,
        document_id=match.document_id,
        document_title=match.document_title,
        chunk_index=match.chunk_index,
        content=match.content,
        similarity_score=match.vector_similarity,
        page_number=match.page_number,
        section_heading=match.section_heading,
        extracted_entities=match.extracted_entities,
    )
    return RetrievedChunkDict(
        citation_key=citation_key,
        chunk_id=cid_str,
        document_id=str(match.document_id),
        document_title=match.document_title,
        chunk_index=match.chunk_index,
        excerpt=match.content,
        similarity_score=match.vector_similarity,
        rrf_score=match.rrf_score,
    )


async def execute_search_document_chunks(
    ctx: TurnToolRuntimeContext,
    *,
    sub_query: str,
    top_k: int = 5,
    min_similarity: float = 0.65,
) -> SearchChunksToolOutput:
    """Execute hybrid chunk search and populate TurnWorkingState.retrieved_chunks."""
    matches = await ctx.hybrid_search.search_chunks(
        query_text=sub_query,
        top_k=top_k,
        min_similarity=min_similarity,
    )
    existing_chunk_ids = {c.chunk_id for c in ctx.state.retrieved_chunks}
    serialized: list[RetrievedChunkDict] = []
    for match in matches:
        cid_str = str(match.chunk_id)
        if cid_str in existing_chunk_ids:
            continue
        existing_chunk_ids.add(cid_str)
        serialized.append(_register_chunk_match(ctx, match))
    return SearchChunksToolOutput(
        retrieved_count=len(serialized),
        retrieved_chunks=serialized,
    )


def _register_kg_edge_row(
    ctx: TurnToolRuntimeContext,
    row: SubgraphEdgeRow,
    src_name: str,
    tgt_name: str,
    doc_title: str,
) -> tuple[KgRelationshipItem, KgPathDict]:
    """Register a traversed KG edge row in TurnWorkingState and return edge/path records."""
    badge_index = len(ctx.state.retrieved_kg_paths) + 1
    citation_key = f"KG:{badge_index}"
    path_summary = f"{src_name} -> {row.relation_type.value} -> {tgt_name}"
    conf = min(max(row.confidence, 0.0), 1.0)

    ctx.state.retrieved_kg_paths.append(
        RetrievedGraphPathStateItem(
            badge_index=badge_index,
            edge_ids=[str(row.edge_id)],
            node_ids=[str(row.source_entity_id), str(row.target_entity_id)],
            path_summary=path_summary,
            evidence_snippet=row.evidence_snippet,
            hop_depth=min(max(row.hop_depth, 1), 3),
            confidence=conf,
            supporting_chunk_ids=[str(row.source_chunk_id)],
        )
    )
    ctx.state.citation_map.append(
        CitationMappingItem(
            badge_id=citation_key,
            modality=ProvenanceModalityEnum.KG,
            badge_index=badge_index,
            target_id=str(row.edge_id),
            display_label=path_summary,
        )
    )
    ctx.kg_paths_by_key[citation_key] = CitedKgPathItem(
        citation_key=citation_key,
        edge_id=row.edge_id,
        source_entity=src_name,
        relation_type=row.relation_type,
        target_entity=tgt_name,
        evidence_snippet=row.evidence_snippet,
        confidence=conf,
        source_chunk_id=row.source_chunk_id,
        document_title=doc_title,
    )
    rel_item = KgRelationshipItem(
        edge_id=row.edge_id,
        source_entity_id=row.source_entity_id,
        target_entity_id=row.target_entity_id,
        relation_type=row.relation_type,
        evidence_snippet=row.evidence_snippet,
        confidence=conf,
        source_chunk_id=row.source_chunk_id,
        document_id=row.document_id,
        hop_depth=min(max(row.hop_depth, 1), 3),
    )
    path_dict = KgPathDict(
        citation_key=citation_key,
        edge_id=str(row.edge_id),
        source_entity=src_name,
        relation_type=row.relation_type.value,
        target_entity=tgt_name,
        evidence_snippet=row.evidence_snippet,
        confidence=round(conf, 4),
        source_chunk_id=str(row.source_chunk_id),
        document_title=doc_title,
    )
    return rel_item, path_dict


async def _hydrate_kg_subgraph_paths(
    ctx: TurnToolRuntimeContext,
    seed_entity_ids: list[UUID],
    max_hops: int,
) -> tuple[list[KgPathDict], list[str]]:
    """Run traverse_subgraph and populate TurnWorkingState.retrieved_kg_paths and subgraph."""
    edge_rows = await ctx.kg_repo.traverse_subgraph(
        seed_entity_ids=seed_entity_ids,
        max_hops=min(max(max_hops, 1), 3),
    )
    if not edge_rows:
        return [], []

    all_node_ids = list(
        dict.fromkeys(
            [
                *seed_entity_ids,
                *[row.source_entity_id for row in edge_rows],
                *[row.target_entity_id for row in edge_rows],
            ]
        )
    )
    entities = await ctx.kg_repo.get_entities_by_ids(all_node_ids)
    entity_map = {ent.entity_id: ent for ent in entities}
    chunk_ids = list(dict.fromkeys(row.source_chunk_id for row in edge_rows))
    chunks_with_titles = await ctx.doc_repo.get_chunks_by_ids(chunk_ids)
    doc_title_by_chunk = {c.chunk_id: title for c, title in chunks_with_titles}

    node_summaries: list[KgEntitySummary] = []
    for ent in entities[:50]:
        deg = await ctx.kg_repo.count_entity_degree(ent.entity_id)
        node_summaries.append(to_kg_entity_summary(ent, degree_count=deg))

    edge_items: list[KgRelationshipItem] = []
    kg_paths: list[KgPathDict] = []
    for row in edge_rows:
        src = (
            entity_map[row.source_entity_id].canonical_name
            if row.source_entity_id in entity_map
            else str(row.source_entity_id)[:8]
        )
        tgt = (
            entity_map[row.target_entity_id].canonical_name
            if row.target_entity_id in entity_map
            else str(row.target_entity_id)[:8]
        )
        doc_title = doc_title_by_chunk.get(row.source_chunk_id, "Knowledge Base")
        rel_item, path_dict = _register_kg_edge_row(ctx, row, src, tgt, doc_title)
        edge_items.append(rel_item)
        kg_paths.append(path_dict)

    ctx.subgraph = TurnSubgraphEnvelope(nodes=node_summaries, edges=edge_items)
    return kg_paths, [str(cid) for cid in chunk_ids]


async def execute_traverse_knowledge_graph(
    ctx: TurnToolRuntimeContext,
    *,
    candidate_entities: list[str],
    max_hops: int = 2,
) -> TraverseKgToolOutput:
    """Resolve candidate entities and execute 1-2 hop recursive CTE Knowledge Graph traversal."""
    query_embedding = await ctx.gemini.embed_query(ctx.state.user_query)
    resolved = await ctx.kg_repo.resolve_candidate_entities(
        candidate_names=candidate_entities,
        query_embedding=query_embedding,
        limit=8,
    )
    resolved_dicts: list[ResolvedEntityDict] = [
        ResolvedEntityDict(
            entity_id=str(ent.entity_id),
            canonical_name=ent.canonical_name,
            entity_type=ent.entity_type,
            description=ent.description,
        )
        for ent in resolved
    ]
    if not resolved:
        return TraverseKgToolOutput(
            resolved_entities=[],
            kg_paths=[],
            backing_chunk_ids=[],
        )

    seed_ids = [ent.entity_id for ent in resolved]
    kg_paths, backing_chunk_ids = await _hydrate_kg_subgraph_paths(
        ctx=ctx,
        seed_entity_ids=seed_ids,
        max_hops=max_hops,
    )
    return TraverseKgToolOutput(
        resolved_entities=resolved_dicts,
        kg_paths=kg_paths,
        backing_chunk_ids=backing_chunk_ids,
    )


def execute_verify_and_format_citations(
    ctx: TurnToolRuntimeContext,
    *,
    draft_markdown: str,
    similarity_threshold: float = 0.65,
    strict_abstention_mode: bool = True,
    has_modality_degradation: bool = False,
    searched_entities: list[str] | None = None,
    searched_queries: list[str] | None = None,
) -> CitationVerificationResult:
    """Validate inline citations against TurnWorkingState and enforce grounding rules."""
    return verify_synthesis_grounding(
        draft_markdown=draft_markdown,
        state=ctx.state,
        evidence=ctx.get_hydrated_evidence(),
        similarity_threshold=similarity_threshold,
        strict_abstention_mode=strict_abstention_mode,
        has_modality_degradation=has_modality_degradation,
        searched_entities=searched_entities,
        searched_queries=searched_queries,
    )


async def execute_consolidate_verified_memory(
    ctx: TurnToolRuntimeContext,
    *,
    verified_facts: list[str],
    turn_id: UUID,
    supporting_chunk_ids: list[UUID],
    entity_ids: list[UUID] | None = None,
    grounding_status: GroundingStatusEnum | None = None,
) -> ConsolidateMemoryToolOutput:
    """Consolidate verified atomic facts into Centralized Memory enforcing Decision D-04."""
    effective_status = grounding_status or ctx.state.grounding_status
    candidates = [
        VerifiedFactCandidate(
            content=fact.strip(),
            memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC,
            supporting_chunk_ids=supporting_chunk_ids,
            related_entity_ids=entity_ids or [],
        )
        for fact in verified_facts
        if len(fact.strip()) >= 5
    ]
    result = await ctx.memory_service.consolidate_verified_facts(
        candidates=candidates,
        grounding_status=effective_status,
        session_id=UUID(ctx.state.session_id),
        source_turn_id=turn_id,
    )
    return ConsolidateMemoryToolOutput(
        created_memory_ids=[str(mid) for mid in result.created_memory_ids],
        superseded_memory_ids=[str(mid) for mid in result.superseded_memory_ids],
        skipped_duplicate_count=result.skipped_duplicate_count,
    )


def _make_recall_memory_tool(ctx: TurnToolRuntimeContext) -> FunctionTool:
    """Create the FunctionTool wrapper for recall_centralized_memory."""

    async def recall_centralized_memory(
        query_text: str,
        include_shared_memory: bool = True,
    ) -> RecallMemoryToolOutput:
        """Recall active session and shared long-term memories by semantic similarity.

        Args:
            query_text: The search query text used to match relevant memories.
            include_shared_memory: Whether to include LONG_TERM_SEMANTIC and EPISODIC tiers.

        Returns:
            RecallMemoryToolOutput dictionary with recalled_count and recalled_memories list.
        """
        return await execute_recall_centralized_memory(
            ctx,
            query_text=query_text,
            session_id=UUID(ctx.state.session_id),
            include_shared_memory=include_shared_memory,
        )

    return FunctionTool(func=recall_centralized_memory)


def _make_search_chunks_tool(ctx: TurnToolRuntimeContext) -> FunctionTool:
    """Create the FunctionTool wrapper for search_document_chunks."""

    async def search_document_chunks(
        sub_query: str,
        top_k: int = 5,
        min_similarity: float = 0.65,
    ) -> SearchChunksToolOutput:
        """Search indexed document chunks using hybrid pgvector + full-text RRF fusion.

        Args:
            sub_query: Targeted search query string for chunk retrieval.
            top_k: Maximum number of top-ranked chunks to return (1..20).
            min_similarity: Minimum cosine similarity threshold (0.0..1.0).

        Returns:
            SearchChunksToolOutput dictionary with retrieved_count and retrieved_chunks list.
        """
        return await execute_search_document_chunks(
            ctx,
            sub_query=sub_query,
            top_k=top_k,
            min_similarity=min_similarity,
        )

    return FunctionTool(func=search_document_chunks)


def _make_traverse_kg_tool(ctx: TurnToolRuntimeContext) -> FunctionTool:
    """Create the FunctionTool wrapper for traverse_knowledge_graph."""

    async def traverse_knowledge_graph(
        candidate_entities: list[str],
        max_hops: int = 2,
    ) -> TraverseKgToolOutput:
        """Resolve candidate entity mentions and traverse 1-2 hop Knowledge Graph neighborhood.

        Args:
            candidate_entities: List of entity names or aliases extracted from the query.
            max_hops: Maximum graph traversal depth in hops (1..2).

        Returns:
            TraverseKgToolOutput dictionary with resolved_entities, kg_paths, and backing_chunk_ids.
        """
        return await execute_traverse_knowledge_graph(
            ctx,
            candidate_entities=candidate_entities,
            max_hops=max_hops,
        )

    return FunctionTool(func=traverse_knowledge_graph)


def _make_verify_citations_tool(ctx: TurnToolRuntimeContext) -> FunctionTool:
    """Create the FunctionTool wrapper for verify_and_format_citations."""

    def verify_and_format_citations(draft_markdown: str) -> VerifyCitationsToolOutput:
        """Validate inline [Doc:N], [KG:N], and [Mem:N] citations against TurnWorkingState.

        Args:
            draft_markdown: Draft synthesized Markdown response containing inline citation badges.

        Returns:
            VerifyCitationsToolOutput dictionary with verified_markdown and grounding_status.
        """
        res = execute_verify_and_format_citations(ctx, draft_markdown=draft_markdown)
        return VerifyCitationsToolOutput(
            verified_markdown=res.verified_markdown,
            grounding_status=res.grounding_status.value,
            grounding_score=res.grounding_score,
            valid_citation_keys=res.valid_citation_keys,
            stripped_phantom_keys=res.stripped_phantom_keys,
        )

    return FunctionTool(func=verify_and_format_citations)


def build_adk_function_tools(ctx: TurnToolRuntimeContext) -> dict[str, FunctionTool]:
    """Construct typed Google ADK FunctionTool wrappers bound to the active turn context."""
    return {
        "recall_centralized_memory": _make_recall_memory_tool(ctx),
        "search_document_chunks": _make_search_chunks_tool(ctx),
        "traverse_knowledge_graph": _make_traverse_kg_tool(ctx),
        "verify_and_format_citations": _make_verify_citations_tool(ctx),
    }
