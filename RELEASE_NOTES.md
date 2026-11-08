# Release Notes — `v2.1.0`

**Release Title:** Multi-Document Upload, Batch Ingestion Pipeline & Domain-Agnostic Knowledge Graph (`v2.1.0`)  
**Tag:** `v2.1.0`  
**Previous Tag:** `v2.0.0`

> **Combining Agentic RAG, Knowledge Graphs, and Hybrid Vector-Graph Retrieval to transform fragmented information into connected intelligence, powered by Google ADK and Gemini 2.5.**

---

## What's New & Fixed in `v2.1.0`

### 1. Multi-Document Upload & Per-Document 5-Step Batch Ingestion (`frontend/src/components/UploadTab.jsx`, `frontend/src/components/IngestionTab.jsx`, `frontend/src/App.jsx`, `app/ingest.py`, `app/api.py`)
- **Multi-File Selection & Drag-and-Drop (`UploadTab.jsx`)**: Added multi-file browser selection (`<input type="file" multiple>`) and multi-file drag-and-drop with an interactive file queue displaying each file's index, icon, size, individual **Remove** button, **Add More Files**, and **Clear All**.
- **Per-Document Live Pipeline Progress (`IngestionTab.jsx`, `app/ingest.py`)**: When uploading multiple files, each document runs sequentially through all 5 pipeline stages (`0%` → `100%`) while displaying **`Selected Document X of Y • Step S of 5 • <Step Name>`** in the live progress banner.
- **Multi-Document Completion Summary (`IngestionTab.jsx`)**: Upon completion of a multi-file batch, the completion card displays **`All 5 Pipeline Steps Completed Successfully (Y Documents Ingested)`**, aggregates total chunks, entities, relationships, and characters across all ingested documents, and lists per-document ingestion metrics.

### 2. Domain-Agnostic Knowledge Graph Routing & Extraction (`app/agent.py`, `app/graph_store.py`, `frontend/src/components/GraphTab.jsx`)
- **Unrestricted Agent Graph Tool Selection (`app/agent.py`)**: Fixed overly narrow `graph_search` and `get_entity_relationships` routing instructions that previously only listed `concepts, technologies, people, or organizations`. The agent now triggers Knowledge Graph retrieval across **any** domain entity category, attribute, hierarchy, dependency, or multi-hop relationship present in the uploaded document.
- **Dynamic Entity Category Inference (`app/graph_store.py`)**: Removed the rigid 8-category constraint in `ExtractedEntity.entity_type` and `EXTRACTION_PROMPT`, enabling Gemini 2.5 to dynamically infer concise, singular `Title Case` entity categories tailored to the document's domain (e.g., `Skill`, `Project`, `Certification`, `Education`, `Role`, `Product`, `Policy`, `Clause`, `Regulation`, `Dataset`, `Component`, `Condition`, `Medication`, etc.) and added `entity_type` matching to Neo4j Cypher search queries (`search_knowledge_graph`).
- **Deterministic Category Badge Palette & SVG Topology Centering (`frontend/src/components/GraphTab.jsx`)**:
  - Fixed a division-by-zero (`NaN` coordinate) layout bug in `computeGraphLayout` when filtering down to a single entity category (where the node previously rendered clipped at `(0, 0)` in the top-left corner).
  - Included 1-hop connected neighbor nodes in the filtered SVG canvas so selecting a category pill renders both the matching entity in the center and its connected relationships around it.
  - Expanded `TYPE_COLORS` with cross-domain categories and added deterministic hash-based color assignment in `getTypeStyle`.

### 3. CodeQL Security & Static Analysis Remediation (`app/`, `frontend/`)
- Resolved all 16 GitHub CodeQL code scanning alerts across Python and JavaScript (`py/stack-trace-exposure`, `py/log-injection`, `py/polynomial-redos`, `py/weak-sensitive-data-hashing`, `py/path-injection`, `py/empty-except`, `py/unused-import`, and `js/empty-catch-block`).

---

# Release Notes — `v2.0.0`

**Release Title:** ADK Agentic RAG + Knowledge Graph Platform (`v2.0.0`)  
**Tag:** `v2.0.0`  
**Previous Tag:** `adk` (`v1.0.0`)

> **Combining Agentic RAG, Knowledge Graphs, and Hybrid Vector-Graph Retrieval to transform fragmented information into connected intelligence, powered by Google ADK and Gemini 2.5.**

---

## Highlights

`v2.0.0` is a complete architectural evolution from a single-vector RAG prototype into an enterprise-grade **Hybrid Vector + Knowledge Graph Document Intelligence Platform** powered by **Google Agent Development Kit (ADK)**, **Gemini 2.5**, **Neon PostgreSQL (`pgvector` + Full-Text Search)**, and **Neo4j AuraDB**.

---

## What's New in `v2.0.0`

### 1. Neon PostgreSQL Hybrid Vector + Lexical Search & Authentication (`app/database.py`, `app/auth.py`, `app/rag_store.py`)
- **Multi-Tenant Authentication**: Added Neon PostgreSQL `users` table with `PBKDF2-HMAC-SHA256` password hashing (`260,000` iterations) and stateless `HS256` JWT Bearer authentication (`POST /auth/signup`, `POST /auth/login`, `GET /auth/me`).
- **768-Dim `pgvector` HNSW + Full-Text Search (`tsvector`)**: Replaced legacy ChromaDB/Pinecone storage with a unified Neon PostgreSQL schema (`users`, `documents`, `document_chunks`) indexed with **HNSW Cosine (`vector_cosine_ops`)** and **GIN Full-Text Search (`to_tsvector`)**.
- **Weighted Hybrid Retrieval Formula**: Combines `70%` dense semantic vector similarity (`1 - (embedding <=> query_vec)`) with `30%` lexical keyword ranking (`ts_rank_cd`) in a single SQL query.

