"""Unit tests for Phase 2 SQLAlchemy ORM models, Pydantic v2 schemas, and async repositories."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models import (
    Base,
    ConversationSession,
    Document,
    KgEntity,
    MemoryEntry,
    SystemSetting,
)
from app.repositories import (
    DEFAULT_SESSION_TITLE,
    DocumentRepository,
    KnowledgeGraphRepository,
    MemoryRepository,
    SessionRepository,
    SettingsRepository,
    normalize_lookup_key,
)
from app.schemas import (
    AgentNameEnum,
    ChunkKgExtractionResult,
    DocumentStatusEnum,
    EntityTypeEnum,
    ExtractedEntityCandidate,
    ExtractedRelationshipCandidate,
    GroundingStatusEnum,
    MemoryTierEnum,
    RelationTypeEnum,
    SessionCreateRequest,
    SystemSettingsUpdateRequest,
    TraceStatusEnum,
    TurnCreateRequest,
    VerifiedFactCandidate,
)


def test_orm_metadata_declares_all_nine_tables() -> None:
    """Verify Base.metadata contains all 9 canonical tables from DATABASE.md."""
    expected_tables = {
        "system_settings",
        "documents",
        "document_chunks",
        "kg_entities",
        "kg_relationships",
        "conversation_sessions",
        "message_turns",
        "memory_entries",
        "agent_execution_traces",
    }
    assert expected_tables.issubset(set(Base.metadata.tables.keys()))
    chunks_table = Base.metadata.tables["document_chunks"]
    assert "metadata" in chunks_table.c


def test_kg_extraction_schema_enforces_d03_enums_and_normalizes_whitespace() -> None:
    """Verify ChunkKgExtractionResult enforces D-03 entity/relation types and extra='forbid'."""
    entity = ExtractedEntityCandidate(
        canonical_name="  Auth   Gateway  ",
        entity_type=EntityTypeEnum.SYSTEM,
        aliases=[" AuthGW ", "Auth   Gateway", ""],
        description="Handles token verification.",
    )
    assert entity.canonical_name == "Auth Gateway"
    assert entity.aliases == ["AuthGW"]

    rel = ExtractedRelationshipCandidate(
        source_entity_name="API Router",
        relation_type=RelationTypeEnum.DEPENDS_ON,
        target_entity_name="Auth Gateway",
        evidence_snippet="  The API Router depends on Auth Gateway for JWT validation.  ",
        confidence=0.93,
    )
    result = ChunkKgExtractionResult(entities=[entity], relationships=[rel])
    assert len(result.entities) == 1
    assert len(result.relationships) == 1

    with pytest.raises(ValidationError):
        ExtractedEntityCandidate.model_validate(
            {
                "canonical_name": "Invalid Type Node",
                "entity_type": "UNSUPPORTED_TYPE",
            }
        )

    with pytest.raises(ValidationError):
        ExtractedRelationshipCandidate.model_validate(
            {
                "source_entity_name": "A",
                "relation_type": "DEPENDS_ON",
                "target_entity_name": "B",
                "evidence_snippet": "A depends on B",
                "unexpected_field": "forbidden",
            }
        )


def test_verified_fact_candidate_and_session_request_validators() -> None:
    """Verify VerifiedFactCandidate, SessionCreateRequest, and TurnCreateRequest validators."""
    chunk_id = uuid4()
    fact = VerifiedFactCandidate(
        content="  Auth Gateway enforces 15-minute JWT expiry.  ",
        memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC,
        supporting_chunk_ids=[chunk_id],
    )
    assert fact.content == "Auth Gateway enforces 15-minute JWT expiry."
    assert fact.supporting_chunk_ids == [chunk_id]

    with pytest.raises(ValidationError):
        VerifiedFactCandidate(
            content="Ungrounded claim without supporting chunks",
            memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC,
            supporting_chunk_ids=[],
        )

    session_req = SessionCreateRequest(title="  Multi-Hop   RAG Audit  ")
    assert session_req.title == "Multi-Hop RAG Audit"

    with pytest.raises(ValidationError):
        TurnCreateRequest(user_query="   ")

    with pytest.raises(ValidationError):
        SystemSettingsUpdateRequest(top_k_chunks=99)


@pytest.mark.asyncio
async def test_memory_repository_enforces_d04_provenance_and_deduplication() -> None:
    """Verify MemoryRepository.create_verified_memory rejects ungrounded long-term writes (D-04)."""
    mock_session = AsyncMock()
    repo = MemoryRepository(mock_session)

    with pytest.raises(ValueError, match="Decision D-04 violation"):
        await repo.create_verified_memory(
            memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC,
            content="Ungrounded fact",
            embedding=[0.01] * 768,
            session_id=None,
            source_turn_id=None,
            supporting_chunk_ids=[],
            related_entity_ids=[],
        )

    # Simulate near-duplicate detection (>= 0.94 cosine similarity)
    existing_entry = MemoryEntry(
        memory_id=uuid4(),
        memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC.value,
        content="Existing verified fact",
        embedding=[0.02] * 768,
        supporting_chunk_ids=[uuid4()],
    )
    dup_result = MagicMock()
    dup_result.scalar_one_or_none.return_value = existing_entry
    mock_session.execute.return_value = dup_result

    entry, superseded, was_dup = await repo.create_verified_memory(
        memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC,
        content="Existing verified fact",
        embedding=[0.02] * 768,
        session_id=None,
        source_turn_id=uuid4(),
        supporting_chunk_ids=[uuid4()],
        related_entity_ids=[],
    )
    assert was_dup is True
    assert entry.memory_id == existing_entry.memory_id
    assert superseded == []


@pytest.mark.asyncio
async def test_kg_repository_upsert_entity_merges_aliases_and_provenance() -> None:
    """Verify KnowledgeGraphRepository.upsert_entity merges aliases and chunk/doc provenance."""
    assert normalize_lookup_key("  Vector   Search  Engine ") == "vector search engine"

    doc_1 = uuid4()
    doc_2 = uuid4()
    chunk_1 = uuid4()
    chunk_2 = uuid4()

    existing_entity = KgEntity(
        entity_id=uuid4(),
        canonical_name="Vector Search Engine",
        lookup_key="vector search engine",
        entity_type=EntityTypeEnum.COMPONENT.value,
        aliases=["VSE"],
        description="Short desc",
        embedding=[0.1] * 768,
        source_chunk_ids=[chunk_1],
        source_document_ids=[doc_1],
    )
    exact_result = MagicMock()
    exact_result.scalar_one_or_none.return_value = existing_entity

    mock_session = AsyncMock()
    mock_session.execute.return_value = exact_result

    repo = KnowledgeGraphRepository(mock_session)
    updated = await repo.upsert_entity(
        canonical_name="Vector Search Engine",
        entity_type=EntityTypeEnum.COMPONENT,
        aliases=["PgVector Search", "VSE"],
        description="Detailed description of the Vector Search Engine component.",
        embedding=[0.1] * 768,
        source_chunk_id=chunk_2,
        source_document_id=doc_2,
    )

    assert updated.entity_id == existing_entity.entity_id
    assert "PgVector Search" in updated.aliases
    assert chunk_2 in updated.source_chunk_ids
    assert doc_2 in updated.source_document_ids
    assert updated.description == "Detailed description of the Vector Search Engine component."


@pytest.mark.asyncio
async def test_settings_document_and_session_repositories() -> None:
    """Verify SettingsRepository, DocumentRepository, and SessionRepository core operations."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # 1. SettingsRepository update
    setting_row = SystemSetting(
        id=1,
        top_k_chunks=5,
        similarity_threshold=Decimal("0.65"),
        max_kg_hops=2,
        max_agent_steps=5,
        turn_timeout_seconds=30,
        auto_consolidate_memory=True,
        strict_abstention_mode=True,
    )
    setting_res = MagicMock()
    setting_res.scalar_one_or_none.return_value = setting_row
    mock_session.execute.return_value = setting_res

    settings_repo = SettingsRepository(mock_session)
    updated_setting = await settings_repo.update_settings(
        SystemSettingsUpdateRequest(top_k_chunks=8, similarity_threshold=0.72)
    )
    assert updated_setting.top_k_chunks == 8
    assert updated_setting.similarity_threshold == Decimal("0.72")

    # 2. DocumentRepository status update
    doc_id = uuid4()
    doc_row = Document(
        document_id=doc_id,
        title="System Spec",
        filename="spec.md",
        mime_type="text/markdown",
        content_hash="a" * 64,
        file_size_bytes=1024,
        status=DocumentStatusEnum.QUEUED.value,
    )
    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = doc_row
    mock_session.execute.return_value = doc_res

    doc_repo = DocumentRepository(mock_session)
    updated_doc = await doc_repo.update_status(
        document_id=doc_id,
        status=DocumentStatusEnum.INDEXED,
        chunk_count=12,
        entity_count=6,
        relation_count=9,
    )
    assert updated_doc is not None
    assert updated_doc.status == "INDEXED"
    assert updated_doc.chunk_count == 12

    # 3. SessionRepository auto-title promotion on first turn (turn_index == 0)
    session_id = uuid4()
    conv_session = ConversationSession(
        session_id=session_id,
        title=DEFAULT_SESSION_TITLE,
        use_shared_memory=True,
    )
    session_res = MagicMock()
    session_res.scalar_one_or_none.return_value = conv_session
    mock_session.execute.return_value = session_res

    session_repo = SessionRepository(mock_session)
    turn = await session_repo.create_message_turn(
        session_id=session_id,
        user_query="How does Auth Gateway validate tokens?",
        assistant_response="Auth Gateway validates tokens using public JWKS keys [Doc:1].",
        grounding_status=GroundingStatusEnum.GROUNDED,
        citations={"chunks": [], "kg_paths": [], "memories": []},
        total_latency_ms=420,
        turn_index=0,
    )
    assert turn.turn_index == 0
    assert conv_session.title == "How does Auth Gateway validate tokens?"

    trace = await session_repo.create_execution_trace(
        turn_id=uuid4(),
        step_order=1,
        agent_name=AgentNameEnum.ORCHESTRATOR,
        action_or_tool="plan_retrieval",
        status=TraceStatusEnum.SUCCESS,
        latency_ms=85,
    )
    assert trace.agent_name == "Orchestrator"
    assert trace.status == "SUCCESS"
