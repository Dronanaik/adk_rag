# Architecture

A detailed walkthrough of the ADK RAG system design, data flows, and component responsibilities.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite)                      │
│   UserIdModal  →  Header  →  Tabs                                 │
│   UploadTab  |  DocumentsTab  |  IngestionTab  |  ChatTab         │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTP via Vite proxy
                            │ Base: http://localhost:8000
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                      FastAPI (app/api.py)                         │
│                                                                    │
│   GET  /health           — health check                           │
│   GET  /ingest/status    — pipeline status + chunk count          │
│   POST /documents/upload — upload + ingest                        │
│   GET  /documents        — list user's documents                  │
│   DELETE /documents/{id} — delete document + chunks               │
│   POST /chat             — ADK agent query                        │
└───────┬───────────────────────────┬──────────────────────────────┘
        │                           │
        │ Ingestion path            │ Chat path
        │                           │
┌───────▼──────────┐     ┌──────────▼──────────────────────────────┐
│  Ingestion        │     │         Google ADK Runner                │
│  Pipeline         │     │                                          │
│                   │     │   InMemorySessionService                 │
│  parsers.py       │     │   Runner(app_name, agent, sessions)      │
│  → extract text   │     │   run_async(user_id, session_id, msg)    │
│                   │     └──────────┬──────────────────────────────┘
│  chunking.py      │                │ calls tool
│  → chunk text     │     ┌──────────▼──────────────────────────────┐
│                   │     │   search_user_documents tool (agent.py)  │
│  embeddings.py    │     │                                          │
│  → Gemini embed   │     │   1. Read user_id from ToolContext       │
│                   │     │   2. Call search_documents(user_id, q)   │
│  rag_store.py     │     │   3. Return chunks + metadata            │
│  → store in Chroma│     └──────────┬──────────────────────────────┘
└───────────────────┘                │
        │                           │ similarity search
        └────────────────┬──────────┘
                         │
              ┌──────────▼──────────────────────────────┐
              │            ChromaDB                      │
              │   PersistentClient(path=./data/chroma)   │
              │   collection: "documents"                │
              │                                          │
              │   Each record:                           │
              │     id       — chunk_id (uuid)           │
              │     document — chunk text                │
              │     embedding — [float * 768]            │
              │     metadata:                            │
              │       user_id      — owner               │
              │       document_id  — parent document     │
              │       filename     — original filename   │
              │       chunk_index  — position in doc     │
              └──────────────────────────────────────────┘
```

---

## Component Responsibilities

### `app/config.py`
Loads environment variables from `.env`. Exports:
- `GOOGLE_API_KEY` — required
- `CHROMA_PATH` — ChromaDB storage path (default: `./data/chroma`)
- `COLLECTION_NAME` — collection name (default: `documents`)
- `TOP_K` — number of chunks to retrieve per query (default: 5)

### `app/database.py`
Creates a ChromaDB `PersistentClient` and gets-or-creates the `documents` collection. This module is imported once at startup — the same client and collection instance are shared across all requests.

### `app/parsers.py`
Maps file extensions to parser functions. Current parsers:

| Function | Extension | Library |
|----------|-----------|---------|
| `extract_from_pdf` | `.pdf` | PyMuPDF (`fitz`) |
| `extract_from_docx` | `.docx` | `python-docx` |
| `extract_from_xlsx` | `.xlsx`, `.xls` | `openpyxl` |
| `extract_from_pptx` | `.pptx` | `python-pptx` |
| `extract_from_text` | `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.htm`, `.log` | built-in |

The `extract_text(file_path)` function is the public dispatcher — it reads the file extension and routes to the correct parser.

### `app/chunking.py`
Two functions:
- `normalize_text(text)` — collapses multiple whitespace, removes empty lines
- `chunk_text(text, chunk_size=1200, overlap=200)` — splits normalized text into overlapping character-level chunks

Overlap prevents information from being cut off at chunk boundaries.

### `app/embeddings.py`
Wraps the Gemini embedding API:
- `embed_text(text)` → `list[float]` (768 dimensions)
- `embed_texts(texts)` → `list[list[float]]` (sequential, one API call per chunk)

Both document chunks and user queries use the same model and dimensionality so that cosine similarity is meaningful.

### `app/rag_store.py`
All ChromaDB read/write operations:
- `add_document_chunks(user_id, document_id, filename, chunks)` — embeds and stores chunks
- `delete_document_chunks(user_id, document_id)` — deletes by compound filter
- `search_documents(user_id, query, top_k)` — embeds query, runs similarity search with `user_id` filter
- `list_user_documents(user_id)` — groups chunks by `document_id`, returns document-level summary

### `app/ingest.py`
Orchestrates the full ingestion pipeline for one file:
1. Generate a UUID `document_id`
2. `extract_text(file_path)`
3. `chunk_text(text)`
4. `add_document_chunks(...)`

Returns stats: `document_id`, `filename`, `chunks_created`, `characters_extracted`.

### `app/agent.py`
Defines the Google ADK `LlmAgent` (`root_agent`) and its `search_user_documents` tool.

The tool reads `user_id` from `ToolContext` (injected by the ADK runner) and calls `search_documents`. This ensures the agent can only search the authenticated user's documents.

### `app/api.py`
FastAPI application with all HTTP endpoints. Key design decisions:
- `InMemorySessionService` is shared across requests — sessions persist as long as the server is running
- The `Runner` is initialized once at startup
- Uploaded files are saved to `./uploads/` as UUIDs, then deleted after ingestion

### `frontend/`
Vite + React single-page application. Calls the backend via the `/api` Vite proxy. See [FRONTEND.md](FRONTEND.md) for component details.

---

## ChromaDB Schema

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000_0_abc12345",
  "document": "chunk text content here...",
  "embedding": [0.021, -0.003, 0.147, ...],
  "metadata": {
    "user_id": "drona",
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "research_paper.pdf",
    "chunk_index": 0
  }
}
```

**ID format**: `{document_id}_{chunk_index}_{random_8_hex}`

---

## Embedding Model

| Property | Value |
|----------|-------|
| Model | `gemini-embedding-001` |
| Dimensionality | 768 |
| Provider | Google Generative AI |
| Similarity metric | Cosine (default ChromaDB) |

> Do not change the embedding model or dimensionality for an existing collection without re-ingesting all documents. Mismatched dimensions will cause query errors.

---

## Security Model

The system uses a simple `x-user-id` header for identity. Every ChromaDB query includes a `where: {"user_id": user_id}` filter, ensuring cross-user data isolation at the query level.

For production, replace the header with a validated authentication token (JWT, Firebase ID token, etc.) and derive `user_id` server-side.
