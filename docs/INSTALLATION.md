# Installation Guide

Step-by-step instructions to set up the ADK RAG system on your local machine.

---

## Prerequisites

| Requirement | Minimum Version | Check |
|-------------|-----------------|-------|
| Python | 3.10 | `python3 --version` |
| pip | Latest | `pip --version` |
| Node.js | 18.x | `node --version` |
| npm | 9.x | `npm --version` |
| Internet | — | Required for Gemini API |
| Google API key | — | [Get one here](https://aistudio.google.com/app/apikey) |

---

## Step 1 — Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd adk_rag
```

---

## Step 2 — Check Your Python Version

```bash
python3 --version
# Expected: Python 3.10.x or higher
```

If your Python version is too old, install a newer version via your OS package manager or [python.org](https://python.org).

---

## Step 3 — Create a Virtual Environment

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` in your terminal prompt when the environment is active.

---

## Step 4 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:

| Package | Purpose |
|---------|---------|
| `google-adk` | Google Agent Development Kit |
| `google-genai` | Gemini API client (embeddings + generation) |
| `chromadb` | Local vector database |
| `fastapi` | REST API framework |
| `uvicorn` | ASGI server |
| `python-multipart` | File upload support |
| `python-dotenv` | `.env` file loading |
| `pymupdf` | PDF text extraction |
| `python-docx` | DOCX text extraction |
| `openpyxl` | Excel (.xlsx/.xls) extraction |
| `python-pptx` | PowerPoint (.pptx) extraction |

---

## Step 5 — Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in your values:

```env
# Required: your Google API key from https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=your_google_api_key_here

# Optional: path to ChromaDB persistent storage
CHROMA_PATH=./data/chroma

# Optional: ChromaDB collection name
COLLECTION_NAME=documents

# Optional: number of chunks returned per search
TOP_K=5
```

> **Never commit your `.env` file to Git.**

---

## Step 6 — Verify the Environment

Check that your API key is loaded:

```bash
python3 -c "from app.config import GOOGLE_API_KEY; print('API key OK:', bool(GOOGLE_API_KEY))"
```

Expected output:

```
API key OK: True
```

---

## Step 7 — Create Required Directories

The directories are created automatically on first run, but you can create them manually:

```bash
mkdir -p data/chroma uploads
```

---

## Step 8 — Start the Backend API

```bash
uvicorn app.api:app --reload
```

The API is available at:

- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

Verify the health check:

```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

---

## Step 9 — Install and Start the React UI

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

The UI is available at: **http://localhost:5173**

---

## Step 10 — First Use

1. Open http://localhost:5173 in your browser
2. Enter your **User ID** (e.g. `drona`) in the welcome screen
3. Click **Upload** tab and drag a document onto the drop zone
4. Wait for ingestion to complete
5. Click **Chat** tab and ask a question

---

## Troubleshooting Installation

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common errors.

| Error | Likely cause |
|-------|-------------|
| `ModuleNotFoundError` | Dependencies not installed or venv not active |
| `KeyError: 'GOOGLE_API_KEY'` | `.env` file missing or API key not set |
| `Connection refused :8000` | Backend server not running |
| `Connection refused :5173` | Frontend dev server not running |
| `npm: command not found` | Node.js not installed |
