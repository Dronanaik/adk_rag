# :material-file-cog-outline: Technical Specifications

Complete engineering specifications for the **ADK Agentic RAG + Knowledge Graph** platform—covering runtime versions, database DDL and Cypher schemas, cryptographic authentication parameters, hybrid retrieval formulas, structured extraction models, and API contracts.

---

## 1. Technology Stack Matrix

| Layer | Component | Package / Technology | Version / Model | Purpose |
|-------|-----------|----------------------|-----------------|---------|
| **Backend Runtime** | Language | Python | `3.10+` (`3.12` recommended) | Core backend runtime |
| **API Server** | Web Framework | FastAPI + Uvicorn | `fastapi >= 0.110`, `uvicorn[standard]` | Async REST API & OpenAPI documentation |
| **Agent Framework** | Orchestration | Google Agent Development Kit (`google-adk`) | Latest (`LlmAgent`, `Runner`, `InMemorySessionService`) | Multi-tool agent reasoning & session management |
| **Reasoning LLM** | Agent Model | Google Gemini (`google-genai`) | `gemini-2.5-pro` (configurable via `AGENT_MODEL`) | Tool selection, multi-hop synthesis, cited responses |
| **Graph Extraction LLM** | Structured Output Model | Google Gemini (`google-genai`) | `gemini-2.5-flash` (configurable via `GRAPH_EXTRACTION_MODEL`) | Fast JSON schema extraction of entities & relationships |
| **Embeddings** | Embedding Model | Google Gemini (`google-genai`) | `gemini-embedding-001` (`768` dimensions) | Dense semantic vector representation of chunks & queries |
| **Relational + Vector DB** | Primary Database | Neon Console Serverless PostgreSQL | PostgreSQL 15/16 + `pgvector` (`vector` extension) | User auth, document metadata, vector search, full-text search |
| **Postgres Driver** | DB Client | `psycopg2-binary` + `pgvector` | `psycopg2-binary >= 2.9`, `pgvector >= 0.2.5` | Threaded connection pooling & vector type registration |
| **Knowledge Graph DB** | Graph Database | Neo4j AuraDB / Neo4j 5+ | Neo4j `5.x` (`neo4j >= 5.18`) | Entity nodes, relationship triplets, multi-hop Cypher traversal |
| **Authentication** | Password + Token | Python `hashlib` + `hmac` | `PBKDF2-HMAC-SHA256` + `HS256` JWT | Stateless Bearer authentication backed by Neon PostgreSQL |
| **Frontend UI** | Web Client | React + Vite | React `18.3`, Vite `5.x`, `lucide-react` | Bioluminescent Neural Forest UI & interactive SVG Knowledge Graph |

---

## 2. Database Schemas & Indexing

=== ":material-database: Neon PostgreSQL (`pgvector` + FTS)"

    Initialized automatically at startup by `app/database.py` (reference schema in `sql/schema.sql`).

    ```sql title="sql/schema.sql"
    CREATE EXTENSION IF NOT EXISTS vector;

    -- 1. Users table (Neon PostgreSQL Authentication)
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_Users_Email ON users(email);

    -- 2. Documents metadata table (metadata JSONB stores SHA-256 content_hash for v2.1.1 deduplication)
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        chunk_count INTEGER DEFAULT 0,
        entity_count INTEGER DEFAULT 0,
        relationship_count INTEGER DEFAULT 0,
        character_count INTEGER DEFAULT 0,
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_Documents_User ON documents(user_id);

    -- 3. Document chunks table with 768-dim Gemini embeddings
    CREATE TABLE IF NOT EXISTS document_chunks (
        chunk_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding VECTOR(768) NOT NULL,
        metadata JSONB DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- B-Tree tenant & join indexes
    CREATE INDEX IF NOT EXISTS idx_Chunks_User ON document_chunks(user_id);
    CREATE INDEX IF NOT EXISTS idx_Chunks_Document ON document_chunks(document_id);

    -- HNSW index for fast approximate cosine similarity search
    CREATE INDEX IF NOT EXISTS idx_Chunks_Embedding_HNSW
        ON document_chunks USING hnsw (embedding vector_cosine_ops);

    -- GIN index for fast English Full-Text Search (tsvector)
    CREATE INDEX IF NOT EXISTS idx_Chunks_Content_FTS
        ON document_chunks USING gin (to_tsvector('english', content));
    ```

=== ":material-graph: Neo4j Knowledge Graph Schema"

    ```mermaid
    erDiagram
        ENTITY ||--o{ ENTITY : "RELATES_TO (relation_type, fact, document_id, user_id)"
        ENTITY }o--o{ DOCUMENT : "MENTIONED_IN (user_id)"

        ENTITY {
            string id PK "user_id::LOWER(name)"
            string name "Canonical Entity Name"
            string category "Technology | Model | Concept | Organization | Person | Metric | Location | Event"
            string description "Contextual summary of the entity"
            string user_id "Tenant owner ID"
            datetime updated_at "Last updated timestamp"
        }

        DOCUMENT {
            string id PK "user_id::document_id"
            string document_id "UUID matching PostgreSQL documents.document_id"
            string filename "Source document filename"
            string user_id "Tenant owner ID"
            datetime updated_at "Ingestion timestamp"
        }
    ```

    ```cypher title="Neo4j Constraints & Indexes (app/database.py)"
    CREATE CONSTRAINT entity_unique_id IF NOT EXISTS
    FOR (e:Entity) REQUIRE e.id IS UNIQUE;

    CREATE INDEX entity_user_idx IF NOT EXISTS
    FOR (e:Entity) ON (e.user_id);

    CREATE INDEX entity_name_idx IF NOT EXISTS
    FOR (e:Entity) ON (e.name);

    CREATE CONSTRAINT doc_unique_id IF NOT EXISTS
    FOR (d:Document) REQUIRE d.id IS UNIQUE;
    ```

