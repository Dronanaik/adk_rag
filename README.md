# Agentic RAG System with Centralized Memory and Knowledge Graph

Production-grade **Multi-Agent Retrieval-Augmented Generation (RAG)** workbench built with **Google Agent Development Kit (ADK)**, **FastAPI**, **React 19 + TypeScript**, and **Supabase PostgreSQL + `pgvector`**.

## Canonical Specifications

1. [`PRD.md`](./PRD.md) — Functional scope, user stories, and architectural decisions (`D-01` through `D-05`).
2. [`ARCHITECTURE.md`](./ARCHITECTURE.md) — Modular monolith structure, Google ADK 5-agent hierarchy, and execution data flows.
3. [`DATABASE.md`](./DATABASE.md) — Unified 9-table PostgreSQL + `pgvector` schema, constraints, HNSW/GIN indexes, and `traverse_kg_subgraph` recursive CTE.
4. [`API.md`](./API.md) — REST/SSE endpoint contracts, error envelope conventions, and ADK `FunctionTool` signatures.
5. [`DESIGN.md`](./DESIGN.md) — Visual tokens, typography, tri-pillar provenance badges (`[Doc:N]`, `[KG:N]`, `[Mem:N]`), and layout shell.
6. [`AGENTS.md`](./AGENTS.md) — Authoritative engineering and coding-agent operational rules.

---

## Project Structure

```text
adk_rag/
├── PRD.md
├── DESIGN.md
├── ARCHITECTURE.md
├── DATABASE.md
├── API.md
├── AGENTS.md
├── .env.example
├── supabase/
│   ├── migrations/0001_initial_schema.sql
│   └── seed.sql
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── api/v1/
│   │   ├── agents/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── utils/
│   └── tests/
└── frontend/
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── api/
        ├── components/{layout,ui,chat,documents,graph,memory}/
        ├── context/
        ├── hooks/
        ├── pages/
        ├── styles/
        └── types/
```

---

## Development Setup & Verification Scripts

### 1. Environment Variables
Copy `.env.example` to `backend/.env` and populate your local credentials:
```bash
cp .env.example backend/.env
```

### 2. Backend (Python 3.11+ / FastAPI / Google ADK)
```bash
# Lint & Type Check
ruff check backend/
mypy backend/app

# Run Unit & Integration Tests
pytest backend/tests

# Start Dev Server (http://localhost:8000)
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### 3. Frontend (React 19 / TypeScript / Vite)
```bash
# Install Dependencies
npm --prefix frontend install

# Strict TypeScript Check, Unit Tests, and Production Build
npm --prefix frontend run typecheck
npm --prefix frontend run test
npm --prefix frontend run build

# Start Dev Server (http://localhost:5173)
npm --prefix frontend run dev
```

