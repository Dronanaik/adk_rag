"""Unit tests for core backend utilities, RRF fusion, and API foundation."""

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app
from app.services.hybrid_search_service import compute_reciprocal_rank_fusion
from app.utils.chunker import chunk_document_text
from app.utils.hashing import (
    compute_sha256_bytes,
    compute_sha256_text,
    normalize_entity_lookup_key,
)


def test_sha256_and_entity_lookup_key_determinism() -> None:
    """Verify SHA-256 text/bytes digest and KG entity lookup key normalization."""
    digest_a = compute_sha256_text("Hello   World\r\n")
    digest_b = compute_sha256_text("Hello   World\n")
    assert digest_a == digest_b
    assert len(digest_a) == 64
    assert len(compute_sha256_bytes(b"sample-bytes")) == 64
    assert normalize_entity_lookup_key("  Payment-Gateway   Service! ") == "payment-gateway service"


def test_chunk_document_text_offsets_and_headings() -> None:
    """Verify deterministic chunk boundaries, overlap, and Markdown section heading tracking."""
    markdown = (
        "# Architecture Overview\n\n"
        + ("The OrchestratorAgent coordinates specialist sub-agents. " * 12)
        + "\n\n## Grounding Verification\n\n"
        + ("Every factual claim requires a valid provenance citation. " * 12)
    )
    chunks = chunk_document_text(markdown, chunk_size=350, chunk_overlap=70, page_number=1)
    assert len(chunks) >= 3
    assert chunks[0].chunk_index == 0
    assert chunks[0].section_heading == "Architecture Overview"
    assert chunks[0].page_number == 1
    assert chunks[0].char_end > chunks[0].char_start
    assert chunks[-1].section_heading == "Grounding Verification"


def test_reciprocal_rank_fusion_ordering() -> None:
    """Verify RRF (k=60) ranks items appearing in both vector and FTS lists highest."""
    vector_ids = ["chunk_a", "chunk_b", "chunk_c"]
    fts_ids = ["chunk_b", "chunk_d", "chunk_a"]
    fused = compute_reciprocal_rank_fusion(vector_ids, fts_ids, k_constant=60, top_k=3)
    assert len(fused) == 3
    assert fused[0].item_id in {"chunk_a", "chunk_b"}
    assert fused[0].vector_rank is not None
    assert fused[0].fts_rank is not None


def test_health_endpoint_and_request_id_header() -> None:
    """Verify GET /api/v1/health returns 200 OK with X-Request-Id header."""
    client = TestClient(create_app())
    response = client.get("/api/v1/health", headers={"X-Request-Id": "req_test_001"})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req_test_001"
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["request_id"] == "req_test_001"


def test_admin_guard_and_error_envelope() -> None:
    """Verify D-05 admin guard rejects researcher role or bad key with standard ErrorEnvelope."""
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(ADMIN_API_KEY="test-secret-admin-key")
    client = TestClient(app)

    # Researcher role is rejected with 403 FORBIDDEN_ADMIN_REQUIRED
    res_researcher = client.post(
        "/api/v1/auth/admin-check",
        headers={"X-App-Role": "researcher"},
    )
    assert res_researcher.status_code == 403
    err_body = res_researcher.json()
    assert err_body["error"]["code"] == "FORBIDDEN_ADMIN_REQUIRED"

    # Admin role with wrong key is rejected
    res_bad_key = client.post(
        "/api/v1/auth/admin-check",
        headers={"X-App-Role": "admin", "X-Admin-Api-Key": "wrong-key"},
    )
    assert res_bad_key.status_code == 403

    # Admin role with matching key succeeds
    res_ok = client.post(
        "/api/v1/auth/admin-check",
        headers={"X-App-Role": "admin", "X-Admin-Api-Key": "test-secret-admin-key"},
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["authorized_role"] == "admin"

