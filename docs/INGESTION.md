# Ingestion Pipeline

The 5-step dual ingestion pipeline converts raw uploaded files into both **searchable `768`-dimensional vector chunks in Neon PostgreSQL (`pgvector`)** and **structured entities and relationships in the Neo4j Knowledge Graph**, while streaming real-time step progress to the UI.

---

## 5-Step Dual Ingestion Overview

```mermaid
flowchart TD
    Upload["Uploaded File (app/api.py -> /tmp/adk_rag_uploads)"] --> Step1["Step 1: Format-Specific Text Extraction (app/parsers.py)"]
    Step1 --> Step2["Step 2: Structure-Aware Semantic Chunking (app/chunking.py — 1200 chars, 200 overlap)"]
    Step2 --> Dedup{"SHA-256 Content-Hash & Filename Check (app/rag_store.py)"}
    Dedup -->|"Same Filename + Same Hash (unchanged)"| FastSkip["Skip Redundant Indexing & Return Existing Metrics"]
    Dedup -->|"Different Filename + Same Hash (duplicate_content)"| FastSkip
    Dedup -->|"Same Filename + Modified Hash (updated)"| PurgeOld["Atomically Purge Previous Chunks (Postgres) & Triples (Neo4j)"]
    PurgeOld --> Step3["Step 3: Batched Gemini Embeddings (app/embeddings.py — gemini-embedding-001, 768-dim)"]
    Dedup -->|"New Document (created)"| Step3
    Step3 --> Step4["Step 4: Neon PostgreSQL Indexing (app/rag_store.py — pgvector HNSW + FTS GIN)"]
    Step4 --> Step5["Step 5: Neo4j Knowledge Graph Extraction (app/graph_store.py — gemini-2.5-flash Structured JSON)"]
```

---

## Redundant & Updated File Upload Handling (`v2.1.1`)

After Step 2, `ingest_document` computes a normalized **SHA-256 content fingerprint** (`hashlib.sha256(re.sub(r"\s+", " ", text.strip()).encode("utf-8")).hexdigest()`) and calls `find_existing_user_document(...)` in `app/rag_store.py` to handle all three redundant/updated upload scenarios automatically:

| Scenario | Condition | `ingest_action` | Pipeline Behavior | UI Badge |
|----------|-----------|-----------------|-------------------|----------|
| **1. Exact Same File Re-Uploaded** | `same filename` + `same content_hash` | `"unchanged"` | Skips redundant Gemini embedding & Neo4j extraction calls, fast-completes Step 5, and returns existing document counts. | `Skipped (Already Indexed)` |
| **2. Same Content, Different Filename** | `different filename` + `same content_hash` | `"duplicate_content"` | Prevents duplicate vector chunks and duplicate graph triples from polluting retrieval; references `duplicate_of`. | `Skipped (Duplicate of <filename>)` |
| **3. Updated Version of Existing File** | `same filename` + `different content_hash` | `"updated"` | Atomically deletes the previous version from Neon PostgreSQL (`delete_document_chunks`) and Neo4j (`delete_document_from_graph`), then indexes the new version through Steps 3–5. | `Updated Version` |
| **4. Brand-New Document** | No filename or content hash match | `"created"` | Runs the full 5-step dual ingestion pipeline and stores `content_hash` in `documents.metadata`. | `Indexed (New)` |

---

## Step 1: Format-Specific Text Extraction (`app/parsers.py`)

`parse_file(file_path)` inspects the lowercase file extension and routes the file to the appropriate parser:

| Extension | Library | Extraction Details |
|-----------|---------|--------------------|
| `.pdf` | `pymupdf` (`import pymupdf as fitz`) | Opens each page in sequence and extracts text blocks via `page.get_text("text")`. |
| `.docx` | `python-docx` | Extracts all non-empty paragraphs followed by all table rows formatted as `cell1 \| cell2`. |
| `.xlsx` | `openpyxl` | Loads workbook with `data_only=True` (evaluated formula values) and formats each sheet under `[Sheet: Name]`. |
| `.xls` | `xlrd` | Iterates legacy Excel sheets and formats non-empty rows. |
| `.pptx` | `python-pptx` | Extracts text frames and tables slide-by-slide under `[Slide N]`. |
| `.txt`, `.md`, `.log` | Built-in `open()` | Reads UTF-8 text directly. |
| `.csv` | `csv` | Joins each CSV row with `, `. |
| `.json` | `json` | Parses JSON and pretty-prints with `indent=2`. |
| `.xml`, `.html`, `.htm` | `xml.etree.ElementTree` / regex | Strips tags and normalizes whitespace into clean text. |

