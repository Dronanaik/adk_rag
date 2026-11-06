# System Architecture

This document describes the architecture, components, and end-to-end data flows of the **ADK Agentic RAG + Knowledge Graph** platform.

---

## 1. High-Level System Architecture

The platform combines **Neon Console Serverless PostgreSQL (`pgvector` + Full-Text Search)** and **Neo4j Knowledge Graph** under a single **Google ADK (`LlmAgent`)** orchestration layer and a **React 18** web application.

```mermaid
flowchart TB
    subgraph Client["React 18 + Vite Frontend (Port 5173)"]
        AuthUI["Sign In / Create Account\n(UserIdModal.jsx)"]
        UploadUI["Upload Tab\n(UploadTab.jsx)"]
        PipelineUI["5-Step Live Pipeline Tab\n(IngestionTab.jsx)"]
        DocsUI["Documents Manager Tab\n(DocumentsTab.jsx)"]
        ChatUI["Agentic Chat Tab\n(ChatTab.jsx + ChatMessage.jsx)"]
        GraphUI["Interactive SVG Knowledge Graph\n(GraphTab.jsx)"]
    end

    subgraph Backend["FastAPI Backend (Port 8000)"]
        API["FastAPI Router\n(app/api.py)"]
        AuthSvc["Neon Auth + HS256 JWT\n(app/auth.py)"]
        IngestSvc["5-Step Dual Ingestion Orchestrator\n(app/ingest.py)"]
        Parsers["Format Extractors\n(app/parsers.py)"]
        Chunker["Structure-Aware Semantic Chunker\n(app/chunking.py)"]
        Embedder["Batched Gemini Embedder\n(app/embeddings.py)"]
        ADKAgent["Google ADK LlmAgent\n(app/agent.py)"]
        RagStore["PostgreSQL Vector & Hybrid Store\n(app/rag_store.py)"]
        GraphStore["Neo4j Graph Extractor & Store\n(app/graph_store.py)"]
    end

    subgraph ExternalAI["Google Gemini API"]
        GeminiEmbed["gemini-embedding-001\n(768-dim vectors)"]
        GeminiFlash["gemini-2.5-flash\n(Structured JSON Graph Extraction)"]
        GeminiPro["gemini-2.5-pro\n(ADK Multi-Tool Reasoning)"]
    end

    subgraph Storage["Cloud Persistence Layer"]
        NeonDB[("Neon Console PostgreSQL\n• users\n• documents\n• document_chunks (pgvector HNSW + FTS GIN)")]
        Neo4jDB[("Neo4j Knowledge Graph\n• (:Entity)-[:RELATES_TO]->(:Entity)\n• (:Entity)-[:MENTIONED_IN]->(:Document)")]
    end

    AuthUI -->|POST /auth/login, /auth/signup| API
    UploadUI -->|POST /documents/upload| API
    PipelineUI -->|GET /ingest/progress, /ingest/status| API
    DocsUI -->|GET /documents, DELETE /documents/:id| API
    ChatUI -->|POST /chat| API
    GraphUI -->|GET /graph, /graph/entity/:name| API

    API --> AuthSvc
    AuthSvc --> NeonDB

    API --> IngestSvc
    IngestSvc --> Parsers
    IngestSvc --> Chunker
    IngestSvc --> Embedder
    Embedder --> GeminiEmbed
    IngestSvc --> RagStore
    IngestSvc --> GraphStore
    GraphStore --> GeminiFlash

    API --> ADKAgent
    ADKAgent --> GeminiPro
    ADKAgent -->|hybrid_search / vector_search| RagStore
    ADKAgent -->|graph_search / get_entity_relationships| GraphStore

    RagStore --> NeonDB
    GraphStore --> Neo4jDB
```

---

## 2. Backend Module Breakdown (`app/`)

