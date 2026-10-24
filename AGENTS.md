# Engineering & Coding-Agent Operational Rules (AGENTS.md)

**Project Name:** Agentic RAG System with Centralized Memory and Knowledge Graph  
**Document Version:** 1.0.0  
**Status:** Authoritative Engineering & Agent Governance Standard  
**Sources of Truth:** [PRD.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/PRD.md) | [DESIGN.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DESIGN.md) | [ARCHITECTURE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/ARCHITECTURE.md) | [DATABASE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DATABASE.md) | [API.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/API.md)

---

## 1. Prime Directives & Source-of-Truth Hierarchy

Every coding agent and contributor working in this repository MUST obey the following prime directives before reading, creating, or modifying any file:

1. **Inspect Before Modifying:** Never create, edit, or refactor a file without first inspecting the existing directory structure, neighboring modules, shared types, and tests.
2. **Follow the Canonical Specification Hierarchy:** All implementation decisions are governed by the five project specifications in this strict precedence order:
   1. [PRD.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/PRD.md) — Functional scope, user stories, approved architectural decisions (`D-01` through `D-05`), and out-of-scope boundaries.
   2. [ARCHITECTURE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/ARCHITECTURE.md) — Tech stack, modular monolith boundaries, Google ADK 5-agent hierarchy, and execution data flows.
   3. [DATABASE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DATABASE.md) — PostgreSQL/`pgvector` 9-table schema, constraints, indexes, cascading rules, and RLS policies.
   4. [API.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/API.md) — REST/SSE endpoint contracts, request/response envelopes, error codes, and ADK tool signatures.
   5. [DESIGN.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DESIGN.md) — Visual tokens, typography, tri-pillar provenance badges (`[Doc:N]`, `[KG:N]`, `[Mem:N]`), layout proportions, and accessibility rules.
3. **Reuse Over Reinvention:** Always search `backend/app/schemas/`, `backend/app/repositories/`, and `frontend/src/components/ui/` for existing patterns, helpers, or components before writing new ones.
4. **Zero Unrelated Changes:** Touch only the files and lines directly required by the current task. Never reformat unrelated files, rename stable symbols, or bundle opportunistic refactors into a feature or bugfix.
5. **No Speculative Over-Engineering:** Do not build features listed as Out-of-Scope in [PRD.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/PRD.md) (e.g., no Redis/Celery workers, no Neo4j/GraphDB, no OCR/audio ingestion, no multi-tenant OAuth/SSO, no free-form KG node/edge editing UI).

---

## 2. Code Quality & Naming Conventions

### 2.1 General Code Quality Rules
- **Single Responsibility:** Each module, class, function, or React component must have one clear responsibility. Functions exceeding 60 lines or components exceeding 200 lines must be decomposed into smaller, testable units.
- **Explicit Over Implicit:** Avoid magic constants, positional tuple returns, or dynamic dictionary keys. Use explicit named constants, Enums, Pydantic models, and TypeScript interfaces.
- **Async by Default (Backend):** All I/O-bound operations in FastAPI routes, services, ADK tools, and SQLAlchemy repositories must use `async def` and `await`. Never call blocking synchronous I/O (`requests`, `time.sleep()`, synchronous `psycopg2`) inside the async event loop.
- **Deterministic & Idempotent Logic:** Ingestion pipelines, KG node/edge upserts, and memory conflict checks must be idempotent so retries never produce duplicate records.

### 2.2 Naming Standards across the Stack

