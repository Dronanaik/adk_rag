# Release Notes — `v2.2.0`

**Release Title:** Lossless Document & Table Extraction with IBM Docling (`v2.2.0`)  
**Tag:** `v2.2.0`  
**Previous Tag:** `v2.1.1`

> **Combining Agentic RAG, Knowledge Graphs, and Hybrid Vector-Graph Retrieval to transform fragmented information into connected intelligence, powered by Google ADK and Gemini 2.5.**

---

## What's New & Improved in `v2.2.0`

### 1. Lossless Layout & Table Extraction Engine with IBM Docling (`app/parsers.py`, `requirements.txt`)
- **IBM Docling Integration (`docling.document_converter.DocumentConverter`)**: Integrated `docling` as the primary layout-aware document converter in Step 1 (`extract_with_docling`), exporting `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.html`, `.htm`, `.md`, and `.csv` documents into structured GitHub-Flavored Markdown (`export_to_markdown()`).
- **Zero-Content-Loss Reconciliation Across All 13 File Formats**:
  - **PDF (`.pdf`)**: Combines Docling's layout & TableFormer conversion with PyMuPDF (`page.get_text("text", sort=True)` + `page.find_tables()`) page-coverage reconciliation so no page, multi-column text block, or embedded table is ever dropped.
  - **Word (`.docx`)**: Traverses the full Word XML body (`w:p` paragraphs with `#`/`##`/`###` heading hierarchy + `w:tbl` tables rendered as Markdown tables) as well as section `header` and `footer` paragraphs.
  - **PowerPoint (`.pptx`)**: Recursively extracts slide text frames, nested grouped shapes (`shape.shapes`), slide tables (`shape.has_table` formatted as Markdown tables), and presenter speaker notes (`slide.notes_slide.notes_text_frame`).
  - **Excel & CSV (`.xlsx`, `.xls`, `.csv`)**: Converts every worksheet and CSV table into structured Markdown tables (`| Header 1 | Header 2 |`) so column headers stay bound to cell values.
  - **HTML (`.html`, `.htm`)**: Converts HTML headings, lists, and `<table>` elements into structured Markdown via Docling + `_LosslessHTMLParser`.

### 2. Table-Header-Preserving Semantic Chunking (`app/chunking.py`)
- Added `_split_markdown_table_block` to `app/chunking.py` so that when a large Markdown table spans multiple `1,200`-character chunks, it splits cleanly along table row boundaries (`\n`) and repeats the Markdown table header (`| Col 1 | Col 2 |\n| --- | --- |`) at the top of each continuation chunk.

### 3. Cross-Platform One-Command Project Setup (`setup.sh`, `setup.bat`)
- Added `setup.sh` (Linux/macOS/WSL) and `setup.bat` (Windows) to automate prerequisite verification, Python `.venv` creation, CPU PyTorch + Docling + backend package installation, `frontend` npm installation, `.env` initialization with auto-generated `JWT_SECRET_KEY`, and optional `--with-docs` / `--start` flags.

---

# Release Notes — `v2.1.1`

**Release Title:** SHA-256 Content Deduplication & Atomic Document Version Replacement (`v2.1.1`)  
**Tag:** `v2.1.1`  
**Previous Tag:** `v2.1.0`

> **Combining Agentic RAG, Knowledge Graphs, and Hybrid Vector-Graph Retrieval to transform fragmented information into connected intelligence, powered by Google ADK and Gemini 2.5.**

---

## What's New & Fixed in `v2.1.1`

### 1. SHA-256 Content-Hash Deduplication & Atomic Version Replacement (`app/ingest.py`, `app/rag_store.py`)
- **Normalized SHA-256 Content Fingerprinting**: Every uploaded document's extracted text is normalized (`re.sub(r"\s+", " ", text.strip())`) and hashed with `SHA-256`, stored in `documents.metadata.content_hash` in Neon PostgreSQL (with automatic backfill for pre-`v2.1.1` rows).
- **Three-Scenario Redundant & Updated File Handling (`find_existing_user_document`)**:
  1. **Exact Same File Uploaded Again (`same filename` + `same content_hash` → `ingest_action: "unchanged"`)**: Skips redundant Gemini embedding and Neo4j LLM extraction calls, fast-completes Step 5, and returns the existing document metrics (`Skipped (Already Indexed)`).
  2. **Same Content with Different Filename (`different filename` + `same content_hash` → `ingest_action: "duplicate_content"`)**: Prevents duplicate vector chunks and duplicate graph triples from polluting retrieval rankings and returns the existing document reference (`Skipped (Duplicate of <existing_filename>)`).
  3. **Updated Version of an Existing File (`same filename` + `different content_hash` → `ingest_action: "updated"`)**: Atomically purges the previous version's chunks from Neon PostgreSQL (`delete_document_chunks`) and its relationships/orphaned entities from Neo4j (`delete_document_from_graph`) before indexing the updated document (`Updated Version`).
  4. **Brand-New Document (`no match` → `ingest_action: "created"`)**: Executes the full 5-step dual ingestion pipeline (`Indexed (New)`).

