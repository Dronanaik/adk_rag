# Installation & Local Setup Guide

This guide walks you through setting up the **ADK Agentic RAG + Knowledge Graph** platform locally.

---

## 1. Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **Python** | `3.10+` (`3.12` recommended) | FastAPI backend & Google ADK agent |
| **Node.js & npm** | `18+` | React 18 + Vite frontend |
| **Google Gemini API Key** | Free / Paid Tier | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| **Neon Console PostgreSQL** | Free / Serverless Tier | [Neon Console](https://console.neon.tech) (`pgvector` enabled automatically) |
| **Neo4j Database** | AuraDB Free or Local `5.x` | [Neo4j Aura Console](https://console.neo4j.io) or local Docker instance |

---

## 2. One-Command Automated Setup (`setup.sh` / `setup.bat`)

After cloning the repository, you can set up the entire project (Python `.venv`, backend packages + Docling, React + Vite frontend dependencies, and `.env` with an auto-generated `JWT_SECRET_KEY`) using a single command:

=== "Linux / macOS / WSL (`setup.sh`)"

    ```bash
    git clone https://github.com/Dronanaik/adk_rag.git
    cd adk_rag
    chmod +x setup.sh
    ./setup.sh
    ```

    Optional flags:
    ```bash
    ./setup.sh --with-docs   # Also install MkDocs Material documentation packages
    ./setup.sh --start       # Run setup and immediately launch Backend (8000) + Frontend (5173)
    ```

=== "Windows (`setup.bat`)"

    ```bat
    git clone https://github.com/Dronanaik/adk_rag.git
    cd adk_rag
    setup.bat
    ```

    Optional flags:
    ```bat
    setup.bat --with-docs    :: Also install MkDocs Material documentation packages
    setup.bat --start        :: Run setup and immediately launch Backend (8000) + Frontend (5173)
    ```

---

## 3. Manual Step-by-Step Setup

### Step 1: Create & Activate Virtual Environment

```bash
cd /path/to/adk_rag
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GOOGLE_API_KEY=your_google_api_key_here
AGENT_MODEL=gemini-2.5-pro
GRAPH_EXTRACTION_MODEL=gemini-2.5-flash

# Neon Console PostgreSQL Connection String
DATABASE_URL=postgresql://neondb_owner:password@ep-xxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require

# JWT Secret for Neon Authentication
JWT_SECRET_KEY=replace-with-a-long-random-secret-string
JWT_EXPIRE_HOURS=168

# Neo4j AuraDB or Local Neo4j Instance
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
NEO4J_DATABASE=neo4j

TOP_K=5
```

> [!TIP]
> **Automatic Database Initialization & UI Settings Page (`v2.3.0`):** You can also enter or update any of these environment variables directly in the browser via the **Settings (`Env & Connections`)** tab—or click **Configure Environment Variables & Connections** on the Sign In screen. Any field left blank automatically falls back to the default value in `.env` or built-in defaults.

---

## How to Get Each Environment Variable

Clicking the **`ⓘ How to get?`** icon next to any variable in the **Settings** tab jumps directly to its corresponding section below.

### 1. `GOOGLE_API_KEY` (Google AI Studio)

`GOOGLE_API_KEY` authenticates the backend with Google's Gemini API for agent reasoning (`gemini-2.5-pro`), knowledge graph extraction (`gemini-2.5-flash`), and vector embeddings (`gemini-embedding-001`).

1. Open **[Google AI Studio — Get API Key](https://aistudio.google.com/app/apikey)** and sign in with your Google account.
2. Click **Create API key** in the top-right corner.
3. Select an existing Google Cloud project or click **Create API key in new project**.
4. Copy the generated key (starts with `AIzaSy...`) and paste it into `GOOGLE_API_KEY` in the **Settings** tab or `.env`.
5. **Fallback behavior**: If left blank in the UI, the platform automatically falls back to the `GOOGLE_API_KEY` defined in `.env`.

---

### 2. `AGENT_MODEL` (ADK Reasoning Model)

`AGENT_MODEL` specifies the Gemini model used by the Google ADK `LlmAgent` (`app/agent.py`) to orchestrate tool calls (`hybrid_search`, `vector_search`, `graph_search`, `get_entity_relationships`) and synthesize cited answers.

- **Recommended / Default Value**: `gemini-2.5-pro`
- **Supported Alternatives**: `gemini-2.5-flash` (faster, lower latency)
- **Fallback behavior**: If left blank, automatically defaults to `gemini-2.5-pro`.

---

### 3. `GRAPH_EXTRACTION_MODEL` (Neo4j Extractor Model)

`GRAPH_EXTRACTION_MODEL` specifies the Gemini model used during **Step 5 (Neo4j Knowledge Graph Extraction)** to extract structured JSON entities and relationships from document chunks.

- **Recommended / Default Value**: `gemini-2.5-flash`
- **Fallback behavior**: If left blank, automatically defaults to `gemini-2.5-flash`.

---

### 4. `EMBEDDING_MODEL` (Vector Embedding Model)

`EMBEDDING_MODEL` specifies the Gemini embedding model used in **Step 3** and during query time to generate `768`-dimensional semantic vectors stored in Neon PostgreSQL (`pgvector`).

- **Recommended / Default Value**: `gemini-embedding-001`
- **Fallback behavior**: If left blank, automatically defaults to `gemini-embedding-001` (`768` dimensions).

---

### 5. `DATABASE_URL` (Neon Console PostgreSQL)

`DATABASE_URL` connects the platform to **Neon Serverless PostgreSQL** for user authentication (`users`), document metadata (`documents`), and `768`-dim `pgvector` + Full-Text Search (`document_chunks`).

1. Go to **[Neon Console](https://console.neon.tech)** and sign up or log in (Free Tier includes `pgvector`).
2. Click **New Project**, choose a project name (e.g., `adk_rag`), select a region close to you, and click **Create project**.
3. On your project **Dashboard**, locate the **Connection Details** card.
4. Ensure **Connection pooling** is enabled and copy the PostgreSQL connection string:
   ```text
   postgresql://neondb_owner:YOUR_PASSWORD@ep-xxx-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```
5. Paste the full URI into `DATABASE_URL` in the **Settings** tab or `.env`.
6. **Automatic Schema Creation**: On connection, `app/database.py` automatically runs `CREATE EXTENSION IF NOT EXISTS vector;` and creates all required tables and HNSW/GIN indexes.
7. **Fallback behavior**: If left blank in the UI, falls back to `DATABASE_URL` in `.env`.

---

### 6. `JWT_SECRET_KEY` & `JWT_EXPIRE_HOURS` (Authentication Security)

- **`JWT_SECRET_KEY`**: Secret string used with `HMAC-SHA256` to sign and verify Bearer session tokens when users sign in.
  - When you run `./setup.sh` or `setup.bat`, a 64-character cryptographic hex secret is generated automatically.
  - You can also generate one manually with:
    ```bash
    python3 -c "import secrets; print(secrets.token_hex(32))"
    ```
  - **Fallback behavior**: If left blank, falls back to the `.env` secret or a deterministic derived key.
- **`JWT_EXPIRE_HOURS`**: Number of hours a signed login session remains valid.
  - **Default Value**: `168` (`7` days).

---

### 7. `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` & `NEO4J_DATABASE` (Neo4j AuraDB)

These variables connect the platform to **Neo4j** for storing and traversing your Knowledge Graph (`(:Document)`, `(:Entity)`, `[:RELATES_TO]`).

1. Open **[Neo4j Aura Console](https://console.neo4j.io)** and sign in.
2. Click **New Instance** → select **AuraDB Free** → click **Create**.
3. **Important**: A modal will appear displaying your **Generated Password**. Click **Download and continue** (which saves a `.txt` credentials file) or copy the password immediately:
   - **`NEO4J_URI`**: Copy the Connection URI from your AuraDB instance card (e.g., `neo4j+s://xxxxxxxx.databases.neo4j.io`). For a local Docker/Desktop Neo4j instance, use `bolt://localhost:7687`.
   - **`NEO4J_USERNAME`**: Default is `neo4j`.
   - **`NEO4J_PASSWORD`**: Paste the generated AuraDB password.
   - **`NEO4J_DATABASE`**: Default is `neo4j`.
4. Wait until your AuraDB instance status turns **Running**, then click **Save & Apply Connections** in the **Settings** tab.
5. **Fallback behavior**: Any field left blank automatically falls back to its default value (`NEO4J_USERNAME=neo4j`, `NEO4J_DATABASE=neo4j`, and `.env` credentials).

---

### 8. `TOP_K` (Hybrid Retrieval Depth)

`TOP_K` controls how many top-scoring document chunks are returned per call to `hybrid_search` and `vector_search`.

- **Recommended / Default Value**: `5` (valid range: `1` to `50`).
- **Fallback behavior**: If left blank, automatically defaults to `5`.

---

### 9. LangSmith Observability & Evaluation

Configure optional **LangSmith** tracing and experiment syncing (`v2.4.0`). Even without a LangSmith API key, the **Evaluation** tab still runs locally using **Gemini 2.5 Flash** as the LLM-as-a-Judge.

- **`LANGSMITH_TRACING`**: Set to `true` to stream live Google ADK agent chains (`/chat`) and retrieval tool spans (`vector_search`, `hybrid_search`, `graph_search`, `get_entity_relationships`) to LangSmith. Defaults to `false`.
- **`LANGSMITH_API_KEY`**: Personal or workspace API key (`lsv2_pt_...`) generated at [smith.langchain.com](https://smith.langchain.com) → **Settings** → **API Keys**.
- **`LANGSMITH_PROJECT`**: Target LangSmith project name for traces and evaluation experiments. Defaults to `adk-agentic-rag`.
- **`LANGSMITH_ENDPOINT`**: LangSmith API endpoint (`https://api.smith.langchain.com` for US, or `https://eu.api.smith.langchain.com` for EU).

---

### Step 4: Start the FastAPI Server

```bash
uvicorn app.api:app --reload
```

Verify the server is running:
- **API Root / Health**: `http://localhost:8000/health`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

---

## 3. Frontend Setup

Open a second terminal window:

```bash
cd /path/to/adk_rag/frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser to access the application.

---

## 4. Building & Serving the MkDocs Documentation

To view this documentation site in your browser with the Material theme and Mermaid diagrams:

```bash
source .venv/bin/activate
pip install mkdocs mkdocs-material
mkdocs serve -a 127.0.0.1:8001
```

Open `http://127.0.0.1:8001` in your browser.