| Module | File | Responsibility |
|--------|------|----------------|
| **Configuration** | `app/config.py` | Loads `.env`, validates `GOOGLE_API_KEY`, configures `DATABASE_URL`, `NEO4J_*`, `JWT_*`, `AGENT_MODEL`, and `GRAPH_EXTRACTION_MODEL`. |
| **Database Layer** | `app/database.py` | Manages the Neon PostgreSQL `ThreadedConnectionPool` (with TCP keepalives, connection health checks, and URL normalization) and the Neo4j driver (`GraphDatabase.driver`). Automatically creates tables, `pgvector` HNSW indexes, GIN FTS indexes, and Neo4j constraints on startup. |
| **Authentication** | `app/auth.py` | Implements `PBKDF2-HMAC-SHA256` password hashing (`260,000` iterations), `HS256` JWT signing/verification, user registration/login against the Neon `users` table, and the `get_current_user` FastAPI security dependency. |
| **Format Parsers** | `app/parsers.py` | Dispatches uploaded files by extension (`.pdf`, `.docx`, `.xlsx`, `.xls`, `.pptx`, `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.log`) to specialized text extractors. |
| **Semantic Chunker** | `app/chunking.py` | Splits extracted document text along markdown headers, paragraphs, and sentences (`chunk_size=1200`, `overlap=200`) to preserve semantic coherence. |
| **Embeddings** | `app/embeddings.py` | Wraps `google-genai` `gemini-embedding-001` (`768` dimensions) with batching (`50` chunks per call) for high-throughput document ingestion and single-query embedding. |
| **Vector & Hybrid Store** | `app/rag_store.py` | Executes Neon PostgreSQL CRUD (`add_document_chunks`, `delete_document_chunks`, `list_user_documents`) and retrieval (`search_documents` pure vector cosine search and `hybrid_search_documents` combining `70%` vector similarity + `30%` `ts_rank_cd` full-text score). |
| **Knowledge Graph Store** | `app/graph_store.py` | Extracts structured `ExtractedEntity` and `ExtractedRelationship` objects from chunks using `gemini-2.5-flash` and persists/queries them in Neo4j via parameterized Cypher queries. |
| **Dual Ingestion Pipeline** | `app/ingest.py` | Orchestrates the 5-step ingestion pipeline and maintains real-time per-user step state (`_user_ingestion_progress`) polled by the frontend UI. |
| **Google ADK Agent** | `app/agent.py` | Defines `root_agent` (`LlmAgent`) equipped with 4 tools (`hybrid_search`, `vector_search`, `graph_search`, `get_entity_relationships`) and dynamic system instructions injecting the active `user_id`. |
| **REST API** | `app/api.py` | Exposes FastAPI endpoints for Auth, Upload, Live Ingestion Progress, Documents, Knowledge Graph, and Agentic Chat. Runs heavy ingestion in `asyncio.to_thread` using system temporary storage so Uvicorn `--reload` is never interrupted. |

---

## 3. End-to-End Data Flows