---

## 3. Authentication & Cryptographic Security (`app/auth.py`)

<div class="grid cards" markdown>

-   :material-key-chain:{ .lg .middle } **Password Hashing (`PBKDF2-HMAC-SHA256`)**

    ---

    - **Work Factor**: `260,000` iterations (OWASP standard)
    - **Salt**: `16` cryptographic random bytes (`32` hex chars) per user via `secrets.token_hex(16)`
    - **Verification**: Constant-time digest comparison via `hmac.compare_digest()`

-   :material-certificate-outline:{ .lg .middle } **Stateless Bearer Token (`HS256` JWT)**

    ---

    - **Algorithm**: `HMAC-SHA256` signed with `JWT_SECRET_KEY`
    - **Default TTL**: `168` hours (`7` days, configurable via `JWT_EXPIRE_HOURS`)
    - **Claims**: `sub` (`user_id`), `email`, `name`, `iat`, `exp`

</div>

---

## 4. Chunking, Embedding & Hybrid Retrieval Math

### 4.1 Structure-Aware Semantic Chunker (`app/chunking.py`)
- **Chunk Size**: `1,200` characters
- **Sliding Overlap**: `200` characters
- **Splitting Priority**: Markdown headings (`#`, `##`, `###`) → double-newline paragraphs (`\n\n`) → sentence boundaries (`(?<=[.!?])\s+`) → hard character slice fallback.

### 4.2 Batched Vector Embeddings (`app/embeddings.py`)
- **Model**: `gemini-embedding-001`
- **Output Dimensionality**: `768` floats
- **Batch Size**: Up to `50` chunks per API request

### 4.3 Hybrid Search Scoring Formula (`app/rag_store.py`)

For a user query $q$ with embedding $\mathbf{e}_q \in \mathbb{R}^{768}$ and a candidate chunk $c$ with embedding $\mathbf{e}_c \in \mathbb{R}^{768}$:

1. **Cosine Vector Similarity** (`pgvector` `<=>` cosine distance operator):
   $$\text{vector\_similarity}(c, q) = 1 - \left( \mathbf{e}_c \iff \mathbf{e}_q \right)$$

2. **Full-Text Cover-Density Rank** (PostgreSQL `ts_rank_cd`):
   $$\text{keyword\_score}(c, q) = \text{ts\_rank\_cd}\left(\text{to\_tsvector}(\text{'english'}, c.\text{content}),\ \text{plainto\_tsquery}(\text{'english'}, q)\right)$$

3. **Weighted Hybrid Score** (`70%` semantic + `30%` lexical):
   $$\text{combined\_score}(c, q) = 0.7 \times \text{vector\_similarity}(c, q) + 0.3 \times \text{keyword\_score}(c, q)$$

---

## 5. Gemini Structured Output Schema (`app/graph_store.py`)

During Step 5 of ingestion, chunks are grouped in batches of `4` (up to `25` chunks per document) and passed to `gemini-2.5-flash` with `response_mime_type="application/json"` and `temperature=0.1`:

```python title="app/graph_store.py"
class ExtractedEntity(BaseModel):
    name: str          # Canonical entity name (e.g., "Google ADK", "PostgreSQL")
    category: str      # Person | Organization | Technology | Concept | Location | Event | Process | Metric | Model
    description: str   # Concise 1-sentence summary in context

class ExtractedRelationship(BaseModel):
    source: str        # Exact name of source entity
    target: str        # Exact name of target entity
    relation_type: str # UPPER_SNAKE_CASE verb (e.g., "USES", "DEPENDS_ON", "BUILT_BY")
    fact: str          # Concise factual sentence explaining how source relates to target

class ChunkGraphExtraction(BaseModel):
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]
```

---

## 6. Environment Configuration Reference (`.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | **Yes** | — | Google Gemini API key from Google AI Studio |
| `DATABASE_URL` | **Yes** | — | Neon Console PostgreSQL connection URI (`postgresql://...?sslmode=require`) |
| `NEO4J_URI` | **Yes** | `bolt://localhost:7687` | Neo4j AuraDB (`neo4j+s://...`) or local Bolt URI |
| `NEO4J_USERNAME` | **Yes** | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | **Yes** | — | Neo4j password |
| `NEO4J_DATABASE` | No | `neo4j` | Target Neo4j database name |
| `JWT_SECRET_KEY` | No | Auto-default | Secret key for signing `HS256` JWT tokens |
| `JWT_EXPIRE_HOURS` | No | `168` | JWT token validity period in hours |
| `AGENT_MODEL` | No | `gemini-2.5-pro` | Gemini model used by the Google ADK reasoning agent |
| `GRAPH_EXTRACTION_MODEL` | No | `gemini-2.5-flash` | Gemini model used for structured entity/relationship extraction |
| `TOP_K` | No | `5` | Default number of chunks returned by vector and hybrid search |