### 2. Action Status Badges in the Ingestion Pipeline UI (`frontend/src/components/IngestionTab.jsx`, `frontend/src/App.jsx`)
- Added real-time status badges (`Indexed (New)`, `Updated Version`, `Skipped (Already Indexed)`, `Skipped (Duplicate of <filename>)`) and `action_detail` summaries to both single-document and multi-document batch completion cards in `IngestionTab.jsx`.

---

# Release Notes — `v2.1.0`

**Release Title:** Multi-Document Upload, Batch Ingestion Pipeline & E2E Walkthrough (`v2.1.0`)  
**Tag:** `v2.1.0`  
**Previous Tag:** `v2.0.1`

> **Combining Agentic RAG, Knowledge Graphs, and Hybrid Vector-Graph Retrieval to transform fragmented information into connected intelligence, powered by Google ADK and Gemini 2.5.**

---

## What's New & Fixed in `v2.1.0`

### 1. Multi-Document Upload & Per-Document 5-Step Batch Ingestion (`frontend/src/components/UploadTab.jsx`, `frontend/src/components/IngestionTab.jsx`, `frontend/src/App.jsx`, `app/ingest.py`, `app/api.py`)
- **Multi-File Selection & Drag-and-Drop (`UploadTab.jsx`)**: Added multi-file browser selection (`<input type="file" multiple>`) and multi-file drag-and-drop with an interactive file queue displaying each file's index, icon, size, individual **Remove** button, **Add More Files**, and **Clear All**.
- **Per-Document Live Pipeline Progress (`IngestionTab.jsx`, `app/ingest.py`)**: When uploading multiple files, each document runs sequentially through all 5 pipeline stages (`0%` → `100%`) while displaying **`Selected Document X of Y • Step S of 5 • <Step Name>`** in the live progress banner.
- **Multi-Document Completion Summary (`IngestionTab.jsx`)**: Upon completion of a multi-file batch, the completion card displays **`All 5 Pipeline Steps Completed Successfully (Y Documents Ingested)`**, aggregates total chunks, entities, relationships, and characters across all ingested documents, and lists per-document ingestion metrics.

---

# Release Notes — `v2.0.1`

**Release Title:** Domain-Agnostic Knowledge Graph Extraction & SVG Topology Centering Fix (`v2.0.1`)  
**Tag:** `v2.0.1`  
**Previous Tag:** `v2.0.0`

---

## What's Fixed in `v2.0.1`

### 1. Domain-Agnostic Knowledge Graph Routing & Extraction (`app/agent.py`, `app/graph_store.py`, `frontend/src/components/GraphTab.jsx`)
- **Unrestricted Agent Graph Tool Selection (`app/agent.py`)**: Fixed overly narrow `graph_search` and `get_entity_relationships` routing instructions that previously only listed `concepts, technologies, people, or organizations`. The agent now triggers Knowledge Graph retrieval across **any** domain entity category, attribute, hierarchy, dependency, or multi-hop relationship present in the uploaded document.
- **Dynamic Entity Category Inference (`app/graph_store.py`)**: Removed the rigid 8-category constraint in `ExtractedEntity.entity_type` and `EXTRACTION_PROMPT`, enabling Gemini 2.5 to dynamically infer concise, singular `Title Case` entity categories tailored to the document's domain (e.g., `Skill`, `Project`, `Certification`, `Education`, `Role`, `Product`, `Policy`, `Clause`, `Regulation`, `Dataset`, `Component`, `Condition`, `Medication`, etc.) and added `entity_type` matching to Neo4j Cypher search queries (`search_knowledge_graph`).
- **Deterministic Category Badge Palette & SVG Topology Centering (`frontend/src/components/GraphTab.jsx`)**:
  - Fixed a division-by-zero (`NaN` coordinate) layout bug in `computeGraphLayout` when filtering down to a single entity category (where the node previously rendered clipped at `(0, 0)` in the top-left corner).
  - Included 1-hop connected neighbor nodes in the filtered SVG canvas so selecting a category pill renders both the matching entity in the center and its connected relationships around it.
  - Expanded `TYPE_COLORS` with cross-domain categories and added deterministic hash-based color assignment in `getTypeStyle`.

### 2. CodeQL Security & Static Analysis Remediation (`app/`, `frontend/`)
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