| Layer / Artifact | Convention | Examples |
| :--- | :--- | :--- |
| **Python Modules & Packages** | `snake_case` | `document_repo.py`, `ingestion_service.py`, `kg_tools.py` |
| **Python Classes & Pydantic Models** | `PascalCase` | `DocumentRepository`, `CitationItem`, `SynthesisVerifierAgent` |
| **Python Functions, Methods & Variables** | `snake_case` | `hybrid_search_chunks`, `traverse_kg_subgraph`, `session_id` |
| **Python Constants & Enum Members** | `UPPER_SNAKE_CASE` | `ALLOWED_ENTITY_TYPES`, `GROUNDING_THRESHOLD`, `LONG_TERM_SEMANTIC` |
| **React Components & TypeScript Types** | `PascalCase` (files & symbols) | `CitationBadge.tsx`, `ProvenanceDrawer.tsx`, `AgentTraceStep` |
| **React Hooks** | `camelCase` prefixed with `use` | `useTurnStream.ts`, `useRoleContext.ts` |
| **TypeScript Functions & Variables** | `camelCase` | `parseInlineCitations`, `activeCitationId`, `groundingStatus` |
| **Database Tables & Columns** | `snake_case` (plural table names) | `documents`, `document_chunks`, `kg_nodes`, `memory_entries` |
| **REST API Paths & Query Params** | `kebab-case` paths, `snake_case` params | `/api/v1/memory-entries`, `/api/v1/kg/subgraph`, `?memory_scope=LONG_TERM_SEMANTIC` |
| **CSS Custom Properties (Design Tokens)** | `--kebab-case` | `--bg-canvas`, `--provenance-doc-fg`, `--status-grounded-bg` |

---

## 3. Project & Folder Structure Rules

### 3.1 Canonical Directory Layout
The repository is a **Modular Monolith** with two top-level application directories (`backend/` and `frontend/`) and five specification documents at the root. Agents must place files strictly in their designated architectural layer as defined in [ARCHITECTURE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/ARCHITECTURE.md):

```text
adk_rag/
├── PRD.md
├── DESIGN.md
├── ARCHITECTURE.md
├── DATABASE.md
├── API.md
├── AGENTS.md
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory, lifespan, CORS, error handlers ONLY
│   │   ├── config.py                # Pydantic BaseSettings environment loader ONLY
│   │   ├── dependencies.py          # FastAPI Depends() providers (DB session, role & admin guards)
│   │   ├── api/v1/                  # HTTP/SSE route handlers (no direct SQL or raw LLM prompts)
│   │   ├── agents/                  # Google ADK 5-agent definitions, prompts, and FunctionTools
│   │   ├── services/                # Domain orchestration (ingestion, KG extraction, memory, hybrid search)
│   │   ├── repositories/            # Async SQLAlchemy + pgvector queries ONLY
│   │   ├── models/                  # SQLAlchemy 2.0 ORM table declarations ONLY
│   │   ├── schemas/                 # Pydantic v2 request/response/internal DTOs ONLY
│   │   └── utils/                   # Pure stateless utilities (chunker, hashing, logging)
│   ├── migrations/                  # Alembic migrations
│   └── tests/                       # unit/, integration/, e2e/
└── frontend/
    └── src/
        ├── api/                     # Typed fetch & SSE client wrappers ONLY
        ├── components/
        │   ├── layout/              # AppShell, TopHeaderBar, LeftSidebarNav, RoleSwitcherPill
        │   ├── ui/                  # Reusable design-system primitives (CitationBadge, ProvenanceDrawer, etc.)
        │   ├── chat/                # Screen 1 components
        │   ├── documents/           # Screen 2 components
        │   ├── graph/               # Screen 3 components
        │   └── memory/              # Screen 4 components
        ├── pages/                   # 4 top-level route views
        ├── context/                 # React context providers (RoleContext, SessionContext, ThemeContext)
        ├── hooks/                   # Custom React hooks
        ├── types/                   # Shared TypeScript interfaces matching API.md
        └── styles/                  # tokens.css and global styles
```

### 3.2 Strict One-Way Layer Dependency Rule
Dependencies must flow strictly inward:
- **Backend:** `api/v1` $\rightarrow$ `agents` / `services` $\rightarrow$ `repositories` $\rightarrow$ `models` (Database).
  - *Forbidden:* `repositories` must never import from `services`, `agents`, or `api`.
  - *Forbidden:* `api/v1` routers must never execute SQL queries directly or import `models` to run ad-hoc database queries.
  - *Forbidden:* `agents` must never execute raw SQL; all agent data access must go through typed `FunctionTool` wrappers calling `services` or `repositories`.
