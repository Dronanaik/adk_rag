"""Unit and endpoint tests for Phase 3 document ingestion, KG extraction, and /api/v1/documents."""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pymupdf
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.routes_kb import get_ingestion_service
from app.config import Settings
from app.dependencies import APIException
from app.main import create_app
from app.models.database import get_db_session
from app.models.entities import Document, DocumentChunk, KgEntity, KgRelationship
from app.schemas.common import DocumentStatusEnum, EntityTypeEnum, RelationTypeEnum
from app.schemas.documents import CorpusSummaryMetrics, DocumentDeleteResponse
from app.services.gemini_service import (
    GeminiService,
    execute_with_resilience,
    extract_deterministic_kg,
    generate_deterministic_embedding,
)
from app.services.ingestion import IngestionService, store_document_payload
from app.services.kg_extractor import KnowledgeGraphExtractionService
from app.utils.document_parser import (
    derive_document_title,
    detect_and_validate_mime_type,
    parse_and_chunk_document,
    sanitize_filename,
)


def _create_sample_pdf_bytes(pages_text: list[str]) -> bytes:
    """Create an in-memory PDF binary using PyMuPDF with the given page texts."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        if text.strip():
            page.insert_text((72, 72), text)
    raw = doc.tobytes()
    doc.close()
    return raw


def test_sanitize_filename_and_validate_mime_types() -> None:
    """Verify path traversal sanitization, magic-byte validation, and size limits."""
    assert sanitize_filename("../../etc/passwd/architecture.md") == "architecture.md"

    with pytest.raises(APIException) as empty_exc:
        detect_and_validate_mime_type("notes.md", b"")
    assert empty_exc.value.status_code == 400
    assert empty_exc.value.code == "VALIDATION_ERROR"

    with pytest.raises(APIException) as large_exc:
        detect_and_validate_mime_type("huge.txt", b"a" * (2 * 1024 * 1024), max_upload_size_mb=1)
    assert large_exc.value.status_code == 413
    assert large_exc.value.code == "FILE_TOO_LARGE"

    with pytest.raises(APIException) as fake_pdf_exc:
        detect_and_validate_mime_type("spoofed.pdf", b"NOT_A_PDF_HEADER_PAYLOAD")
    assert fake_pdf_exc.value.status_code == 415
    assert fake_pdf_exc.value.code == "UNSUPPORTED_MEDIA_TYPE"

    with pytest.raises(APIException) as bad_utf8_exc:
        detect_and_validate_mime_type("corrupt.md", b"\xff\xfe\x00\x00invalid")
    assert bad_utf8_exc.value.status_code == 415
    assert bad_utf8_exc.value.code == "UNSUPPORTED_MEDIA_TYPE"

    md_bytes = b"# Auth Gateway Spec\n\nAuth Gateway depends on Token Service."
    assert detect_and_validate_mime_type("spec.md", md_bytes) == "text/markdown"
    assert derive_document_title("spec.md", md_bytes, "text/markdown") == "Auth Gateway Spec"


def test_parse_and_chunk_pdf_and_markdown_documents() -> None:
    """Verify PyMuPDF page-aware parsing, scanned PDF rejection, and Markdown chunking."""
    pdf_bytes = _create_sample_pdf_bytes(
        [
            "Page 1: Payment Service communicates with Ledger Database for settlements.",
            "Page 2: Risk Engine mitigates Fraud Event using Policy Rules.",
        ]
    )
    mime = detect_and_validate_mime_type("payments.pdf", pdf_bytes)
    assert mime == "application/pdf"

    chunks = parse_and_chunk_document(
        raw_bytes=pdf_bytes,
        mime_type="application/pdf",
        chunk_size=300,
        chunk_overlap=50,
    )
    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2

    blank_pdf = _create_sample_pdf_bytes([""])
    with pytest.raises(APIException) as scanned_exc:
        parse_and_chunk_document(blank_pdf, "application/pdf")
    assert scanned_exc.value.status_code == 415
    assert scanned_exc.value.code == "UNSUPPORTED_MEDIA_TYPE"


@pytest.mark.asyncio
async def test_gemini_service_offline_embeddings_kg_and_retry_resilience() -> None:
    """Verify 768-dim normalized embeddings, deterministic KG extraction, and retry backoff."""
    settings = Settings(GOOGLE_API_KEY="", EMBEDDING_DIMENSION=768)
    gemini = GeminiService(settings)
    assert not gemini.is_live_configured

    texts = [f"Document chunk {i} about `AuthGateway` and `TokenStore`." for i in range(35)]
    vectors = await gemini.embed_texts(texts)
    assert len(vectors) == 35
    assert len(vectors[0]) == 768
    assert generate_deterministic_embedding("same input") == generate_deterministic_embedding(
        "same input"
    )

    kg_result = extract_deterministic_kg(
        "The `Auth Gateway` depends on `Token Service` and is governed by `Security Policy`.",
        "Security Architecture",
    )
    assert len(kg_result.entities) >= 2
    assert len(kg_result.relationships) >= 1
    assert kg_result.relationships[0].relation_type == RelationTypeEnum.DEPENDS_ON

    attempts = 0

    async def _flaky_op() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("429 RESOURCE_EXHAUSTED quota spike")
        return "recovered"

    result = await execute_with_resilience(
        _flaky_op,
        timeout_seconds=2.0,
        operation_name="test_flaky_gemini",
        backoff_schedule=(0.01, 0.02, 0.04),
    )
    assert result == "recovered"
    assert attempts == 3


@pytest.mark.asyncio
async def test_kg_extraction_service_persists_triples_and_enriches_chunk_metadata() -> None:
    """Verify KnowledgeGraphExtractionService resolves entities/edges and updates chunk metadata."""
    settings = Settings(GOOGLE_API_KEY="")
    gemini = GeminiService(settings)

    kg_repo = MagicMock()

    async def _fake_upsert_entity(
        canonical_name: str,
        entity_type: EntityTypeEnum,
        aliases: list[str],
        description: str,
        embedding: list[float],
        source_chunk_id: UUID,
        source_document_id: UUID,
    ) -> KgEntity:
        return KgEntity(
            entity_id=uuid4(),
            canonical_name=canonical_name,
            lookup_key=canonical_name.lower(),
            entity_type=entity_type.value,
            aliases=aliases,
            description=description,
            embedding=embedding,
            source_chunk_ids=[source_chunk_id],
            source_document_ids=[source_document_id],
        )

    async def _fake_upsert_rel(
        source_entity_id: UUID,
        target_entity_id: UUID,
        relation_type: RelationTypeEnum,
        evidence_snippet: str,
        confidence: float,
        source_chunk_id: UUID,
        document_id: UUID,
    ) -> KgRelationship:
        return KgRelationship(
            edge_id=uuid4(),
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relation_type=relation_type.value,
            evidence_snippet=evidence_snippet,
            confidence=Decimal(f"{confidence:.2f}"),
            source_chunk_id=source_chunk_id,
            document_id=document_id,
        )

    kg_repo.upsert_entity = AsyncMock(side_effect=_fake_upsert_entity)
    kg_repo.upsert_relationship = AsyncMock(side_effect=_fake_upsert_rel)

    extractor = KnowledgeGraphExtractionService(kg_repo=kg_repo, gemini_service=gemini)
    doc_id = uuid4()
    chunk = DocumentChunk(
        chunk_id=uuid4(),
        document_id=doc_id,
        chunk_index=0,
        content="`Order Service` depends on `Inventory Database` for stock reservation.",
        embedding=[0.01] * 768,
        chunk_metadata={"page_number": 1, "char_start": 0, "char_end": 70, "token_count": 12},
    )

    stats = await extractor.extract_and_persist_for_chunks(
        document_id=doc_id,
        document_title="Order Architecture",
        chunks=[chunk],
    )
    assert stats.entity_count >= 2
    assert stats.relation_count >= 1
    assert "extracted_entities" in chunk.chunk_metadata
    assert "extracted_relationships" in chunk.chunk_metadata


@pytest.mark.asyncio
async def test_ingestion_service_six_stage_pipeline_and_failure_isolation() -> None:
    """Verify IngestionService transitions through all stages and isolates failures to FAILED."""
    session = AsyncMock()
    settings = Settings(GOOGLE_API_KEY="")
    service = IngestionService(session=session, settings=settings)

    doc_id = uuid4()
    raw_md = b"# Resilience Spec\n\n`API Gateway` depends on `Auth Service` for request signing."
    now = datetime.now(UTC)
    doc_record = Document(
        document_id=doc_id,
        title="Resilience Spec",
        filename="resilience.md",
        mime_type="text/markdown",
        content_hash="a" * 64,
        file_size_bytes=len(raw_md),
        status=DocumentStatusEnum.QUEUED.value,
        chunk_count=0,
        entity_count=0,
        relation_count=0,
        created_at=now,
        updated_at=now,
    )

    recorded_statuses: list[DocumentStatusEnum] = []

    async def _track_status(
        document_id: UUID,
        status: DocumentStatusEnum,
        error_message: str | None = None,
        chunk_count: int | None = None,
        entity_count: int | None = None,
        relation_count: int | None = None,
    ) -> Document:
        recorded_statuses.append(status)
        doc_record.status = status.value
        doc_record.error_message = error_message
        if chunk_count is not None:
            doc_record.chunk_count = chunk_count
        if entity_count is not None:
            doc_record.entity_count = entity_count
        if relation_count is not None:
            doc_record.relation_count = relation_count
        return doc_record

    async def _fake_insert_chunks(
        document_id: UUID,
        chunks: list[tuple[int, str, list[float], dict[str, object]]],
    ) -> list[DocumentChunk]:
        return [
            DocumentChunk(
                chunk_id=uuid4(),
                document_id=document_id,
                chunk_index=idx,
                content=content,
                embedding=vec,
                chunk_metadata=meta,
                created_at=now,
            )
            for idx, content, vec, meta in chunks
        ]

    service._doc_repo.get_by_id = AsyncMock(return_value=doc_record)
    service._doc_repo.update_status = AsyncMock(side_effect=_track_status)
    service._doc_repo.insert_chunks = AsyncMock(side_effect=_fake_insert_chunks)
    service._kg_extractor.extract_and_persist_for_chunks = AsyncMock(
        return_value=MagicMock(entity_count=2, relation_count=1)
    )

    summary = await service.run_ingestion_pipeline(doc_id, raw_md)
    assert summary is not None
    assert summary.status == DocumentStatusEnum.INDEXED
    assert summary.entity_count == 2
    assert summary.relation_count == 1
    assert recorded_statuses == [
        DocumentStatusEnum.PARSING,
        DocumentStatusEnum.CHUNKING,
        DocumentStatusEnum.EMBEDDING,
        DocumentStatusEnum.EXTRACTING_KG,
        DocumentStatusEnum.INDEXED,
    ]

    # Now simulate an embedding failure and verify stage isolation + rollback
    recorded_statuses.clear()
    service._gemini.embed_texts = AsyncMock(side_effect=RuntimeError("Upstream embedding error"))
    failed_summary = await service.run_ingestion_pipeline(doc_id, raw_md)
    assert failed_summary is not None
    assert failed_summary.status == DocumentStatusEnum.FAILED
    assert failed_summary.error_message is not None
    assert "[EMBEDDING]" in failed_summary.error_message
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_kb_routes_rbac_upload_list_chunks_reindex_and_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify /api/v1/documents REST endpoints, RBAC guards, and 409 conflict checks."""
    app = create_app()
    now = datetime.now(UTC)
    doc_id = uuid4()
    chunk_id = uuid4()

    stored_doc = Document(
        document_id=doc_id,
        title="Platform Runbook",
        filename="runbook.md",
        mime_type="text/markdown",
        content_hash="b" * 64,
        file_size_bytes=128,
        status=DocumentStatusEnum.INDEXED.value,
        error_message=None,
        chunk_count=1,
        entity_count=2,
        relation_count=1,
        created_at=now,
        updated_at=now,
    )
    stored_chunk = DocumentChunk(
        chunk_id=chunk_id,
        document_id=doc_id,
        chunk_index=0,
        content="`Gateway` depends on `Auth`.",
        embedding=[0.1] * 768,
        chunk_metadata={
            "page_number": 1,
            "section_heading": "Platform Runbook",
            "char_start": 0,
            "char_end": 28,
            "token_count": 6,
            "extracted_entities": [],
            "extracted_relationships": [],
        },
        created_at=now,
    )

    fake_session = AsyncMock()
    fake_service = MagicMock(spec=IngestionService)

    async def _stage_upload(
        *,
        filename: str,
        raw_bytes: bytes,
        content_type: str | None = None,
        replace_existing: bool = False,
    ):
        from app.services.ingestion import to_upload_item_response

        return to_upload_item_response(stored_doc, deduplicated_hit=False), True

    fake_service.stage_upload_file = AsyncMock(side_effect=_stage_upload)
    fake_service.run_ingestion_pipeline = AsyncMock(return_value=None)
    fake_service.prepare_reindex = AsyncMock(return_value=stored_doc)

    app.dependency_overrides[get_db_session] = lambda: fake_session
    app.dependency_overrides[get_ingestion_service] = lambda: fake_service

    monkeypatch.setattr(
        "app.repositories.document_repo.DocumentRepository.list_documents",
        AsyncMock(return_value=([stored_doc], 1)),
    )
    monkeypatch.setattr(
        "app.repositories.document_repo.DocumentRepository.get_corpus_metrics",
        AsyncMock(
            return_value=CorpusSummaryMetrics(
                total_documents=1,
                total_indexed_chunks=1,
                total_kg_entities=2,
                total_kg_relationships=1,
            )
        ),
    )
    monkeypatch.setattr(
        "app.repositories.document_repo.DocumentRepository.get_by_id",
        AsyncMock(return_value=stored_doc),
    )
    monkeypatch.setattr(
        "app.repositories.document_repo.DocumentRepository.list_document_chunks",
        AsyncMock(return_value=([stored_chunk], 1)),
    )
    monkeypatch.setattr(
        "app.repositories.document_repo.DocumentRepository.delete_document_cascade",
        AsyncMock(
            return_value=DocumentDeleteResponse(
                deleted_document_id=doc_id,
                removed_chunks_count=1,
                removed_relationships_count=1,
                removed_orphaned_entities_count=2,
            )
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Researcher role cannot upload documents (403 FORBIDDEN_ADMIN_REQUIRED)
        forbidden_res = await client.post(
            "/api/v1/documents/upload",
            headers={"X-App-Role": "researcher"},
            files=[("files", ("runbook.md", b"# Runbook\nContent", "text/markdown"))],
        )
        assert forbidden_res.status_code == 403
        assert forbidden_res.json()["error"]["code"] == "FORBIDDEN_ADMIN_REQUIRED"

        # 2. Admin role uploads document -> 202 Accepted
        upload_res = await client.post(
            "/api/v1/documents/upload",
            headers={"X-App-Role": "admin"},
            files=[("files", ("runbook.md", b"# Runbook\nContent", "text/markdown"))],
        )
        assert upload_res.status_code == 202
        assert len(upload_res.json()["documents"]) == 1

        # 3. GET /api/v1/documents returns items + summary_metrics + pagination
        list_res = await client.get("/api/v1/documents")
        assert list_res.status_code == 200
        list_payload = list_res.json()
        assert list_payload["summary_metrics"]["total_documents"] == 1
        assert list_payload["pagination"]["total"] == 1

        # 4. GET /api/v1/documents/{id}/chunks returns deterministic chunks
        chunks_res = await client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert chunks_res.status_code == 200
        assert len(chunks_res.json()["items"]) == 1

        # 5. POST /api/v1/documents/{id}/reindex -> 202 Accepted
        store_document_payload(doc_id, b"# Runbook\nContent")
        reindex_res = await client.post(
            f"/api/v1/documents/{doc_id}/reindex",
            headers={"X-App-Role": "admin"},
        )
        assert reindex_res.status_code == 202

        # 6. DELETE /api/v1/documents/{id} -> 200 OK
        del_res = await client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"X-App-Role": "admin"},
        )
        assert del_res.status_code == 200
        assert del_res.json()["removed_chunks_count"] == 1

        # 7. Active ingestion state blocks reindex & delete with 409 INGESTION_IN_PROGRESS
        stored_doc.status = DocumentStatusEnum.EXTRACTING_KG.value
        conflict_res = await client.delete(
            f"/api/v1/documents/{doc_id}",
            headers={"X-App-Role": "admin"},
        )
        assert conflict_res.status_code == 409
        assert conflict_res.json()["error"]["code"] == "INGESTION_IN_PROGRESS"

