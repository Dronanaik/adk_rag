-- ============================================================================
-- Migration: 0001_initial_schema.sql
-- Product: Agentic RAG System with Centralized Memory and Knowledge Graph
-- Source of Truth: DATABASE.md (v1.0.0)
-- ============================================================================

-- 1. Enable Required PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. Trigger Function for Automatic `updated_at` Timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Table 1: system_settings (Singleton Runtime Configuration)
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    top_k_chunks INTEGER NOT NULL DEFAULT 5 CHECK (top_k_chunks BETWEEN 1 AND 20),
    similarity_threshold NUMERIC(3,2) NOT NULL DEFAULT 0.65 CHECK (similarity_threshold BETWEEN 0.00 AND 1.00),
    max_kg_hops INTEGER NOT NULL DEFAULT 2 CHECK (max_kg_hops BETWEEN 1 AND 2),
    max_agent_steps INTEGER NOT NULL DEFAULT 5 CHECK (max_agent_steps BETWEEN 3 AND 8),
    turn_timeout_seconds INTEGER NOT NULL DEFAULT 30 CHECK (turn_timeout_seconds BETWEEN 10 AND 60),
    auto_consolidate_memory BOOLEAN NOT NULL DEFAULT true,
    strict_abstention_mode BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. Table 2: documents