- **Frontend:** `pages` $\rightarrow$ `components/{chat,documents,graph,memory}` $\rightarrow$ `components/ui` $\rightarrow$ `hooks` / `context` $\rightarrow$ `api` $\rightarrow$ `types`.
  - *Forbidden:* Presentational components in `components/ui/` must never make direct network calls (`fetch`) or depend on route state.

---

## 4. Component & Logic Reuse Rules

1. **Design Token Enforcement:** Every frontend component MUST use the CSS variables defined in `frontend/src/styles/tokens.css` (from [DESIGN.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DESIGN.md) Section 2). Hardcoded hex colors (`#ffffff`, `#2563eb`), arbitrary Tailwind spacing (`w-[347px]`), or off-scale font sizes are strictly prohibited.
2. **Canonical Reusable UI Primitives:** Do not duplicate UI elements across the 4 screens. Always import and reuse the 9 canonical components from `frontend/src/components/ui/`:
   - `CitationBadge` (`[Doc:N]` Cobalt Blue, `[KG:N]` Violet Purple, `[Mem:N]` Teal Cyan)
   - `GroundingStatusBanner` (`GROUNDED`, `PARTIAL`, `ABSTAINED`)
   - `AgentTraceTimeline` & `AgentStepRow` (`Orchestrator`, `DocumentRetrieval`, `KnowledgeGraph`, `Memory`, `SynthesisVerifier`)
   - `ProvenanceDrawer` (360px / 400px right-hand inspector with `Documents`, `KG Paths`, `Shared Memory`, and `Agent Trace` tabs)
   - `IngestionStatusStepper` (`QUEUED` $\rightarrow$ `PARSING` $\rightarrow$ `CHUNKING` $\rightarrow$ `EMBEDDING` $\rightarrow$ `EXTRACTING_KG` $\rightarrow$ `INDEXED` / `FAILED`)
   - `GraphEntityCard` & `GraphRelationshipPill`
   - `MemoryFactCard`
   - `RoleSwitcherPill` (`Researcher` vs. `Knowledge Admin`)
3. **Shared Backend Utilities:** Text chunking (`utils/chunker.py`), SHA-256 content hashing (`utils/hashing.py`), and Reciprocal Rank Fusion scoring (`services/hybrid_search_service.py`) must exist in a single canonical location and be imported wherever needed.

---

## 5. Dependency Management Rules

1. **Lockfile Discipline:** Both `backend/pyproject.toml` (with `uv.lock` or `requirements.lock`) and `frontend/package-lock.json` must be committed and kept in sync with any approved dependency change.
2. **No Unapproved Packages:** Do not install new third-party packages when the standard library or an already-installed package solves the problem:
   - **Backend Approved Stack:** `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`, `google-adk`, `google-genai`, `sqlalchemy[asyncio]`, `asyncpg`, `pgvector`, `alembic`, `pymupdf`, `tiktoken`, `structlog`, `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`.
   - **Frontend Approved Stack:** `react`, `react-dom`, `react-router-dom`, `@tanstack/react-query`, `lucide-react`, `react-force-graph-2d` (or `cytoscape`), `react-markdown`, `remark-gfm`, `tailwindcss`, `vite`, `typescript`, `vitest`, `@playwright/test`.
3. **Forbidden Dependencies:**
   - Do not add `langchain`, `llama-index`, `crewai`, or `autogen` (Decision `D-01` locks **Google ADK**).
   - Do not add `neo4j`, `qdrant-client`, `pinecone-client`, `chromadb`, or `redis` (Decision `D-02` locks **Supabase PostgreSQL + `pgvector`**).
   - Do not add heavy UI component kits (`@mui/material`, `antd`, `bootstrap`) or animation libraries (`gsap`, `animejs`, `three`).
4. **Version Pinning:** Pin major and minor versions for all production dependencies. Never use wildcard (`*`) or unpinned git branch dependencies.

---

## 6. Type Safety & Schema Validation Rules