### 3.1 Flow 1: Neon PostgreSQL Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant UI as React Frontend
    participant API as FastAPI (/auth/*)
    participant Auth as app/auth.py
    participant Neon as Neon PostgreSQL (users)

    User->>UI: Enter Email & Password (Sign In or Sign Up)
    UI->>API: POST /auth/signup or POST /auth/login
    API->>Auth: register_user() / authenticate_user()
    Auth->>Neon: SELECT / INSERT user record
    Neon-->>Auth: User row (user_id, email, name, password_hash)
    Auth->>Auth: Verify PBKDF2-SHA256 hash & sign HS256 JWT
    Auth-->>API: {token, user}
    API-->>UI: 200 OK {token, user}
    UI->>UI: Save JWT in localStorage & attach Authorization: Bearer <token>
```

---

### 3.2 Flow 2: 5-Step Dual Ingestion & Live Progress Tracking

When a user uploads a file, the backend runs the 5-step pipeline in a worker thread while the frontend polls `GET /ingest/progress` every `800ms` to highlight the exact step currently running.

```mermaid
sequenceDiagram
    actor User
    participant UI as React UI (UploadTab / IngestionTab)
    participant API as FastAPI (app/api.py)
    participant Ingest as app/ingest.py
    participant Gemini as Google Gemini API
    participant Neon as Neon PostgreSQL (pgvector)
    participant Neo4j as Neo4j Knowledge Graph

    User->>UI: Select file & click "Upload & Ingest"
    UI->>UI: Switch to Ingestion Pipeline tab & start polling /ingest/progress
    UI->>API: POST /documents/upload (multipart file + Bearer JWT)
    API->>Ingest: asyncio.to_thread(ingest_document)

    Note over Ingest: Step 1 (running)
    Ingest->>Ingest: parse_file(file_path) -> raw text

    Note over Ingest: Step 2 (running)
    Ingest->>Ingest: chunk_text(text, size=1200, overlap=200)

    Note over Ingest: Step 3 (running)
    Ingest->>Gemini: get_embeddings_batch(chunks) [gemini-embedding-001]
    Gemini-->>Ingest: 768-dim float vectors

    Note over Ingest: Step 4 (running)
    Ingest->>Neon: INSERT documents + execute_values(document_chunks)

    Note over Ingest: Step 5 (running)
    Ingest->>Gemini: extract_graph_from_chunks() [gemini-2.5-flash JSON]
    Gemini-->>Ingest: Entities & Relationships
    Ingest->>Neo4j: Cypher MERGE (:Entity), (:Document), [:RELATES_TO]
    Ingest->>Neon: UPDATE documents SET entities_count, relationships_count

    Ingest-->>API: Summary dict (chunks, entities, relationships)
    API-->>UI: 200 OK Ingestion Complete
```

---

### 3.3 Flow 3: Multi-Tool Agentic Chat Flow

When the user asks a question in **Agentic Chat**, the Google ADK `Runner` executes `root_agent`. The agent decides which tool(s) to invoke, synthesizes the retrieved chunks and graph triplets, and returns an answer with both tool badges and inline citations.

```mermaid
sequenceDiagram
    actor User
    participant UI as React ChatTab
    participant API as FastAPI (POST /chat)
    participant Runner as Google ADK Runner (LlmAgent)
    participant Rag as app/rag_store.py (Neon Postgres)
    participant Graph as app/graph_store.py (Neo4j)

    User->>UI: Ask question
    UI->>API: POST /chat {question, session_id} + Bearer JWT
    API->>Runner: runner.run_async(user_id, session_id, message)

    alt Hybrid / Vector Query
        Runner->>Rag: hybrid_search(query, user_id) or vector_search(query, user_id)
        Rag-->>Runner: Top-K ranked document chunks + similarity scores
    end

    alt Entity / Relationship Query
        Runner->>Graph: graph_search(query, user_id) or get_entity_relationships(entity_name, user_id)
        Graph-->>Runner: Matched Neo4j entities & (Source)-[RELATES_TO]->(Target) facts
    end

    Runner-->>API: Final synthesized response + tool call events
    API-->>UI: {answer, tools_used, session_id}
    UI-->>User: Render Markdown answer with Tool Badges & [Source]/[Graph] citations
```

---

### 3.4 Flow 4: Cascade Document Deletion Flow

Deleting a document from the **Documents** tab cleans up both databases atomically:

```mermaid
flowchart LR
    A["DELETE /documents/{document_id}"] --> B["Neon PostgreSQL:\nDelete from documents & document_chunks\nWHERE document_id = :id AND user_id = :uid"]
    B --> C["Neo4j Step 1:\nDelete RELATES_TO edges\nWHERE r.document_id = :id AND r.user_id = :uid"]
    C --> D["Neo4j Step 2:\nDETACH DELETE (:Document {id: uid::doc_id})"]
    D --> E["Neo4j Step 3:\nPrune orphaned (:Entity) nodes\nwith no remaining MENTIONED_IN or RELATES_TO links"]
```

---

## 4. Multi-Tenant Isolation Architecture

Every data record across the entire stack is partitioned by the authenticated `user_id`:
1. **Authentication Layer (`app/auth.py`)**: Extracts and verifies the `user_id` (`sub` claim) from the `HS256` JWT token on every API request.
2. **Neon PostgreSQL (`app/rag_store.py`)**: Every `SELECT` and `DELETE` statement includes `WHERE user_id = %s`, preventing cross-user access at the SQL query level.
3. **Neo4j Knowledge Graph (`app/graph_store.py`)**: Every node ID is prefixed with `<user_id>::` (e.g., `user_123::postgresql`) and every Cypher `MATCH` filters on `{user_id: $user_id}`, guaranteeing complete graph isolation between users.
4. **Google ADK Session Service (`app/api.py` & `app/agent.py`)**: ADK chat sessions are keyed by `(app_name, user_id, session_id)` and the active `user_id` is dynamically injected into the agent's system instruction via `build_agent_instruction(ReadonlyContext)`.