---

## Step 2: Structure-Aware Semantic Chunking (`app/chunking.py`)

Instead of slicing text at arbitrary character offsets (which breaks sentences and tables mid-thought), `chunk_text(text, chunk_size=1200, overlap=200)` preserves document structure:

1. **Line Normalization**: Converts `\r\n` to `\n` and collapses 3+ consecutive newlines into `\n\n`.
2. **Paragraph & Header Segmentation**: Splits along paragraph breaks (`\n\n`) and Markdown headings (`#`, `##`, `###`).
3. **Greedy Paragraph Packing**: Accumulates complete paragraphs into the current chunk as long as total length remains $\le 1200$ characters.
4. **Sentence-Boundary Fallback**: If a single paragraph exceeds `1200` characters, splits along sentence boundaries (`(?<=[.!?])\s+`).
5. **Contextual Overlap**: Carries the trailing `200` characters of chunk $i$ into the start of chunk $i+1$ so concepts spanning chunk boundaries remain intact.

---

## Step 3: Batched Gemini Embedding Generation (`app/embeddings.py`)

`get_embeddings_batch(texts, batch_size=50)` generates `768`-dimensional vectors for all chunks using `gemini-embedding-001`:

```python
response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=batch,
    config=types.EmbedContentConfig(output_dimensionality=768),
)
```

Batching up to `50` chunks per API request significantly reduces ingestion latency compared to sequential per-chunk calls.

---

## Step 4: Neon PostgreSQL Vector + Full-Text Indexing (`app/rag_store.py`)

`add_document_chunks(...)` inserts the document metadata into `documents` and bulk-inserts all chunks into `document_chunks` using `psycopg2.extras.execute_values`:

- **Vector Index (`pgvector` HNSW)**: Indexes `embedding vector_cosine_ops` for fast cosine similarity search.
- **Full-Text Index (PostgreSQL GIN)**: Indexes `to_tsvector('english', content)` for keyword and phrase matching.

---

## Step 5: Neo4j Knowledge Graph Extraction (`app/graph_store.py`)

`add_document_to_graph(...)` extracts domain entities and factual relationships from the chunks and merges them into Neo4j:

1. **Structured LLM Extraction**:
   - Sends batches of `4` chunks to `gemini-2.5-flash` configured with `response_mime_type="application/json"` and `response_schema=ChunkGraphExtraction`.
   - Extracts canonical `ExtractedEntity` nodes (`name`, `category`, `description`) and `ExtractedRelationship` edges (`source`, `target`, `relation_type`, `fact`).
2. **Neo4j Cypher Persistence**:
   - Creates/merges the `(:Document {id: user_id::document_id})` node.
   - Merges each `(:Entity {id: user_id::lower(name)})` node and links `(e)-[:MENTIONED_IN]->(d)`.
   - Merges directed `(source:Entity)-[:RELATES_TO {relation_type, document_id, user_id}]->(target:Entity)` edges storing the supporting `fact`.
3. **Metadata Sync**:
   - Updates `documents.entities_count` and `documents.relationships_count` in Neon PostgreSQL so the **Documents** tab displays accurate counts for every file.

---

## Live Per-User & Multi-Document Progress Tracking (`app/ingest.py`)

When a user selects multiple files in `UploadTab.jsx`, `App.jsx` orchestrates sequential batch ingestion (`doc_index = 1..N`, `total_docs = N`) so each document runs through Steps 1–5 (`0%` → `100%`) cleanly.

During ingestion, `ingest_document(file_path, filename, user_id, doc_index, total_docs)` updates `_ingestion_progress[user_id]` before and after each of the 5 stages. The frontend polls `GET /ingest/progress` every `450ms` while an upload is active, receiving:

```json
{
  "state": "running",
  "filename": "ADK_Architecture_Brief.md",
  "doc_index": 2,
  "total_docs": 2,
  "current_step": 5,
  "step_name": "Neo4j Knowledge Graph Extraction",
  "message": "Extracting domain entities & relationships with Gemini into Neo4j…",
  "step_outputs": {
    "1": "Extracted 1,142 characters from ADK_Architecture_Brief.md",
    "2": "Created 2 overlapping semantic chunks",
    "3": "Generated 2 × 768-dim embedding vectors",
    "4": "Indexed 2 chunks in Neon pgvector + FTS"
  }
}
```
