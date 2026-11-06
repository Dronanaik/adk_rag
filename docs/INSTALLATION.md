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

## 2. Backend Setup

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
> **Automatic Database Initialization:** When you start the FastAPI server, `app/database.py` automatically enables the `pgvector` extension, creates the `users`, `documents`, and `document_chunks` tables and indexes in Neon PostgreSQL, and creates uniqueness constraints in Neo4j. You can also run `sql/schema.sql` manually in the Neon SQL Editor if desired.

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