CREATE TABLE IF NOT EXISTS documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL CHECK (char_length(trim(title)) > 0),
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL CHECK (mime_type IN ('application/pdf', 'text/markdown', 'text/plain')),
    content_hash CHAR(64) NOT NULL UNIQUE,
    file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes > 0 AND file_size_bytes <= 26214400),
    status TEXT NOT NULL DEFAULT 'QUEUED' CHECK (status IN ('QUEUED', 'CHUNKING', 'EXTRACTING_KG', 'INDEXED', 'FAILED')),
    error_message TEXT NULL,
    chunk_count INTEGER NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
    entity_count INTEGER NOT NULL DEFAULT 0 CHECK (entity_count >= 0),
    relation_count INTEGER NOT NULL DEFAULT 0 CHECK (relation_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. Table 3: document_chunks
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL CHECK (char_length(trim(content)) > 0),
    embedding vector(768) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

-- 6. Table 4: kg_entities (Schema-Guided Core Entity Types D-03)
CREATE TABLE IF NOT EXISTS kg_entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT NOT NULL,
    lookup_key TEXT NOT NULL UNIQUE,
    entity_type TEXT NOT NULL CHECK (entity_type IN (
        'System', 'Component', 'Organization', 'Person', 'Concept',
        'Process', 'Policy', 'Location', 'Event'
    )),
    aliases TEXT[] NOT NULL DEFAULT '{}',
    description TEXT NOT NULL DEFAULT '',
    embedding vector(768) NOT NULL,
    source_chunk_ids UUID[] NOT NULL DEFAULT '{}' CHECK (cardinality(source_chunk_ids) > 0),
    source_document_ids UUID[] NOT NULL DEFAULT '{}' CHECK (cardinality(source_document_ids) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. Table 5: kg_relationships (Schema-Guided Core Relation Types D-03)
CREATE TABLE IF NOT EXISTS kg_relationships (
    edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id UUID NOT NULL REFERENCES kg_entities(entity_id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES kg_entities(entity_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK (relation_type IN (
        'DEPENDS_ON', 'PART_OF', 'MANAGED_BY', 'AUTHORED_BY', 'CAUSES',
        'MITIGATES', 'COMMUNICATES_WITH', 'GOVERNED_BY', 'LOCATED_IN', 'RELATED_TO'
    )),
    evidence_snippet TEXT NOT NULL CHECK (char_length(evidence_snippet) BETWEEN 1 AND 500),
    confidence NUMERIC(3,2) NOT NULL DEFAULT 0.85 CHECK (confidence BETWEEN 0.00 AND 1.00),
    source_chunk_id UUID NOT NULL REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_entity_id, target_entity_id, relation_type, source_chunk_id)
);

-- 8. Table 6: conversation_sessions
CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL DEFAULT 'New Research Session' CHECK (char_length(trim(title)) > 0),
    use_shared_memory BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9. Table 7: message_turns
CREATE TABLE IF NOT EXISTS message_turns (
    turn_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL CHECK (turn_index >= 0),
    user_query TEXT NOT NULL CHECK (char_length(trim(user_query)) > 0),
    assistant_response TEXT NOT NULL,
    grounding_status TEXT NOT NULL CHECK (grounding_status IN ('GROUNDED', 'PARTIAL', 'INSUFFICIENT_EVIDENCE')),
    citations JSONB NOT NULL DEFAULT '{"chunks": [], "kg_paths": [], "memories": []}'::jsonb,
    total_latency_ms INTEGER NOT NULL DEFAULT 0 CHECK (total_latency_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, turn_index)
);

-- 10. Table 8: memory_entries
CREATE TABLE IF NOT EXISTS memory_entries (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_tier TEXT NOT NULL CHECK (memory_tier IN ('SESSION', 'LONG_TERM_SEMANTIC', 'LONG_TERM_EPISODIC')),
    session_id UUID NULL REFERENCES conversation_sessions(session_id) ON DELETE CASCADE,
    content TEXT NOT NULL CHECK (char_length(trim(content)) > 0),
    embedding vector(768) NOT NULL,
    related_entity_ids UUID[] NOT NULL DEFAULT '{}',
    source_turn_id UUID NULL REFERENCES message_turns(turn_id) ON DELETE SET NULL,
    supporting_chunk_ids UUID[] NOT NULL DEFAULT '{}',
    superseded_by_id UUID NULL REFERENCES memory_entries(memory_id) ON DELETE SET NULL CHECK (superseded_by_id != memory_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 11. Table 9: agent_execution_traces
CREATE TABLE IF NOT EXISTS agent_execution_traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    turn_id UUID NOT NULL REFERENCES message_turns(turn_id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL CHECK (step_order >= 1),
    agent_name TEXT NOT NULL CHECK (agent_name IN ('Orchestrator', 'MemoryAgent', 'VectorRetriever', 'KGRetriever', 'SynthesisVerifier')),
    action_or_tool TEXT NOT NULL,
    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    output_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    latency_ms INTEGER NOT NULL DEFAULT 0 CHECK (latency_ms >= 0),
    status TEXT NOT NULL DEFAULT 'SUCCESS' CHECK (status IN ('SUCCESS', 'FALLBACK', 'ERROR')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (turn_id, step_order)
);

-- 12. Indexes (DATABASE.md Section 4)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_entities_embedding_hnsw
    ON kg_entities USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw
    ON memory_entries USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)
    WHERE superseded_by_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_chunks_doc_order
    ON document_chunks (document_id, chunk_index);

CREATE UNIQUE INDEX IF NOT EXISTS idx_entities_lookup_key
    ON kg_entities (lookup_key);

CREATE INDEX IF NOT EXISTS idx_entities_aliases_gin
    ON kg_entities USING GIN (aliases);

CREATE INDEX IF NOT EXISTS idx_entities_source_docs_gin
    ON kg_entities USING GIN (source_document_ids);

CREATE INDEX IF NOT EXISTS idx_rel_source_entity
    ON kg_relationships (source_entity_id, relation_type);

CREATE INDEX IF NOT EXISTS idx_rel_target_entity
    ON kg_relationships (target_entity_id, relation_type);

CREATE INDEX IF NOT EXISTS idx_rel_source_chunk
    ON kg_relationships (source_chunk_id);

CREATE INDEX IF NOT EXISTS idx_memories_active_tier
    ON memory_entries (memory_tier, session_id, created_at DESC)
    WHERE superseded_by_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_turns_session_order
    ON message_turns (session_id, turn_index ASC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_traces_turn_step
    ON agent_execution_traces (turn_id, step_order ASC);

-- 13. Bounded 1-2 Hop Knowledge Graph Traversal Function (DATABASE.md Section 7.1)
CREATE OR REPLACE FUNCTION traverse_kg_subgraph(
    seed_entity_ids UUID[],
    max_hops INT DEFAULT 2
)
RETURNS TABLE (
    edge_id UUID,
    source_entity_id UUID,
    target_entity_id UUID,
    relation_type TEXT,
    evidence_snippet TEXT,
    confidence NUMERIC(3,2),
    source_chunk_id UUID,
    document_id UUID,
    hop_depth INT
) AS $$
DECLARE
    clamped_hops INT := LEAST(GREATEST(max_hops, 1), 3);
BEGIN
    RETURN QUERY
    WITH RECURSIVE graph_walk AS (
        SELECT
            r.edge_id,
            r.source_entity_id,
            r.target_entity_id,
            r.relation_type,
            r.evidence_snippet,
            r.confidence,
            r.source_chunk_id,
            r.document_id,
            1 AS depth,
            ARRAY[r.source_entity_id, r.target_entity_id] AS visited_nodes
        FROM kg_relationships r
        WHERE r.source_entity_id = ANY(seed_entity_ids)
           OR r.target_entity_id = ANY(seed_entity_ids)

        UNION ALL

        SELECT
            r.edge_id,
            r.source_entity_id,
            r.target_entity_id,
            r.relation_type,
            r.evidence_snippet,
            r.confidence,
            r.source_chunk_id,
            r.document_id,
            gw.depth + 1 AS depth,
            gw.visited_nodes || CASE
                WHEN r.source_entity_id = ANY(gw.visited_nodes) THEN r.target_entity_id
                ELSE r.source_entity_id
            END
        FROM kg_relationships r
        INNER JOIN graph_walk gw
            ON (r.source_entity_id = gw.target_entity_id OR r.target_entity_id = gw.source_entity_id)
        WHERE gw.depth < clamped_hops
          AND NOT (r.source_entity_id = ANY(gw.visited_nodes) AND r.target_entity_id = ANY(gw.visited_nodes))
    )
    SELECT DISTINCT ON (gw.edge_id)
        gw.edge_id,
        gw.source_entity_id,
        gw.target_entity_id,
        gw.relation_type,
        gw.evidence_snippet,
        gw.confidence,
        gw.source_chunk_id,
        gw.document_id,
        gw.depth AS hop_depth
    FROM graph_walk gw
    ORDER BY gw.edge_id, gw.depth ASC
    LIMIT 150;
END;
$$ LANGUAGE plpgsql STABLE;

-- 14. Enable Row-Level Security on All 9 Tables (DATABASE.md Section 5.2)
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE kg_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE kg_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE message_turns ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_execution_traces ENABLE ROW LEVEL SECURITY;

-- 15. Attach `updated_at` Triggers
DROP TRIGGER IF EXISTS trg_system_settings_updated_at ON system_settings;
CREATE TRIGGER trg_system_settings_updated_at
    BEFORE UPDATE ON system_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_documents_updated_at ON documents;
CREATE TRIGGER trg_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_kg_entities_updated_at ON kg_entities;
CREATE TRIGGER trg_kg_entities_updated_at
    BEFORE UPDATE ON kg_entities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_conversation_sessions_updated_at ON conversation_sessions;
CREATE TRIGGER trg_conversation_sessions_updated_at
    BEFORE UPDATE ON conversation_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

