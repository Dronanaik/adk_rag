-- =============================================================================
-- ADK RAG + Knowledge Graph — Neon PostgreSQL Schema (pgvector + Hybrid Search)
-- Inspired by coleam00/ottomator-agents/agentic-rag-knowledge-graph
-- =============================================================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1b. Users table for Neon PostgreSQL Authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users (LOWER(email));

-- 2. Documents table (tracks uploaded files & extraction counts per user)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    entity_count INTEGER NOT NULL DEFAULT 0,
    relationship_count INTEGER NOT NULL DEFAULT 0,
    character_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Document chunks table (stores text chunks + 768-dim Gemini embeddings)
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. Indexes for multi-tenant isolation, vector similarity (HNSW), and Full-Text Search
CREATE INDEX IF NOT EXISTS idx_documents_user_id
    ON documents (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_chunks_user_doc
    ON document_chunks (user_id, document_id);

CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts
    ON document_chunks
    USING gin (to_tsvector('english', content));
