# Troubleshooting Guide

Solutions for common errors in the ADK RAG system.

---

## Backend Issues

### `KeyError: 'GOOGLE_API_KEY'`

**Cause**: The `.env` file is missing or the key is not set.

**Fix**:
```bash
# Check if .env exists
ls -la .env

# Check if the key is set
cat .env | grep GOOGLE_API_KEY

# Create from example if missing
cp .env.example .env
# Then edit .env and add your key
```

---

### `ModuleNotFoundError: No module named 'app'`

**Cause**: Running the server from the wrong directory, or the virtual environment is not active.

**Fix**:
```bash
# Always run from the project root (adk_rag/)
cd /path/to/adk_rag

# Activate the virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Then start the server
uvicorn app.api:app --reload
```

---

### `curl: (7) Failed to connect to localhost port 8000`

**Cause**: The FastAPI server is not running.

**Fix**:
```bash
cd /path/to/adk_rag
source .venv/bin/activate
uvicorn app.api:app --reload
```

---

### `ValueError: Unsupported file type: '.doc'`

**Cause**: Trying to upload a legacy `.doc` file. Only `.docx` is supported.

**Fix**: Convert `.doc` to `.docx` using Microsoft Word or LibreOffice, then upload the converted file.

---

### `ValueError: No readable text was found in the document.`

**Cause**: The PDF is scanned (image-based) or the file is otherwise empty.

**Fix**:
- For scanned PDFs: use OCR software (Tesseract, Adobe Acrobat, Google Document AI) to produce a searchable PDF or a text file
- For image PDFs: extract text with Cloud Vision API and save as `.txt`
- For empty files: verify the file contains actual content

---

### `HTTP 400: Unsupported file type`

**Cause**: The uploaded file extension is not in the supported list.

**Fix**: Check [docs/INGESTION.md](INGESTION.md) for supported file types. Convert your file to a supported format (e.g., save an Excel file as `.xlsx` rather than `.ods`).

---

### `HTTP 500: Document ingestion failed`

**Cause**: An unexpected error during ingestion (embedding API failure, Pinecone DB error).

**Check the server logs** for the full traceback:
```
INFO:     POST /documents/upload - 500
...
Exception: ...
```

Common sub-causes:
- Gemini API quota exceeded → wait or upgrade your quota
- Pinecone DB connection error → check your PINECONE_API_KEY
- Network error to Gemini API → check your internet connection

---

### Gemini API authentication error

**Cause**: Invalid or expired API key.

**Fix**:
```bash
# Test the key directly
python3 -c "
from google import genai
from app.config import GOOGLE_API_KEY
client = genai.Client(api_key=GOOGLE_API_KEY)
r = client.models.embed_content(model='gemini-embedding-001', contents='test')
print('OK', len(r.embeddings[0].values))
"
```

If this fails, get a new key from https://aistudio.google.com/app/apikey and update `.env`.

---

### Pinecone Dimension Mismatch

**Cause**: Existing Pinecone index was created with a different embedding dimensionality.

**Fix**: Delete the existing index in the Pinecone console and create a new one with the correct dimension (768), then re-ingest.

> This permanently deletes all stored embeddings. You must re-ingest all documents.

---

### Index stats show 0 vectors after upload

**Cause**: Upload appeared to succeed but chunks were not stored.

**Debug**:
```python
python3 -c "
from app.database import index
stats = index.describe_index_stats()
print('Count:', stats.total_vector_count)
"
```

Check:
- The upload returned `chunks_created > 0`
- The `PINECONE_INDEX_NAME` and `PINECONE_API_KEY` in `.env` match your Pinecone project
- No exceptions occurred during `add_document_chunks`

---

## Frontend Issues

### `npm: command not found`

**Cause**: Node.js is not installed.

**Fix**: Install Node.js from https://nodejs.org (LTS version recommended).

---

### Frontend loads but shows "API Offline"

**Cause**: The backend is not running or is on a different port.

**Fix**:
1. Start the backend: `uvicorn app.api:app --reload`
2. Verify it's on port 8000: `curl http://localhost:8000/health`
3. Check `frontend/vite.config.js` — the proxy target should be `http://localhost:8000`

---

### `CORS error` in browser console

**Cause**: The frontend is accessing the backend directly (not through the Vite proxy), or the backend CORS config doesn't include the frontend origin.

**Fix**:
- Use the Vite dev server (`npm run dev`) — it proxies `/api/*` automatically
- If you've changed ports, update `vite.config.js` proxy target

---

### Chat returns "Agent error: ..."

**Cause**: The ADK agent or Gemini API encountered an error.

**Check**:
- The backend terminal for the full error traceback
- Your Gemini API quota and billing status
- That `GOOGLE_API_KEY` is correctly set

---

### Documents list is empty after upload

**Cause**: The `x-user-id` used for upload and for listing may be different.

**Fix**: In the React UI, the User ID entered at the start is used for all operations. Ensure you're logged in as the same user who uploaded the documents. Different users have separate document collections.

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Running `uvicorn` without activating the venv | Always activate `.venv` first |
| Changing `GOOGLE_API_KEY` after Pinecone DB is populated | The key change only affects new embeddings; existing ones are unaffected |
| Uploading the same file twice | Each upload creates a new `document_id` — duplicate chunks will exist. Delete the old document first. |
| Using `user_123` in the API but a different ID in the UI | User IDs must match exactly — they are case-sensitive |
| Restarting the backend during a chat | The ADK session is lost. Start a new chat session. |
| Very large files (50+ MB) | Ingestion will be slow due to per-chunk Gemini API calls. Consider splitting large files. |
