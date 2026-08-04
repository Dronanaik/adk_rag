# ADK RAG

> **Document Intelligence Platform** — Upload, ingest, and chat with your documents using Google ADK, Gemini, and ChromaDB.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-latest-4285F4?logo=google&logoColor=white)](https://developers.google.com/adk)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-latest-orange)](https://www.trychroma.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Supported File Types](#supported-file-types)
- [API Endpoints](#api-endpoints)
- [Documentation](#documentation)
- [Production Recommendations](#production-recommendations)

---

## Overview

ADK RAG is a **Retrieval-Augmented Generation** system that lets users upload documents, converts them into searchable vector embeddings, and answers natural language questions using only the user's uploaded content.

Each user has an **isolated document workspace** — one user cannot access another user's documents.

---

## Features

| Feature | Details |
|---------|---------|
| **Document Upload** | PDF, DOCX, XLSX, XLS, PPTX, TXT, MD, CSV, JSON, XML, HTML, LOG |
| **Text Extraction** | Format-specific parsers (PyMuPDF, python-docx, openpyxl, python-pptx) |
| **Chunking** | Overlapping 1200-character chunks, 200-character overlap |
| **Embeddings** | Gemini `gemini-embedding-001`, 768 dimensions |
| **Vector Store** | ChromaDB persistent local collection |
| **AI Agent** | Google ADK `LlmAgent` powered by `gemini-2.5-pro` |
| **Source Citations** | `[Source: filename, chunk N]` in every answer |
| **React UI** | Dark glassmorphism theme, drag-and-drop upload, chat interface |
| **User Isolation** | All ChromaDB queries are filtered by `user_id` |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     React UI                         │
│  (Upload · Documents · Ingestion Pipeline · Chat)    │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP (Vite proxy → localhost:8000)
┌─────────────────▼───────────────────────────────────┐
│              FastAPI Backend                         │
│  POST /documents/upload   GET /documents             │
│  DELETE /documents/{id}   POST /chat                 │
│  GET /ingest/status       GET /health                │
└──────┬──────────────────────────────┬───────────────┘
       │                              │
┌──────▼──────────┐        ┌──────────▼────────────────┐
│  Ingestion       │        │    Google ADK Runner       │
│  Pipeline        │        │    (LlmAgent)              │
│                  │        │    gemini-2.5-pro           │
│  1. Extract text │        └──────────┬────────────────┘
│  2. Chunk        │                   │ search_user_documents tool
│  3. Embed        │        ┌──────────▼────────────────┐
│     (Gemini)     │        │    ChromaDB Query          │
│  4. Store        │        │    (user_id filter)        │
└──────┬──────────┘        └───────────────────────────┘
       │
┌──────▼──────────┐
│   ChromaDB       │
│  (./data/chroma) │
│  collection:     │
│    documents     │
└─────────────────┘
```

### Ingestion pipeline (step by step)

```
File uploaded
    ↓
parsers.py      — extract raw text by file type
    ↓
chunking.py     — normalize whitespace, split into 1200-char overlapping chunks
    ↓
embeddings.py   — Gemini gemini-embedding-001 → 768-dim vectors
    ↓
rag_store.py    — store chunks + embeddings + metadata in ChromaDB
```

---

## Quick Start

### Prerequisites

- Python 3.10 or later
- Node.js 18 or later (for the React UI)
- A [Google API key](https://aistudio.google.com/app/apikey)

### 1 — Clone and enter the project

```bash
git clone <YOUR_REPOSITORY_URL>
cd adk_rag
```

### 2 — Set up the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3 — Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your Google API key
```

```env
GOOGLE_API_KEY=your_google_api_key_here
CHROMA_PATH=./data/chroma
COLLECTION_NAME=documents
TOP_K=5
```

### 4 — Start the backend API

```bash
uvicorn app.api:app --reload
# API available at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### 5 — Start the React UI

```bash
cd frontend
npm install
npm run dev
# UI available at http://localhost:5173
```

### 6 — Open the app

Navigate to **http://localhost:5173**, enter your User ID, and start uploading documents.

---

## Project Structure

```
adk_rag/
├── app/
│   ├── __init__.py
│   ├── agent.py          # Google ADK LlmAgent + search tool
│   ├── api.py            # FastAPI endpoints (upload, chat, delete, status)
│   ├── chunking.py       # Text normalization and overlapping chunker
│   ├── config.py         # Environment variable loading
│   ├── database.py       # ChromaDB persistent client
│   ├── embeddings.py     # Gemini embedding-001 wrapper
│   ├── ingest.py         # Orchestrates extract → chunk → embed → store
│   ├── parsers.py        # Format-specific text extractors
│   ├── rag_store.py      # ChromaDB CRUD operations
│   └── run_agent.py      # Standalone CLI agent runner
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   │   ├── UserIdModal.jsx    # User ID gate
│   │   │   ├── Header.jsx         # App header + sub-header
│   │   │   ├── Tabs.jsx           # Tab navigation
│   │   │   ├── UploadTab.jsx      # Drag-and-drop upload
│   │   │   ├── DocumentsTab.jsx   # Document list + delete
│   │   │   ├── IngestionTab.jsx   # Pipeline status + file types
│   │   │   ├── ChatTab.jsx        # RAG chat interface
│   │   │   └── ChatMessage.jsx    # Message bubble component
│   │   ├── api.js         # API utility functions
│   │   ├── App.jsx        # Root component
│   │   └── index.css      # Design system (dark glassmorphism)
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── data/
│   └── chroma/           # ChromaDB persistent storage
├── docs/
│   ├── ARCHITECTURE.md   # System architecture deep-dive
│   ├── API.md            # All API endpoints with examples
│   ├── CHAT.md           # ADK agent and chat system
│   ├── FRONTEND.md       # React UI guide
│   ├── INGESTION.md      # Ingestion pipeline walkthrough
│   ├── INSTALLATION.md   # Step-by-step installation
│   └── TROUBLESHOOTING.md # Common errors and fixes
├── uploads/              # Temporary file storage (auto-cleaned)
├── .env                  # Your local environment (do not commit)
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Supported File Types

| Extension | Parser | Notes |
|-----------|--------|-------|
| `.pdf` | PyMuPDF | Text-based PDFs only. Scanned PDFs require OCR. |
| `.docx` | python-docx | Full paragraph extraction. |
| `.xlsx` | openpyxl | All sheets extracted row by row. |
| `.xls` | openpyxl | Legacy Excel format. |
| `.pptx` | python-pptx | Slide-by-slide text extraction. |
| `.txt` | Plain reader | UTF-8 with error-ignore fallback. |
| `.md` | Plain reader | Markdown treated as plain text. |
| `.csv` | Plain reader | Raw CSV values. |
| `.json` | Plain reader | Raw JSON text. |
| `.xml` | Plain reader | Raw XML markup. |
| `.html` / `.htm` | Plain reader | HTML tags included. |
| `.log` | Plain reader | Log files as plain text. |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/ingest/status` | Pipeline status + chunk count |
| `POST` | `/documents/upload` | Upload and ingest a document |
| `GET` | `/documents` | List user's documents |
| `DELETE` | `/documents/{id}` | Delete a document and its chunks |
| `POST` | `/chat` | Chat with the ADK agent |

All document endpoints require the `x-user-id` header.

See [docs/API.md](docs/API.md) for full examples.

---

## Documentation

| Document | Description |
|----------|-------------|
| [INSTALLATION.md](docs/INSTALLATION.md) | Step-by-step environment setup |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and data flow |
| [INGESTION.md](docs/INGESTION.md) | Ingestion pipeline walkthrough |
| [API.md](docs/API.md) | All API endpoints with curl examples |
| [CHAT.md](docs/CHAT.md) | ADK agent and session lifecycle |
| [FRONTEND.md](docs/FRONTEND.md) | React UI setup and component guide |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common errors and fixes |

---

## Production Recommendations

For production deployments, consider:

- **Authentication**: Replace `x-user-id` header with Firebase Auth, Google Identity Platform, or JWT
- **Vector storage**: PostgreSQL with pgvector, Vertex AI Vector Search, or AlloyDB
- **Document storage**: Google Cloud Storage for original files
- **Async ingestion**: Cloud Pub/Sub + worker service for large file processing
- **OCR**: Tesseract, Google Document AI, or Cloud Vision API for scanned PDFs
- **Rate limiting**: API Gateway or FastAPI middleware
- **Security**: File size limits, virus scanning, content validation

---

## Author

Created by **Drona**.

## License

MIT License