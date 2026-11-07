# ADK Agentic RAG + Knowledge Graph

> *"Where Knowledge Connects, Agents Reason, and Intelligence Emerges."*
>
> **Hybrid Document Intelligence Platform** — Authenticate, upload, monitor a live 5-step dual ingestion pipeline, explore interactive knowledge graphs, and chat with your documents using **Google ADK**, **Gemini**, **Neon Console PostgreSQL (`pgvector`)**, and **Neo4j**.
>
> *Inspired by [`coleam00/ottomator-agents/agentic-rag-knowledge-graph`](https://github.com/coleam00/ottomator-agents/tree/main/agentic-rag-knowledge-graph)*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-latest-4285F4?logo=google&logoColor=white)](https://developers.google.com/adk)
[![Neon PostgreSQL](https://img.shields.io/badge/Neon%20Postgres-pgvector-00E599?logo=postgresql&logoColor=white)](https://neon.tech)
[![Neo4j](https://img.shields.io/badge/Neo4j-Knowledge%20Graph-008CC1?logo=neo4j&logoColor=white)](https://neo4j.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)

<br/>

## End-to-End Platform Demonstration

<video src="docs/adk_rag.mp4" width="100%" controls autoplay loop muted></video>

![ADK Agentic RAG + Knowledge Graph End-to-End Walkthrough](docs/assets/adk_rag_demo.gif)

> **Full Recorded Video (MP4):** [`docs/adk_rag.mp4`](docs/adk_rag.mp4)

---

## Overview

**ADK Agentic RAG + Knowledge Graph** upgrades traditional single-tool RAG into a **Hybrid Agentic RAG** system:
1. **Neon Console PostgreSQL (`pgvector` + `tsvector`)** stores structure-aware document chunks and 768-dimensional Gemini embeddings for both semantic vector search and hybrid keyword+vector retrieval.
2. **Neo4j Knowledge Graph** stores domain entities (`Person`, `Organization`, `Technology`, `Concept`, `Model`, `Metric`, etc.) and factual relationships (`RELATES_TO`) extracted automatically during ingestion using Gemini Structured Outputs.
3. **Google ADK `LlmAgent`** dynamically chooses between four tools—`hybrid_search`, `vector_search`, `graph_search`, and `get_entity_relationships`—or combines them to answer complex questions with full citations.
4. **Neon PostgreSQL Authentication** provides full user registration and sign-in (`users` table in Neon Postgres secured with `PBKDF2-HMAC-SHA256` and `HS256` JWT Bearer tokens).
5. **Bioluminescent Neural Forest UI** features an atmospheric Tree of Knowledge backdrop, translucent emerald-pine glass cards, cyan & golden firefly accents, live step-by-step ingestion tracking, and an interactive **Knowledge Graph Explorer** tab.

---

## Features

| Feature | Details |
|---------|---------|
| **Neon Authentication** | Sign Up / Sign In backed by Neon PostgreSQL (`PBKDF2-SHA256` password hashing + `HS256` JWT tokens) |
| **Document Upload** | PDF, DOCX, XLSX, XLS, PPTX, TXT, MD, CSV, JSON, XML, HTML, LOG |
| **Live 5-Step Pipeline** | Real-time per-step progress polling (`Completed`, `Running Now...`, `Queued`) |
| **Semantic Chunking** | Structure-aware paragraph & sentence chunking (1200 chars, 200-char overlap) |
| **Embeddings** | Gemini `gemini-embedding-001` (batched, 768 dimensions) |
| **Vector & Hybrid Store** | **Neon Console PostgreSQL** with `pgvector` HNSW index + `tsvector` GIN full-text index |
| **Knowledge Graph** | **Neo4j** storing `(:Entity)-[:RELATES_TO]->(:Entity)` and `(:Document)` nodes |
| **Agentic RAG Tools** | `hybrid_search`, `vector_search`, `graph_search`, `get_entity_relationships` |
| **Dual Citations** | `[Source: filename, chunk N]` and `[Graph: Source -> RELATION -> Target]` |
| **Bioluminescent Forest UI** | Neural Tree backdrop + translucent emerald glass cards + Interactive SVG Knowledge Graph Explorer |
| **User Isolation** | Every SQL row and Neo4j node/edge is strictly scoped by `user_id` |

---

## Hybrid Ingestion & Retrieval Pipeline

```
File Uploaded
    ↓
parsers.py       — Format-specific text extraction
    ↓
chunking.py      — Structure-aware paragraph & sentence chunking (1200 chars, 200 overlap)
    ├──→ embeddings.py + rag_store.py  → Neon PostgreSQL (pgvector + Full-Text Search)
    └──→ graph_store.py (Gemini JSON)  → Neo4j Knowledge Graph (Entities & Relationships)
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)
- A [Neon Console PostgreSQL](https://console.neon.tech) database connection string (`DATABASE_URL`)
- A [Neo4j AuraDB](https://console.neo4j.io) or local Neo4j instance (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`)

### 1 — Set up the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2 — Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GOOGLE_API_KEY=your_google_api_key_here
AGENT_MODEL=gemini-2.5-pro
GRAPH_EXTRACTION_MODEL=gemini-2.5-flash

# Neon Console PostgreSQL (pgvector is enabled automatically on startup)
DATABASE_URL=postgresql://neondb_owner:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require

# JWT Secret for Neon Authentication
JWT_SECRET_KEY=replace-with-a-secure-random-secret-key
JWT_EXPIRE_HOURS=168

# Neo4j Knowledge Graph
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
NEO4J_DATABASE=neo4j

TOP_K=5
```

> Note: On startup, the backend automatically initializes the `pgvector` extension, PostgreSQL tables/indexes (also available in `sql/schema.sql`), and Neo4j constraints/indexes.

### 3 — Start the FastAPI backend

```bash
uvicorn app.api:app --reload
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### 4 — Start the React UI

```bash
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

---

## Project Structure

```
adk_rag/
├── app/
│   ├── __init__.py
│   ├── agent.py          # Google ADK LlmAgent with 4 hybrid vector + graph tools
│   ├── api.py            # FastAPI endpoints (auth, upload, progress, chat, documents, graph)
│   ├── auth.py           # Neon PostgreSQL authentication (PBKDF2-SHA256 + HS256 JWT)
│   ├── chunking.py       # Structure-aware semantic chunker
│   ├── config.py         # Environment variable configuration
│   ├── database.py       # Neon PostgreSQL pool + Neo4j driver & schema init
│   ├── embeddings.py     # Batched Gemini embedding wrapper (768-dim)
│   ├── graph_store.py    # Gemini Structured Output extraction + Neo4j Cypher CRUD/search
│   ├── ingest.py         # 5-step dual ingestion with live step progress tracking
│   ├── parsers.py        # Format-specific text extractors
│   └── rag_store.py      # Neon PostgreSQL (pgvector + FTS) CRUD & hybrid search
├── docs/
│   ├── index.md                      # MkDocs documentation home
│   ├── USER_GUIDE.md                 # Step-by-step end-user interaction guide
│   ├── ARCHITECTURE.md               # System architecture & data flow diagrams
│   ├── TECHNICAL_SPECIFICATIONS.md   # Database schemas, auth, scoring & API specs
│   ├── INGESTION.md                  # 5-step dual ingestion pipeline deep dive
│   ├── CHAT.md                       # Google ADK multi-tool agent guide
│   ├── FRONTEND.md                   # React 18 UI & Knowledge Graph guide
│   ├── API.md                        # REST API reference
│   ├── INSTALLATION.md               # Local setup instructions
│   ├── DEPLOYMENT.md                 # Production cloud deployment guide
│   └── TROUBLESHOOTING.md            # Common error resolutions
├── sql/
│   └── schema.sql        # Reference Neon PostgreSQL pgvector schema
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UserIdModal.jsx    # Neon PostgreSQL Sign In / Create Account screen
│   │   │   ├── Header.jsx         # Sticky top navigation bar
│   │   │   ├── Tabs.jsx           # 5-tab navigation bar
│   │   │   ├── UploadTab.jsx      # Drag-and-drop document upload
│   │   │   ├── IngestionTab.jsx   # Live 5-step hybrid pipeline & Neon/Neo4j metrics
│   │   │   ├── DocumentsTab.jsx   # Document list + cascade delete
│   │   │   ├── GraphTab.jsx       # Interactive Neo4j Knowledge Graph explorer
│   │   │   ├── ChatTab.jsx        # Agentic RAG + Graph chat interface
│   │   │   └── ChatMessage.jsx    # Message bubble with tool badges & citations
│   │   ├── api.js         # Frontend API client
│   │   ├── App.jsx        # Root React application
│   │   └── index.css      # Bioluminescent Neural Forest Design System
│   ├── public/
│   │   └── bg-neural-tree.jpg # Tree of Knowledge backdrop artwork
│   └── package.json
├── mkdocs.yml            # MkDocs documentation site configuration
├── .env.example
├── requirements.txt
└── README.md
```

---

## Documentation (MkDocs)

Comprehensive documentation is available in the `docs/` directory and configured for **MkDocs**:

- **[User Guide](docs/USER_GUIDE.md)** — Step-by-step guide on how to sign in, upload documents, monitor live 5-step ingestion, manage files, chat with the ADK agent, and explore the Knowledge Graph.
- **[Architecture](docs/ARCHITECTURE.md)** — High-level system architecture, module breakdown, and sequence diagrams for authentication, dual ingestion, multi-tool retrieval, and cascade deletion.
- **[Technical Specifications](docs/TECHNICAL_SPECIFICATIONS.md)** — Full engineering specs covering Neon PostgreSQL & Neo4j schemas, `PBKDF2-SHA256` + `HS256` JWT security, hybrid search scoring formulas, and structured output schemas.

To serve the interactive documentation site locally:

```bash
source .venv/bin/activate
pip install mkdocs mkdocs-material
mkdocs serve -a 127.0.0.1:8001
# Open http://127.0.0.1:8001
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/auth/signup` | Create a user account in Neon PostgreSQL |
| `POST` | `/auth/login` | Sign in with email & password and receive a Bearer JWT |
| `GET` | `/auth/me` | Verify active Bearer JWT session |
| `GET` | `/ingest/status` | Neon Postgres + Neo4j pipeline status & counts |
| `GET` | `/ingest/progress` | Real-time step-by-step status for the 5 ingestion stages |
| `POST` | `/documents/upload` | Upload & ingest into Neon Postgres + Neo4j |
| `GET` | `/documents` | List user's documents with chunk/entity/relation counts |
| `DELETE` | `/documents/{id}` | Cascade-delete document from Neon Postgres & Neo4j |
| `GET` | `/graph` | Fetch user's Neo4j nodes, edges, and stats for UI visualization |
| `GET` | `/graph/entity/{name}` | Traverse 1-hop relationships for a specific entity |
| `POST` | `/chat` | Chat with the multi-tool Google ADK agent |
