# Troubleshooting Guide

Solutions for common issues encountered when running the **ADK Agentic RAG + Knowledge Graph** platform.

---

## 1. Database & Connection Issues

### `ERROR: database "...sslmode=require" does not exist` or `connection is insecure (try using sslmode=require)`

**Cause**: The `DATABASE_URL` in `.env` was missing the `?` query separator before `sslmode=require`.

**Fix**:
Ensure your `DATABASE_URL` in `.env` includes `?sslmode=require`:
```env
DATABASE_URL=postgresql://user:password@ep-xxx.region.aws.neon.tech/dbname?sslmode=require
```
*(Note: `app/database.py` also includes `_normalize_database_url()` to auto-repair missing `?` delimiters at runtime.)*

---

### `Neo4j GqlStatusObject 01N51: warn: relationship type does not exist (RELATES_TO)`

**Cause**: Neo4j 5+ emits informational GQL notifications when querying relationship types or node labels on a newly created, empty database before any document has been ingested.

**Fix**:
1. `app/database.py` suppresses these harmless notifications via `NotificationMinimumSeverity.OFF`.
2. Restart `uvicorn app.api:app --reload` or upload your first document to create the initial `:Entity` and `:RELATES_TO` elements.

---

### `Neo4j connection warning` on startup

**Cause**: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, or `NEO4J_DATABASE` in `.env` does not match your running Neo4j instance, or your Neo4j AuraDB instance is paused.

**Fix**:
- Check your credentials in `.env`.
- If using Neo4j AuraDB Free tier, verify in the [Aura Console](https://console.neo4j.io) that your instance is **Running** (Aura Free instances pause after inactivity) and that `NEO4J_DATABASE` matches your database name.

---

## 2. Frontend & Vite Proxy Issues

### `[vite] http proxy error: connect ECONNREFUSED 127.0.0.1:8000`

**Cause**: The Vite frontend dev server (`http://localhost:5173`) is trying to proxy API requests to `http://127.0.0.1:8000`, but the FastAPI backend is not running.

**Fix**:
Start the FastAPI backend in a terminal from the project root:
```bash
source .venv/bin/activate
uvicorn app.api:app --reload
```

---

### `[vite] http proxy error: /documents/upload (socket hang up / ECONNRESET)`

**Cause**: Occurs if the FastAPI server restarts mid-upload or if the backend process is killed while processing a file.

**Fix**:
`app/api.py` stores temporary upload files in the OS system temp directory (`/tmp/adk_rag_uploads`) outside the Uvicorn `--reload` watch tree and executes `ingest_document` in a background worker thread (`asyncio.to_thread`). Ensure you do not edit `.py` files in the project root while an upload is actively in progress.

---

## 3. Authentication Issues

### `HTTP 401: Invalid or expired authentication token`

**Cause**: Your JWT session token expired or `JWT_SECRET_KEY` was changed on the server.

**Fix**:
Click **Sign Out** in the top-right header bar (or sign in again on the Sign In screen) to obtain a fresh JWT token.

---

## 4. Document Ingestion Issues

### `HTTP 400: Unsupported file type`

**Cause**: The uploaded file extension is not in the supported list (for example, legacy `.doc` instead of `.docx`).

**Fix**:
Convert the file to one of the supported extensions: `.pdf`, `.docx`, `.xlsx`, `.xls`, `.pptx`, `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.log`.

---

### `ValueError: No readable text was found in the document`

**Cause**: The uploaded PDF contains scanned images without an embedded text layer, or the file is empty.

**Fix**:
Run OCR on scanned PDFs before uploading, or verify the document contains selectable text.
