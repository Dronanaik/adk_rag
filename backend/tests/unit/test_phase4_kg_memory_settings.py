"""Unit and endpoint tests for Phase 4: /api/v1/kg, /api/v1/memories, and /api/v1/settings."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.routes_kg import get_kg_explorer_service
from app.api.v1.routes_memory import get_memory_service
from app.config import Settings, get_settings
from app.dependencies import APIException
from app.main import create_app
from app.models.database import get_db_session
from app.models.entities import DocumentChunk, KgEntity, MemoryEntry, SystemSetting
from app.schemas.common import (
    EntityTypeEnum,
    GroundingStatusEnum,
    MemoryTierEnum,
    RelationTypeEnum,
)
from app.schemas.kg import SubgraphEdgeRow
from app.schemas.memory import VerifiedFactCandidate
from app.schemas.settings import SystemSettingsUpdateRequest
from app.services.gemini_service import GeminiService, generate_deterministic_embedding
from app.services.kg_explorer_service import KnowledgeGraphExplorerService
from app.services.memory_service import MemoryService


class _InMemoryPhase4State:
    """In-memory store backing KnowledgeGraph, Memory, Document, and Settings repositories."""

    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.doc_id = uuid4()
        self.chunk_id = uuid4()
        self.center_entity_id = uuid4()
        self.neighbor_entity_id = uuid4()

        self.chunk = DocumentChunk(
            chunk_id=self.chunk_id,
            document_id=self.doc_id,
            chunk_index=0,
            content="AuthGateway depends on TokenStore for JWT session verification.",
            embedding=generate_deterministic_embedding("auth chunk"),
            chunk_metadata={"page_number": 1},
            created_at=now,
        )
        self.entities: dict[UUID, KgEntity] = {
            self.center_entity_id: KgEntity(
                entity_id=self.center_entity_id,
                canonical_name="AuthGateway",
                lookup_key="authgateway",
                entity_type=EntityTypeEnum.SYSTEM.value,
                aliases=["Auth API"],
                description="Edge authentication gateway.",
                embedding=generate_deterministic_embedding("AuthGateway"),
                source_chunk_ids=[self.chunk_id],
                source_document_ids=[self.doc_id],
                created_at=now,
                updated_at=now,
            ),
            self.neighbor_entity_id: KgEntity(
                entity_id=self.neighbor_entity_id,
                canonical_name="TokenStore",
                lookup_key="tokenstore",
                entity_type=EntityTypeEnum.COMPONENT.value,
                aliases=[],
                description="Signed JWT key store.",
                embedding=generate_deterministic_embedding("TokenStore"),
                source_chunk_ids=[self.chunk_id],
                source_document_ids=[self.doc_id],
                created_at=now,
                updated_at=now,
            ),
        }
        self.edge = SubgraphEdgeRow(
            edge_id=uuid4(),
            source_entity_id=self.center_entity_id,
            target_entity_id=self.neighbor_entity_id,
            relation_type=RelationTypeEnum.DEPENDS_ON,
            evidence_snippet="AuthGateway depends on TokenStore for JWT session verification.",
            confidence=0.93,
            source_chunk_id=self.chunk_id,
            document_id=self.doc_id,
            hop_depth=1,
        )
        self.memories: dict[UUID, MemoryEntry] = {}
        self.setting = SystemSetting(
            id=1,
            top_k_chunks=5,
            similarity_threshold=Decimal("0.65"),
            max_kg_hops=2,
            max_agent_steps=5,
            turn_timeout_seconds=30,
            auto_consolidate_memory=True,
            strict_abstention_mode=True,
            updated_at=now,
        )


def _wire_kg_service(state: _InMemoryPhase4State) -> KnowledgeGraphExplorerService:
    """Build a KnowledgeGraphExplorerService wired to in-memory test state."""
    session = AsyncMock()
    service = KnowledgeGraphExplorerService(session=session)
    kg_repo = MagicMock()
    doc_repo = MagicMock()

    async def _list_entities(
        search: str | None = None,
        entity_type: EntityTypeEnum | None = None,
        document_id: UUID | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[tuple[KgEntity, int]], int]:
        rows = list(state.entities.values())
        if entity_type is not None:
            rows = [r for r in rows if r.entity_type == entity_type.value]
        if document_id is not None:
            rows = [r for r in rows if document_id in (r.source_document_ids or [])]
        if search:
            rows = [r for r in rows if search.lower() in r.canonical_name.lower()]
        return [(r, 1) for r in rows[offset : offset + limit]], len(rows)

    kg_repo.list_entities = AsyncMock(side_effect=_list_entities)
    kg_repo.get_entity_by_id = AsyncMock(side_effect=lambda eid: state.entities.get(eid))
    kg_repo.count_entity_degree = AsyncMock(return_value=1)
    kg_repo.traverse_subgraph = AsyncMock(return_value=[state.edge])
    kg_repo.get_entities_by_ids = AsyncMock(
        side_effect=lambda ids: [state.entities[i] for i in ids if i in state.entities]
    )
    doc_repo.get_chunks_by_ids = AsyncMock(
        side_effect=lambda cids: (
            [(state.chunk, "Architecture Spec")] if state.chunk_id in cids else []
        )
    )
    service._kg_repo = kg_repo
    service._doc_repo = doc_repo
    return service


def _wire_memory_service(
    state: _InMemoryPhase4State,
    settings: Settings,
) -> MemoryService:
    """Build a MemoryService wired to in-memory test state."""
    session = AsyncMock()
    gemini = GeminiService(settings)
    service = MemoryService(session=session, settings=settings, gemini_service=gemini)

    mem_repo = MagicMock()
    kg_repo = MagicMock()
    doc_repo = MagicMock()

    async def _create_verified_memory(
        memory_tier: MemoryTierEnum,
        content: str,
        embedding: list[float],
        session_id: UUID | None,
        source_turn_id: UUID | None,
        supporting_chunk_ids: list[UUID],
        related_entity_ids: list[UUID],
        supersedes_memory_ids: list[UUID] | None = None,
    ) -> tuple[MemoryEntry, list[UUID], bool]:
        for existing in state.memories.values():
            if existing.content == content.strip() and existing.superseded_by_id is None:
                return existing, [], True
        entry = MemoryEntry(
            memory_id=uuid4(),
            memory_tier=memory_tier.value,
            session_id=session_id,
            content=content.strip(),
            embedding=embedding,
            related_entity_ids=related_entity_ids,
            source_turn_id=source_turn_id,
            supporting_chunk_ids=supporting_chunk_ids,
            superseded_by_id=None,
            created_at=datetime.now(UTC),
        )
        state.memories[entry.memory_id] = entry
        superseded = list(supersedes_memory_ids or [])
        for old_id in superseded:
            if old_id in state.memories:
                state.memories[old_id].superseded_by_id = entry.memory_id
        return entry, superseded, False

    async def _list_memories(
        memory_tier: MemoryTierEnum | None = None,
        session_id: UUID | None = None,
        include_superseded: bool = False,
        search: str | None = None,
        query_embedding: list[float] | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> tuple[list[tuple[MemoryEntry, float | None]], int]:
        _ = query_embedding
        items = list(state.memories.values())
        if not include_superseded:
            items = [m for m in items if m.superseded_by_id is None]
        if memory_tier is not None:
            items = [m for m in items if m.memory_tier == memory_tier.value]
        if session_id is not None:
            items = [m for m in items if m.session_id == session_id]
        if search:
            items = [m for m in items if search.lower() in m.content.lower()]
        return [(m, None) for m in items[offset : offset + limit]], len(items)

    async def _update_memory_content(
        memory_id: UUID,
        content: str,
        embedding: list[float],
    ) -> MemoryEntry | None:
        entry = state.memories.get(memory_id)
        if entry is None:
            return None
        entry.content = content
        entry.embedding = embedding
        return entry

    async def _delete_memory(memory_id: UUID) -> MemoryEntry | None:
        return state.memories.pop(memory_id, None)

    mem_repo.get_by_id = AsyncMock(side_effect=lambda mid: state.memories.get(mid))
    mem_repo.create_verified_memory = AsyncMock(side_effect=_create_verified_memory)
    mem_repo.list_memories = AsyncMock(side_effect=_list_memories)
    mem_repo.update_memory_content = AsyncMock(side_effect=_update_memory_content)
    mem_repo.delete_memory = AsyncMock(side_effect=_delete_memory)

    kg_repo.get_entities_by_ids = AsyncMock(
        side_effect=lambda ids: [state.entities[i] for i in ids if i in state.entities]
    )
    doc_repo.get_chunks_by_ids = AsyncMock(
        side_effect=lambda cids: (
            [(state.chunk, "Architecture Spec")] if state.chunk_id in cids else []
        )
    )

    service._memory_repo = mem_repo
    service._kg_repo = kg_repo
    service._doc_repo = doc_repo
    return service


@pytest.mark.asyncio
async def test_memory_service_decision_d04_consolidation_and_deduplication() -> None:
    """Verify Decision D-04: long-term memory requires GROUNDED status and supporting chunks."""
    state = _InMemoryPhase4State()
    settings = Settings(GOOGLE_API_KEY="", ADMIN_API_KEY="test-admin-secret")
    service = _wire_memory_service(state, settings)

    candidate = VerifiedFactCandidate(
        content="AuthGateway requires signed JWT tokens issued by TokenStore.",
        memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC,
        related_entity_ids=[state.center_entity_id, state.neighbor_entity_id],
        supporting_chunk_ids=[state.chunk_id],
    )

    with pytest.raises(APIException) as ungrounded_exc:
        await service.consolidate_verified_facts(
            candidates=[candidate],
            grounding_status=GroundingStatusEnum.PARTIAL,
        )
    assert ungrounded_exc.value.status_code == 400
    assert ungrounded_exc.value.code == "UNVERIFIED_MEMORY_CONSOLIDATION"

    first_res = await service.consolidate_verified_facts(
        candidates=[candidate],
        grounding_status=GroundingStatusEnum.GROUNDED,
    )
    assert len(first_res.created_memory_ids) == 1
    assert first_res.skipped_duplicate_count == 0

    dup_res = await service.consolidate_verified_facts(
        candidates=[candidate],
        grounding_status=GroundingStatusEnum.GROUNDED,
    )
    assert len(dup_res.created_memory_ids) == 0
    assert dup_res.skipped_duplicate_count == 1


@pytest.mark.asyncio
async def test_kg_explorer_endpoints_entities_and_subgraph() -> None:
    """Verify GET /api/v1/kg/entities and GET /api/v1/kg/entities/{entity_id}/subgraph."""
    state = _InMemoryPhase4State()
    kg_service = _wire_kg_service(state)

    app = create_app()
    app.dependency_overrides[get_kg_explorer_service] = lambda: kg_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        list_resp = await client.get("/api/v1/kg/entities?search=Auth")
        assert list_resp.status_code == 200
        list_payload = list_resp.json()
        assert list_payload["pagination"]["total"] == 1
        assert list_payload["items"][0]["canonical_name"] == "AuthGateway"
        assert list_payload["items"][0]["degree_count"] == 1

        sub_resp = await client.get(
            f"/api/v1/kg/entities/{state.center_entity_id}/subgraph?hops=2"
        )
        assert sub_resp.status_code == 200
        sub_payload = sub_resp.json()
        assert sub_payload["center_entity"]["canonical_name"] == "AuthGateway"
        assert len(sub_payload["nodes"]) == 1
        assert sub_payload["nodes"][0]["canonical_name"] == "TokenStore"
        assert len(sub_payload["edges"]) == 1
        assert sub_payload["edges"][0]["relation_type"] == "DEPENDS_ON"
        assert len(sub_payload["supporting_chunks"]) == 1
        assert sub_payload["supporting_chunks"][0]["document_title"] == "Architecture Spec"

        missing_resp = await client.get(f"/api/v1/kg/entities/{uuid4()}/subgraph")
        assert missing_resp.status_code == 404
        assert missing_resp.json()["error"]["code"] == "ENTITY_NOT_FOUND"


@pytest.mark.asyncio
async def test_memory_explorer_endpoints_hydration_and_rbac_deletion() -> None:
    """Verify /api/v1/memories hydration, PATCH admin guard, and tier-scoped DELETE RBAC."""
    state = _InMemoryPhase4State()
    settings = Settings(GOOGLE_API_KEY="", ADMIN_API_KEY="test-admin-secret")
    mem_service = _wire_memory_service(state, settings)

    session_id = uuid4()
    await mem_service.consolidate_verified_facts(
        candidates=[
            VerifiedFactCandidate(
                content="Session working note: inspect latency metrics on AuthGateway.",
                memory_tier=MemoryTierEnum.SESSION,
                related_entity_ids=[state.center_entity_id],
                supporting_chunk_ids=[],
            ),
            VerifiedFactCandidate(
                content="Shared semantic fact: AuthGateway depends on TokenStore.",
                memory_tier=MemoryTierEnum.LONG_TERM_SEMANTIC,
                related_entity_ids=[state.center_entity_id, state.neighbor_entity_id],
                supporting_chunk_ids=[state.chunk_id],
            ),
        ],
        grounding_status=GroundingStatusEnum.GROUNDED,
        session_id=session_id,
    )

    app = create_app()
    app.dependency_overrides[get_memory_service] = lambda: mem_service
    app.dependency_overrides[get_settings] = lambda: settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        list_resp = await client.get("/api/v1/memories")
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        assert len(items) == 2

        session_mem = next(m for m in items if m["memory_tier"] == "SESSION")
        shared_mem = next(m for m in items if m["memory_tier"] == "LONG_TERM_SEMANTIC")
        assert "AuthGateway" in shared_mem["related_entity_names"]
        assert "Architecture Spec" in shared_mem["supporting_document_titles"]

        # Researcher can delete SESSION memory
        del_sess_resp = await client.delete(
            f"/api/v1/memories/{session_mem['memory_id']}",
            headers={"X-App-Role": "researcher"},
        )
        assert del_sess_resp.status_code == 200
        assert del_sess_resp.json()["memory_tier"] == "SESSION"

        # Researcher CANNOT delete LONG_TERM_SEMANTIC memory (403 MEMORY_SCOPE_FORBIDDEN)
        forbid_resp = await client.delete(
            f"/api/v1/memories/{shared_mem['memory_id']}",
            headers={"X-App-Role": "researcher"},
        )
        assert forbid_resp.status_code == 403
        assert forbid_resp.json()["error"]["code"] == "MEMORY_SCOPE_FORBIDDEN"

        # Admin can PATCH and DELETE LONG_TERM_SEMANTIC memory
        admin_headers = {"X-App-Role": "admin", "X-Admin-Api-Key": "test-admin-secret"}
        patch_resp = await client.patch(
            f"/api/v1/memories/{shared_mem['memory_id']}",
            headers=admin_headers,
            json={"content": "Updated semantic fact: AuthGateway strictly requires TokenStore."},
        )
        assert patch_resp.status_code == 200
        assert "strictly requires" in patch_resp.json()["content"]

        del_shared_resp = await client.delete(
            f"/api/v1/memories/{shared_mem['memory_id']}",
            headers=admin_headers,
        )
        assert del_shared_resp.status_code == 200
        assert del_shared_resp.json()["memory_tier"] == "LONG_TERM_SEMANTIC"


@pytest.mark.asyncio
async def test_settings_endpoints_get_telemetry_and_put_admin_rbac(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify GET /api/v1/settings telemetry and PUT /api/v1/settings Admin guard."""
    state = _InMemoryPhase4State()
    settings = Settings(GOOGLE_API_KEY="", ADMIN_API_KEY="test-admin-secret")

    class _FakeSettingsRepo:
        def __init__(self, _session: object) -> None:
            pass

        async def get_settings(self) -> SystemSetting:
            return state.setting

        async def measure_db_latency_ms(self) -> float:
            return 1.42

        async def update_settings(self, updates: SystemSettingsUpdateRequest) -> SystemSetting:
            if updates.top_k_chunks is not None:
                state.setting.top_k_chunks = updates.top_k_chunks
            if updates.similarity_threshold is not None:
                state.setting.similarity_threshold = Decimal(f"{updates.similarity_threshold:.2f}")
            if updates.max_kg_hops is not None:
                state.setting.max_kg_hops = updates.max_kg_hops
            if updates.strict_abstention_mode is not None:
                state.setting.strict_abstention_mode = updates.strict_abstention_mode
            return state.setting

    monkeypatch.setattr("app.api.v1.routes_settings.SettingsRepository", _FakeSettingsRepo)

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    async def _fake_db() -> object:
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = _fake_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        get_resp = await client.get("/api/v1/settings")
        assert get_resp.status_code == 200
        payload = get_resp.json()
        assert payload["settings"]["top_k_chunks"] == 5
        assert payload["telemetry"]["adk_runtime_status"] == "READY"
        assert payload["telemetry"]["db_latency_ms"] == 1.42

        # Researcher forbidden from PUT /api/v1/settings
        forbid_put = await client.put(
            "/api/v1/settings",
            headers={"X-App-Role": "researcher"},
            json={"top_k_chunks": 8},
        )
        assert forbid_put.status_code == 403

        # Admin allowed to PUT /api/v1/settings
        admin_put = await client.put(
            "/api/v1/settings",
            headers={"X-App-Role": "admin", "X-Admin-Api-Key": "test-admin-secret"},
            json={"top_k_chunks": 10, "similarity_threshold": 0.72, "max_kg_hops": 1},
        )
        assert admin_put.status_code == 200
        updated = admin_put.json()
        assert updated["top_k_chunks"] == 10
        assert updated["similarity_threshold"] == 0.72
        assert updated["max_kg_hops"] == 1

