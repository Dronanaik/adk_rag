# ADK Agentic RAG + Knowledge Graph

> **Hybrid Document Intelligence Platform** — Upload documents, monitor a live 5-step dual ingestion pipeline, explore interactive Neo4j knowledge graphs, and chat with your documents using **Google ADK**, **Gemini**, **Neon Console PostgreSQL (`pgvector`)**, and **Neo4j**.

---

## Welcome to the Documentation

This documentation covers everything you need to use, understand, configure, and deploy the **ADK Agentic RAG + Knowledge Graph** platform:

| Section | Description |
|---------|-------------|
| **[User Guide](USER_GUIDE.md)** | Step-by-step instructions on how users sign in, upload files, monitor the live 5-step ingestion pipeline, manage documents, ask questions in Agentic Chat, and explore the Knowledge Graph. |
| **[Architecture](ARCHITECTURE.md)** | System design, component breakdown, data flow diagrams (Authentication, Dual Ingestion, Multi-Tool Retrieval, Cascade Deletion), and module responsibilities. |
| **[Technical Specifications](TECHNICAL_SPECIFICATIONS.md)** | Detailed specifications for the tech stack, Neon PostgreSQL & Neo4j schemas, authentication security (`PBKDF2-SHA256` + `HS256` JWT), chunking/embedding parameters, hybrid search scoring, and API contracts. |
| **[Ingestion Pipeline](INGESTION.md)** | Deep dive into format-specific text parsing, structure-aware semantic chunking, batched Gemini embeddings, and Gemini Structured Output graph extraction. |
| **[Agentic Chat & Graph Tools](CHAT.md)** | How the Google ADK `LlmAgent` selects and combines `hybrid_search`, `vector_search`, `graph_search`, and `get_entity_relationships`. |
| **[Frontend Application](FRONTEND.md)** | React 18 + Vite component architecture, Clean Modern SaaS Light theme tokens, and interactive SVG Knowledge Graph canvas. |
| **[API Reference](API.md)** | Request/response schemas and `curl` examples for all FastAPI endpoints. |
| **[Installation](INSTALLATION.md)** | Local setup guide for Python, Node.js, Neon PostgreSQL, and Neo4j. |
| **[Deployment](DEPLOYMENT.md)** | Production deployment guide for Render, Netlify, Neon, and Neo4j AuraDB. |
| **[Troubleshooting](TROUBLESHOOTING.md)** | Solutions for common database, authentication, ingestion, and frontend errors. |

---

## Key Capabilities

1. **Neon PostgreSQL Authentication**: Built-in user accounts (`users` table in Neon Postgres) secured with `PBKDF2-HMAC-SHA256` password hashing and `HS256` JWT Bearer tokens, ensuring strict multi-tenant data isolation.
2. **5-Step Live Dual Ingestion Pipeline**:
   - **Step 1**: Format-specific text extraction (`PDF`, `DOCX`, `XLSX`, `PPTX`, `TXT`, `MD`, `CSV`, `JSON`, `XML`, `HTML`, `LOG`)
   - **Step 2**: Structure-aware semantic paragraph & sentence chunking (`1200` chars, `200`-char overlap)
   - **Step 3**: Batched `768`-dimensional vector embedding generation via `gemini-embedding-001`
   - **Step 4**: Neon PostgreSQL `pgvector` HNSW + `tsvector` GIN indexing
   - **Step 5**: Gemini Structured Output entity/relationship extraction & Neo4j `MERGE` persistence
3. **Multi-Tool Google ADK Agent**:
   - `hybrid_search`: Combined semantic vector similarity (`70%`) + PostgreSQL full-text rank (`30%`)
   - `vector_search`: Pure semantic cosine similarity over `pgvector`
   - `graph_search`: Keyword search across Neo4j entities and factual triplets
   - `get_entity_relationships`: Multi-hop neighborhood traversal around specific entities
4. **Interactive Knowledge Graph Explorer**: Force-layout SVG canvas with category filtering, search, zoom controls, and 1-hop relationship inspection drawer.

---

## Previewing This Documentation Locally

```bash
source .venv/bin/activate
pip install mkdocs mkdocs-material
mkdocs serve -a 127.0.0.1:8001
```

Then open `http://127.0.0.1:8001` in your browser.