### 2. Neo4j Knowledge Graph Extraction & Multi-Hop Traversal (`app/graph_store.py`)
- **Structured Entity & Relationship Extraction**: Uses `gemini-2.5-flash` with strict Pydantic JSON schemas (`GraphExtractionResult`) to extract domain entities (`Person`, `Technology`, `Model`, `Organization`, `Concept`, `Metric`, `Location`, `Event`) and directed `RELATES_TO` edges during document ingestion.
- **Idempotent Cypher Upserts & Atomic Cascade Deletion**: Merges `(:Document)-[:MENTIONS]->(:Entity)` and `(:Entity)-[:RELATES_TO]->(:Entity)` triples into Neo4j and atomically cleans up both Neon PostgreSQL and Neo4j (including orphan entity pruning) when a document is deleted (`DELETE /documents/{doc_id}`).

### 3. Live 5-Step Hybrid Ingestion Pipeline (`app/ingest.py`, `app/chunking.py`, `app/parsers.py`)
- **Structure-Aware Semantic Chunking**: Preserves section headings and paragraph boundaries with `1,200`-character windows and `200`-character overlap across **13 file formats** (`.pdf`, `.docx`, `.xlsx`, `.xls`, `.pptx`, `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.htm`, `.log`).
- **Real-Time Progress Telemetry (`GET /ingest/progress`)**: Exposes live step-by-step execution status across all 5 stages (Text Extraction → Semantic Chunking → `gemini-embedding-001` Generation → Neon `pgvector` Indexing → Neo4j Knowledge Graph Extraction).

### 4. Multi-Tool Google ADK Agent (`app/agent.py`)
- **Autonomous 4-Tool Orchestration**: Upgraded `hybrid_rag_kg_agent` (`LlmAgent`) to autonomously select and combine:
  1. `hybrid_search` (Neon PostgreSQL `70%` Vector + `30%` FTS)
  2. `vector_search` (Neon PostgreSQL pure `pgvector` cosine similarity)
  3. `graph_search` (Neo4j entity & relationship search)
  4. `get_entity_relationships` (Neo4j 1-hop neighborhood traversal)
- **Verifiable Dual Citations**: Grounded responses cite both document chunks (`[Source: filename, chunk N]`) and knowledge graph triples (`[Graph: EntityA -> RELATION -> EntityB]`).

### 5. Bioluminescent Neural Forest UI & Interactive Graph Explorer (`frontend/`)
- **Redesigned React 18 + Vite Interface**: Built a 5-tab workspace (**Upload** → **Ingestion Pipeline** → **Documents** → **Agentic Chat** → **Knowledge Graph**) over a Bioluminescent Neural Forest glassmorphism theme.
- **Interactive Neo4j SVG Topology & 1-Hop Inspector**: Added `GraphTab.jsx` featuring category filter pills, real-time triple search, radial SVG entity topology, and 1-hop gold neighborhood highlighting.

### 6. `adk.dev`-Styled Documentation Portal & CI/CD (`docs/`, `mkdocs.yml`, `.github/workflows/`)
- **Documentation Site (`https://dronanaik.github.io/adk_rag/`)**: Added full MkDocs Material documentation replicated after `adk.dev`, including Architecture Blueprints, Technical Specifications, API Reference, and a complete visual User Guide with 12 live application screenshots.
- **GitHub Actions Workflows**: Added automated GitHub Pages deployment (`.github/workflows/mkdocs-deploy.yml`) and upgraded CodeQL Security Analysis to `v4` on Node.js 24 (`.github/workflows/codeql.yml`).

---

## Commit Summary (`adk..v2.0.0`)

- `acf274f` — `feat(neon): integrate Neon PostgreSQL pgvector hybrid store and JWT authentication`
- `43e2fe9` — `feat(neo4j): add Neo4j Knowledge Graph extraction, 5-step live ingestion, and multi-tool ADK agent`
- `3340c79` — `feat(ui): redesign frontend with Bioluminescent Neural Forest theme, Neon auth screen, and Graph Explorer`
- `71a9319` — `docs(mkdocs): add MkDocs configuration, User Guide, Technical Specifications, and Architecture docs`
- `0e72d18` — `chore(cleanup): remove legacy ChromaDB data, old uploads, and unused prototype files`
- `c0ba82e` — `ci(mkdocs): add GitHub Actions workflow to deploy MkDocs to GitHub Pages`
- `03b4235` — `ci: upgrade GitHub Actions to Node 24 compatible versions`
- `3dbe263` / `9c1800f` — `docs(mkdocs): replicate official adk.dev landing page, custom.css, homepage.css, and overrides`
- `f70bcd6` / `307cb16` — `docs(user-guide): add all 12 live application screens and step-by-step visual walkthrough`
- `816dcff` — `docs(header): update announcement banner and site description text`
- `7612915` — `ci(codeql): upgrade codeql-action to v4, enable Node 24, and fix npm ci peer deps`