### 6.1 Python Backend Type Safety
- **100% Type Annotations:** Every function signature (arguments and return value) in `backend/app/` must have explicit Python 3.11+ type annotations.
- **No `Any` Escape Hatches:** Usage of `typing.Any` is forbidden in domain schemas, service signatures, ADK tool definitions, and repository methods. Use `TypedDict`, `Protocol`, generics, or Pydantic `BaseModel`.
- **Pydantic v2 Strict Contracts:**
  - All API request bodies, query parameters, SSE event payloads, and LLM structured-extraction outputs must be validated using Pydantic v2 models (`ConfigDict(extra="forbid", from_attributes=True)`).
  - Knowledge Graph extraction via Gemini (`extraction_service.py`) must use `response_schema` bound to a Pydantic model that enforces the allowed entity and relation enums from Decision `D-03` (`System`, `Component`, `Organization`, `Person`, `Concept`, `Process`, `Policy`, `Location`, `Event`; and `DEPENDS_ON`, `PART_OF`, `MANAGED_BY`, `AUTHORED_BY`, `CAUSES`, `MITIGATES`, `COMMUNICATES_WITH`, `GOVERNED_BY`, `LOCATED_IN`, `RELATED_TO`).
- **ADK Tool Signatures:** Every Google ADK `FunctionTool` must have complete parameter type hints and a structured docstring describing each argument and the exact dictionary/model return structure so the Gemini model can invoke it deterministically.

### 6.2 TypeScript Frontend Type Safety
- **Strict Compiler Mode:** `tsconfig.json` must maintain `"strict": true`, `"noImplicitAny": true`, `"strictNullChecks": true`, and `"noUncheckedIndexedAccess": true`.
- **Forbidden Constructs:** Never use `any`, `@ts-ignore`, or `@ts-expect-error` in production code. Use discriminated unions (e.g., for SSE events `turn.started | agent.step.started | agent.step.completed | response.delta | response.citations | turn.completed | turn.error`) and type guards.
- **API Contract Parity:** Every interface in `frontend/src/types/api.ts` must mirror the exact field names (`snake_case` JSON properties) and types defined in [API.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/API.md).

---

## 7. Error Handling & Resilience Rules

1. **Standardized API Error Envelope:** Every non-2xx HTTP response from the backend MUST return the canonical error envelope defined in [API.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/API.md) Section 3:
   ```json
   {
     "error": {
       "code": "MACHINE_READABLE_CODE",
       "message": "Clear, user-safe explanation.",
       "details": {},
       "request_id": "req_01J8Z9X2..."
     }
   }
   ```
2. **No Silent Exceptions:** Never write bare `except:` or `except Exception: pass`. Every caught exception must either be translated into a domain exception with context, logged via `structlog` with `request_id` and `session_id`, or re-raised.
3. **External AI Call Resilience:**
   - All Gemini LLM and `text-embedding-004` calls must enforce explicit timeouts (`15s` per retrieval/extraction call, `45s` overall turn budget) and exponential backoff (`1s`, `2s`, `4s`, max 3 attempts) on transient `429` or `503` errors.
4. **Partial Modality Degradation:** If one retrieval tool times out during a turn (e.g., `traverse_kg_subgraph` fails while `search_document_chunks` succeeds), the `OrchestratorAgent` and `SynthesisVerifierAgent` must degrade gracefully, log the failed tool in `agent_execution_logs` (`status = 'FAILED'`), and synthesize a `PARTIAL` or `GROUNDED` response from the surviving evidence rather than crashing the turn with a `500`.
5. **Ingestion Failure Isolation:** If document ingestion fails at any stage (`PARSING`, `CHUNKING`, `EMBEDDING`, `EXTRACTING_KG`), catch the error in `ingestion_service.py`, roll back the partial transaction, and update `documents.status = 'FAILED'` with a human-readable `error_message` and `failed_stage` so the user can inspect and click **Retry Ingestion**.
6. **Zero Hallucination / Abstention Enforcement:** If `SynthesisVerifierAgent` detects unsupported claims or zero retrieved evidence above the similarity threshold, it must set `grounding_status = 'ABSTAINED'` and return a transparent abstention explanation rather than fabricating an answer.

