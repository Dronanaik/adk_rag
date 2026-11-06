# Deployment Guide

This guide explains how to deploy the **ADK Agentic RAG + Knowledge Graph** platform to production using cloud services:
- **Vector & Auth Database**: [Neon Console Serverless PostgreSQL](https://console.neon.tech)
- **Knowledge Graph Database**: [Neo4j AuraDB](https://console.neo4j.io)
- **FastAPI Backend**: [Render](https://render.com) (configured via `render.yaml`)
- **React Frontend**: [Netlify](https://www.netlify.com) (configured via `frontend/netlify.toml`)

---

## 1. Provision Cloud Databases

### 1.1 Neon Console PostgreSQL (`pgvector`)
1. Sign in to [Neon Console](https://console.neon.tech) and create a project.
2. Copy your pooled connection string (`postgresql://user:pass@ep-...pooler...neon.tech/dbname?sslmode=require`).
3. On first startup, the backend automatically executes `CREATE EXTENSION IF NOT EXISTS vector;` and creates the `users`, `documents`, and `document_chunks` tables (or run `sql/schema.sql` directly in the Neon SQL Editor).

### 1.2 Neo4j AuraDB
1. Sign in to [Neo4j Aura Console](https://console.neo4j.io) and create a Free or Professional instance.
2. Copy your connection URI (`neo4j+s://xxxxxxxx.databases.neo4j.io`), username (`neo4j`), and generated password.

---

## 2. Deploy the Backend to Render

1. Push your repository to GitHub.
2. Sign in to [Render](https://render.com) and create a new **Web Service** connected to your repository.
3. Configure the service (or use the included `render.yaml` Blueprint):
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
4. Set the following **Environment Variables** in Render:
   - `GOOGLE_API_KEY`: Your Gemini API key
   - `DATABASE_URL`: Your Neon Console PostgreSQL connection string (including `?sslmode=require`)
   - `JWT_SECRET_KEY`: A strong random secret key for signing JWT tokens
   - `JWT_EXPIRE_HOURS`: `168`
   - `NEO4J_URI`: Your Neo4j AuraDB URI (`neo4j+s://...`)
   - `NEO4J_USERNAME`: `neo4j`
   - `NEO4J_PASSWORD`: Your Neo4j password
   - `NEO4J_DATABASE`: `neo4j`
   - `AGENT_MODEL`: `gemini-2.5-pro`
   - `GRAPH_EXTRACTION_MODEL`: `gemini-2.5-flash`
   - `TOP_K`: `5`
5. Deploy and copy your live Render URL (e.g., `https://adk-rag-backend.onrender.com`).

---

## 3. Deploy the Frontend to Netlify

1. Sign in to [Netlify](https://www.netlify.com) and click **Add new site → Import an existing project**.
2. Select your GitHub repository and configure:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/dist`
3. Under **Environment Variables**, add:
   - `VITE_API_URL`: Your Render backend URL (without a trailing slash)
4. Click **Deploy site**.
