# Ingestion Pipeline

A complete walkthrough of how documents are processed from upload to searchable vector storage.

---

## Overview

```
File Upload (via API or UI)
         ↓
 ┌───────────────────┐
 │  1. Text Extract  │  parsers.py
 └────────┬──────────┘
          ↓
 ┌───────────────────┐
 │  2. Normalize     │  chunking.py → normalize_text()
 │     & Chunk       │  chunking.py → chunk_text()
 └────────┬──────────┘
          ↓
 ┌───────────────────┐
 │  3. Embed         │  embeddings.py → embed_texts()
 │     (Gemini)      │  gemini-embedding-001, 768 dims
 └────────┬──────────┘
          ↓
 ┌───────────────────┐
 │  4. Store         │  rag_store.py → add_document_chunks()
 │     (Pinecone DB)    │  with user_id, document_id metadata
 └───────────────────┘
```

---

## Step 1 — Text Extraction

**File**: `app/parsers.py`  
**Entry point**: `extract_text(file_path: str) -> str`

The function reads the file extension and dispatches to the correct parser.

### Supported formats

| Extension | Parser | Library | Notes |
|-----------|--------|---------|-------|
| `.pdf` | `extract_from_pdf` | PyMuPDF (`fitz`) | Adds `[Page N]` headers. Text-based PDFs only. |
| `.docx` | `extract_from_docx` | `python-docx` | Extracts non-empty paragraphs. |
| `.xlsx`, `.xls` | `extract_from_xlsx` | `openpyxl` | All sheets; rows as tab-separated values. Adds `[Sheet: name]` headers. |
| `.pptx` | `extract_from_pptx` | `python-pptx` | All slides; text frames in order. Adds `[Slide N]` headers. |
| `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.htm`, `.log` | `extract_from_text` | built-in | UTF-8 with `errors='ignore'` fallback. |

### Unsupported formats

The following formats are **not** supported and will raise `ValueError: Unsupported file type`:

- `.doc` (old Word binary format)
- `.ppt` (old PowerPoint)
- `.rtf`
- Images (`.png`, `.jpg`, `.jpeg`, `.tiff`)
- Scanned PDFs (returns empty text from PyMuPDF)

For scanned documents, use OCR (Tesseract, Google Document AI, or Cloud Vision API) to produce a text file first.

---

## Step 2 — Text Normalization and Chunking

**File**: `app/chunking.py`

### Normalization (`normalize_text`)

Before chunking, the text is cleaned:
- Each line is stripped of leading/trailing whitespace
- Multiple consecutive spaces within a line are collapsed to one
- Empty lines are removed

This prevents chunks from being filled with whitespace padding.

### Chunking (`chunk_text`)

```python
chunk_text(text, chunk_size=1200, overlap=200)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | 1200 | Maximum characters per chunk |
| `overlap` | 200 | Characters shared between consecutive chunks |

**Why overlap?**  
If a sentence or concept spans the boundary of two chunks, overlap ensures that content is not lost — it appears in both the preceding and the following chunk.

**Example** (simplified with chunk_size=20, overlap=5):
```
Input:  "Hello world this is a test sentence for chunking"
Chunk 1: "Hello world this is "
Chunk 2: "is a test sentence f"
Chunk 3: "nce for chunking"
```

---

## Step 3 — Embedding Generation

**File**: `app/embeddings.py`

Each chunk is converted to a 768-dimensional vector using the Gemini embedding model.

```python
response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=chunk_text,
    config=EmbedContentConfig(output_dimensionality=768),
)
embedding = response.embeddings[0].values  # list of 768 floats
```

**Important**: The same model and dimensionality are used for:
1. Indexing document chunks
2. Embedding user queries at search time

Both must match for cosine similarity to work correctly.

> ⚠️ If you change the embedding model or dimensionality, you must re-ingest all documents. Old embeddings in Pinecone DB will be incompatible.

---

## Step 4 — Vector Storage

**File**: `app/rag_store.py`  
**Function**: `add_document_chunks`

Each chunk is stored in Pinecone DB with:

```python
collection.add(
    ids=[chunk_id, ...],          # unique per chunk
    documents=[chunk_text, ...],  # raw text
    embeddings=[embedding, ...],  # 768-dim vector
    metadatas=[{                  # per-chunk metadata
        "user_id": user_id,
        "document_id": document_id,
        "filename": filename,
        "chunk_index": chunk_index,
    }, ...],
)
```

**Chunk ID format**: `{document_id}_{chunk_index}_{8-hex-random}`  
Example: `550e8400-e29b-41d4-a716-446655440000_3_ab12cd34`

---

## Ingestion Result

After a successful upload, the API returns:

```json
{
  "success": true,
  "message": "Document ingested successfully.",
  "result": {
    "document_id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "research.pdf",
    "chunks_created": 12,
    "characters_extracted": 13400
  }
}
```

---

## Checking the Database

```python
from app.database import collection

# Total chunks in the collection
print(collection.count())

# View recent records
records = collection.get(limit=5, include=["documents", "metadatas"])
print(records)
```

---

## Troubleshooting Ingestion

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ValueError: Unsupported file type` | File extension not in parser list | Convert to a supported format or add a custom parser |
| `ValueError: No readable text was found` | Empty or scanned PDF | Use OCR or choose a text-based PDF |
| `chunks_created: 0` | Text was empty after normalization | Verify the file contains readable text |
| Slow ingestion | Many chunks + Gemini API latency | Expected — each chunk requires one API call |
| `openai.APIError` or similar | Wrong API key | Check `GOOGLE_API_KEY` in `.env` |