---

## 8. Security & Secrets Rules

1. **Strict Secret Isolation:**
   - `GOOGLE_API_KEY`, `DATABASE_URL`, `DIRECT_DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `ADMIN_API_KEY` must exist **only** in `backend/.env` (loaded via `backend/app/config.py`).
   - Never prefix any secret with `VITE_` or reference secrets anywhere in `frontend/`.
   - Never hardcode API keys, database passwords, or tokens in source files, migrations, tests, or documentation.
   - Never log secret values, raw authorization headers, or full 768-dimensional embedding arrays.
2. **Server-Side Authorization Enforcement (`D-05`):**
   - Frontend role toggling (`Researcher` vs. `Knowledge Admin`) is a UX convenience only.
   - Every mutating admin endpoint (`POST /api/v1/documents`, `POST /api/v1/documents/{id}/retry`, `DELETE /api/v1/documents/{id}`, `PATCH /api/v1/memory-entries/{id}`, `DELETE /api/v1/memory-entries/{id}`) MUST enforce the `require_admin_role` dependency on the backend, verifying both `X-App-Role: admin` and constant-time comparison (`secrets.compare_digest`) of `X-Admin-Api-Key`.
3. **Input Validation & Sanitization:**
   - Validate uploaded files by checking magic bytes (`%PDF-` for PDF, valid UTF-8 for `.md`/`.txt`), enforcing the 20 MB size limit (`413 FILE_TOO_LARGE`), and stripping path traversal sequences from `file_name`.
   - Render all LLM-generated Markdown and document chunks on the frontend through `react-markdown` without `dangerouslySetInnerHTML` or raw HTML execution.
4. **Verified-Only Memory Writes (`D-04`):**
   - Only `MemoryAgent` may write `LONG_TERM_SEMANTIC` or `LONG_TERM_EPISODIC` rows to `memory_entries`, and **only after** `SynthesisVerifierAgent` confirms `grounding_status == 'GROUNDED'` with at least one valid `source_chunk_id` or `source_node_id`. Unverified user prompts or ungrounded LLM outputs must never pollute shared memory.

---

## 9. Database & API Access Rules

1. **Repository Pattern Enforcement:** All SQL and `pgvector` queries must live inside `backend/app/repositories/`. Use SQLAlchemy 2.0 `select()`, `insert()`, `update()`, `delete()`, or bound parameterized `text()` statements (for the `traverse_kg_subgraph` recursive CTE).
2. **Zero String-Interpolated SQL:** Never use Python f-strings or `%` formatting to construct SQL strings. Every runtime variable must be bound as a query parameter to prevent SQL injection.
3. **Schema & Migration Discipline:**
   - Never modify database tables manually or use `Base.metadata.create_all()` in production code.
   - Every schema change must be authored as a reversible Alembic migration in `backend/migrations/versions/` that strictly matches [DATABASE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DATABASE.md).
4. **Cascading Provenance Hygiene:**
   - When deleting a document (`DELETE /api/v1/documents/{document_id}`), execute the cleanup inside a single atomic database transaction (`document_repo.py`): cascade-delete `document_chunks`, prune `kg_edges` and `kg_nodes` whose only provenance was that document (`primary_document_id = document_id`), and mark orphaned `memory_entries` (`source_chunk_id IS NULL AND source_node_id IS NULL`) as `status = 'INVALIDATED'`.
5. **Bounded Queries & Pagination:**
   - Every list endpoint (`GET /api/v1/documents`, `GET /api/v1/sessions`, `GET /api/v1/kg/nodes`, `GET /api/v1/memory-entries`) must enforce cursor pagination (`limit` max 100, default 20). Never execute unbounded `SELECT *` queries without `LIMIT`.
   - Knowledge Graph traversal (`traverse_kg_subgraph`) must clamp `max_hops` to `1..3` (default `2`) and `max_nodes` to `<= 150`.

---

## 10. Testing Rules

1. **Mandatory Verification Before Completion:** No task is complete until automated tests and type checks pass. Agents must run relevant checks after every code change:
   - **Backend Lint & Types:** `ruff check backend/` and `mypy backend/app`
   - **Backend Tests:** `pytest backend/tests`
   - **Frontend Types & Build:** `npm --prefix frontend run typecheck` and `npm --prefix frontend run test`
2. **Three-Tier Testing Requirements:**
   - **Unit Tests (`backend/tests/unit/`, `frontend/src/**/*.test.tsx`):** Test chunking boundary logic, SHA-256 deduplication, RRF score fusion, citation parser (`[Doc:N]`, `[KG:N]`, `[Mem:N]`), Pydantic schema validators, and UI badge/banner states in isolation without network calls.
   - **Integration Tests (`backend/tests/integration/`):** Test repository queries against a real PostgreSQL + `pgvector` test database (hybrid vector + FTS search, `traverse_kg_subgraph` cycle prevention, document deletion cascading cleanup, and `X-Admin-Api-Key` guards). Mock external Gemini API calls using deterministic fixtures so tests never consume live API quota or fail due to network jitter.
   - **End-to-End Tests (`frontend/tests/e2e/`):** Verify the 4 core user journeys from [PRD.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/PRD.md) (Document Upload $\rightarrow$ Grounded Multi-Hop Chat with Provenance Drawer $\rightarrow$ KG Explorer Subgraph Inspection $\rightarrow$ Memory Inspector Edit/Delete).
3. **Bugfix Regression Rule:** Whenever fixing a bug, first write or update a test that reproduces the failure, then apply the minimal fix until the test passes.

---

## 11. Documentation Rules

1. **Keep Specifications Synchronized:** If an approved user change alters an endpoint contract, database column, architectural boundary, or UI component state, update the corresponding specification file ([PRD.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/PRD.md), [DESIGN.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DESIGN.md), [ARCHITECTURE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/ARCHITECTURE.md), [DATABASE.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/DATABASE.md), or [API.md](file:///home/drona/Documents/GitHub/ADK_Learning/Project/adk_rag/API.md)) in the same change set.
2. **Preserve Existing Comments & Docstrings:** Never delete existing explanatory comments, docstrings, or architectural notes unless they are directly invalidated by the current change.
3. **ADK Agent & Tool Docstrings:** Every ADK agent instruction prompt (`agents/prompts.py`) and every `FunctionTool` docstring must clearly document its inputs, outputs, and grounding rules, because the Gemini runtime uses tool docstrings as part of its tool-selection context.
4. **No Redundant Noise Comments:** Write self-documenting code; reserve inline comments for *why* a non-obvious decision was made (e.g., RRF constant `k=60`, `pgvector` HNSW `ef_search` tuning, or cycle prevention in recursive CTEs).

---

## 12. Git & Change Discipline

1. **Pre-Flight & Post-Flight Checks:**
   - Before starting work, inspect `git status` and `git diff` to understand the workspace state.
   - Before declaring any task finished, run `git status` and `git diff` to verify that no temporary files, debug print statements (`print()`, `console.log()`), `.env` files, or unintended edits are present.
2. **Atomic, Scoped Changes:** Keep each change focused on a single logical unit of work (e.g., database models & migration, a single service + repository slice, or one frontend screen).
3. **Conventional Commit Messages:** Format commit messages using Conventional Commits:
   - `feat(agents): implement SynthesisVerifierAgent grounding check`
   - `feat(ui): add ProvenanceDrawer with Doc, KG, and Mem tabs`
   - `fix(ingestion): handle corrupt PDF syntax error with FAILED_PARSE code`
   - `test(kg): add cycle detection integration test for traverse_kg_subgraph`
   - `docs(api): align memory conflict endpoint response schema`
4. **Protected Files & Destructive Git Commands:**
   - Never commit `.env`, `.venv/`, `node_modules/`, `__pycache__/`, or local build artifacts (`dist/`, `.coverage`).
   - Never run destructive git commands (`git reset --hard`, `git checkout -- .`, `git clean -fd`, `git push --force`) unless explicitly instructed by the user.

