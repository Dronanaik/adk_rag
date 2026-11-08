# API Reference

The FastAPI backend (`app/api.py`) exposes REST endpoints on `http://localhost:8000` (interactive Swagger UI available at `http://localhost:8000/docs`).

All protected endpoints require an `Authorization: Bearer <jwt_token>` header obtained from `/auth/login` or `/auth/signup`.

---

## 1. Health Check

### `GET /health`
Returns server liveness status.

```bash
curl http://localhost:8000/health
```

**Response (`200 OK`)**:
```json
{
  "status": "ok",
  "service": "ADK Agentic RAG + Knowledge Graph API"
}
```

---

## 2. Authentication Endpoints (Neon PostgreSQL)

### `POST /auth/signup`
Creates a new user account in the Neon PostgreSQL `users` table and returns a signed `HS256` JWT Bearer token.

```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Morgan",
    "email": "alice@company.com",
    "password": "securepassword123"
  }'
```

**Response (`200 OK`)**:
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "user_9f8e7d6c5b4a3210",
    "email": "alice@company.com",
    "name": "Alice Morgan",
    "created_at": "2026-11-06T18:30:00+00:00"
  }
}
```

---

### `POST /auth/login`
Authenticates an existing user by email and password against Neon PostgreSQL.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@company.com",
    "password": "securepassword123"
  }'
```

**Response (`200 OK`)**: Same structure as `/auth/signup`.

---

### `GET /auth/me`
Verifies the Bearer JWT token and returns the active user profile.

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 3. Ingestion Pipeline & Status Endpoints

### `GET /ingest/status`
Returns database connectivity and aggregate counts across Neon PostgreSQL (`pgvector`) and Neo4j for the authenticated user.

```bash
curl http://localhost:8000/ingest/status \
  -H "Authorization: Bearer <TOKEN>"
```

**Response (`200 OK`)**:
```json
{
  "status": "ready",
  "vector_db": "Neon PostgreSQL (pgvector + FTS)",
  "vector_db_connected": true,
  "graph_db": "Neo4j Knowledge Graph",
  "graph_db_connected": true,
  "embedding_model": "gemini-embedding-001",
  "agent_model": "gemini-2.5-pro",
  "graph_extraction_model": "gemini-2.5-flash",
  "total_documents": 2,
  "total_chunks_in_db": 28,
  "total_entities_in_graph": 34,
  "total_relationships_in_graph": 41,
  "supported_file_types": [".csv", ".docx", ".htm", ".html", ".json", ".log", ".md", ".pdf", ".pptx", ".txt", ".xls", ".xlsx", ".xml"]
}
```

---

### `GET /ingest/progress`
Returns real-time step-by-step execution status (`pending`, `running`, `completed`, `error`) for each of the 5 ingestion stages for the authenticated user.

```bash
curl http://localhost:8000/ingest/progress \
  -H "Authorization: Bearer <TOKEN>"
```

---

### `POST /documents/upload`
Uploads a file and runs the 5-step dual ingestion pipeline into Neon PostgreSQL and Neo4j. Accepts optional `doc_index` and `total_docs` query parameters for multi-document batch telemetry in `GET /ingest/progress`. Automatically detects redundant uploads (`unchanged`, `duplicate_content`) and atomically replaces prior versions when an updated file with the same filename is uploaded (`updated`).

```bash
curl -X POST "http://localhost:8000/documents/upload?doc_index=1&total_docs=2" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@/path/to/document.pdf"
```

**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Indexed new document 'document.pdf' into Neon PostgreSQL and Neo4j.",
  "result": {
    "document_id": "52e1a9d0-8c1a-4f3b-9b12-0192837465ab",
    "filename": "document.pdf",
    "chunks_created": 14,
    "entities_extracted": 18,
    "relationships_extracted": 22,
    "characters_extracted": 15240,
    "ingest_action": "created",
    "content_hash": "9f86d081884c7d65",
    "action_detail": "Indexed new document 'document.pdf' into Neon PostgreSQL and Neo4j."
  }
}
```

---

## 4. Document Management Endpoints

### `GET /documents`
Lists all ingested documents belonging to the authenticated user.

```bash
curl http://localhost:8000/documents \
  -H "Authorization: Bearer <TOKEN>"
```

---

### `DELETE /documents/{document_id}`
Cascade-deletes a document and all of its chunks from Neon PostgreSQL and removes its relationships, document node, and orphaned entities from Neo4j.

```bash
curl -X DELETE http://localhost:8000/documents/52e1a9d0-8c1a-4f3b-9b12-0192837465ab \
  -H "Authorization: Bearer <TOKEN>"
```

---

### `DELETE /documents`
Bulk-deletes **all** documents, vector chunks, and Neo4j Knowledge Graph entities/relationships belonging to the authenticated user (`v2.3.3`).

```bash
curl -X DELETE http://localhost:8000/documents \
  -H "Authorization: Bearer <TOKEN>"
```

**Response (`200 OK`)**:
```json
{
  "success": true,
  "deleted_documents": 3,
  "deleted_chunks": 13,
  "deleted_entities": 119,
  "deleted_relationships": 116
}
```

---

## 5. Knowledge Graph Endpoints (Neo4j)

### `GET /graph`
Returns the user's Neo4j knowledge graph (`nodes`, `edges`, and `stats`) for visualization in the **Knowledge Graph** tab.

```bash
curl "http://localhost:8000/graph?limit=150" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### `GET /graph/entity/{entity_name}`
Returns the 1-hop incoming and outgoing relationships for a specific entity in Neo4j.

```bash
curl "http://localhost:8000/graph/entity/PostgreSQL?depth=1" \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 6. Agentic Chat Endpoint

### `POST /chat`
Sends a question to the Google ADK `LlmAgent` equipped with `hybrid_search`, `vector_search`, `graph_search`, and `get_entity_relationships`.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How are entities extracted and connected across my documents?",
    "session_id": "session_demo_1"
  }'
```

**Response (`200 OK`)**:
```json
{
  "status": "success",
  "question": "How are entities extracted and connected across my documents?",
  "answer": "Entities are extracted using Gemini Structured Outputs and stored in Neo4j...",
  "tools_used": ["hybrid_search", "graph_search"],
  "session_id": "session_demo_1",
  "user_id": "user_9f8e7d6c5b4a3210"
}
```

---

## 7. Environment & Connection Settings Endpoints (`v2.3.0`)

### `GET /settings/env`
Returns all 12 connection environment variables, their active source (`"default"` vs. `"custom"`), masked default fallback previews, documentation deep-link URLs (`doc_url`), and live connection statuses (`gemini`, `postgres`, `neo4j`).

```bash
curl http://localhost:8000/settings/env
```

---

### `POST /settings/env`
Updates connection environment variables at runtime (and optionally persists non-empty values to `.env` when `persist_to_env: true`). Any variable omitted or submitted as an empty string (`""`) automatically falls back to its default value and reloads database/LLM clients.

```bash
curl -X POST http://localhost:8000/settings/env \
  -H "Content-Type: application/json" \
  -d '{
    "values": {
      "AGENT_MODEL": "gemini-2.5-pro",
      "TOP_K": "8"
    },
    "persist_to_env": false
  }'
```

---

### `POST /settings/env/reset`
Clears all runtime overrides and restores every environment variable to its default `.env` / built-in system value.

```bash
curl -X POST http://localhost:8000/settings/env/reset
```
