# API Reference

All HTTP endpoints exposed by the FastAPI backend.

**Base URL** (local development): `http://localhost:8000`  
**Swagger UI**: http://localhost:8000/docs  
**ReDoc**: http://localhost:8000/redoc

---

## Authentication

All document and chat endpoints require the `x-user-id` header.

```http
x-user-id: your_user_id
```

> In production, replace this with a validated authentication token. The server should derive the user ID from the token, not from a user-supplied header.

---

## Endpoints

### `GET /health`

Health check. No authentication required.

**Response**

```json
{"status": "ok"}
```

**Example**

```bash
curl http://localhost:8000/health
```

---

### `GET /ingest/status`

Returns the current pipeline status and statistics.

**Response**

```json
{
  "status": "ready",
  "total_chunks": 47,
  "supported_file_types": [".pdf", ".docx", ".xlsx", "..."],
  "pipeline_steps": [
    "1. Text extraction (parser)",
    "2. Text normalization & chunking",
    "3. Gemini embedding generation (gemini-embedding-001)",
    "4. ChromaDB vector storage"
  ]
}
```

**Example**

```bash
curl http://localhost:8000/ingest/status
```

---

### `POST /documents/upload`

Upload a document and run the full ingestion pipeline.

**Headers**

| Header | Required | Description |
|--------|----------|-------------|
| `x-user-id` | ✅ | User identifier |
| `Content-Type` | auto | Set by multipart form |

**Body**: `multipart/form-data`

| Field | Type | Description |
|-------|------|-------------|
| `file` | file | The document to upload |

**Supported file types**: `.pdf`, `.docx`, `.xlsx`, `.xls`, `.pptx`, `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.htm`, `.log`

**Response (200)**

```json
{
  "success": true,
  "message": "Document ingested successfully.",
  "result": {
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "research_paper.pdf",
    "chunks_created": 12,
    "characters_extracted": 13400
  }
}
```

**Error responses**

| Status | Cause |
|--------|-------|
| 400 | Missing filename, unsupported file type, or no readable text |
| 500 | Ingestion pipeline failure |

**Example**

```bash
curl -X POST \
  -H "x-user-id: drona" \
  -F "file=@/path/to/document.pdf" \
  http://localhost:8000/documents/upload
```

---

### `GET /documents`

List all documents for the authenticated user.

**Headers**: `x-user-id` required

**Response (200)**

```json
{
  "success": true,
  "documents": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "research_paper.pdf",
      "chunks": 12
    },
    {
      "document_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
      "filename": "notes.txt",
      "chunks": 3
    }
  ]
}
```

**Example**

```bash
curl -H "x-user-id: drona" http://localhost:8000/documents
```

---

### `DELETE /documents/{document_id}`

Delete a document and all of its chunks from ChromaDB.

**Path parameters**: `document_id` — the UUID of the document to delete

**Headers**: `x-user-id` required

**Response (200)**

```json
{
  "success": true,
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted_chunks": 12
}
```

**Error responses**

| Status | Cause |
|--------|-------|
| 404 | Document not found for this user |

**Example**

```bash
curl -X DELETE \
  -H "x-user-id: drona" \
  http://localhost:8000/documents/550e8400-e29b-41d4-a716-446655440000
```

---

### `POST /chat`

Send a question to the Google ADK agent. The agent searches the user's documents and returns an answer with source citations.

**Headers**: `x-user-id` required, `Content-Type: application/json`

**Request body**

```json
{
  "query": "What are the main conclusions in the research paper?",
  "session_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | ✅ | The question to ask |
| `session_id` | string | ❌ | Reuse an existing ADK session for conversation history |

**Response (200)**

```json
{
  "answer": "The main conclusions are...\n\n[Source: research_paper.pdf, chunk 3]\n[Source: research_paper.pdf, chunk 7]",
  "session_id": "abc123-def456-..."
}
```

Pass the returned `session_id` in subsequent requests to maintain conversation context.

**Error responses**

| Status | Cause |
|--------|-------|
| 500 | ADK agent or Gemini API error |

**Example**

```bash
# First message (creates new session)
curl -X POST \
  -H "x-user-id: drona" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}' \
  http://localhost:8000/chat

# Follow-up (same session)
curl -X POST \
  -H "x-user-id: drona" \
  -H "Content-Type: application/json" \
  -d '{"query": "Can you elaborate on that?", "session_id": "abc123-def456-..."}' \
  http://localhost:8000/chat
```

---

## CORS

The backend accepts requests from any origin (`*`) in development mode. In production, restrict `allow_origins` to your actual frontend domain in `app/api.py`.
