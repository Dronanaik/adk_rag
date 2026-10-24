-- ============================================================================
-- Seed Script: supabase/seed.sql
-- Product: Agentic RAG System with Centralized Memory and Knowledge Graph
-- Source of Truth: DATABASE.md Section 7.2
-- ============================================================================

INSERT INTO system_settings (
    id,
    top_k_chunks,
    similarity_threshold,
    max_kg_hops,
    max_agent_steps,
    turn_timeout_seconds,
    auto_consolidate_memory,
    strict_abstention_mode
) VALUES (
    1,
    5,
    0.65,
    2,
    5,
    30,
    true,
    true
)
ON CONFLICT (id) DO NOTHING;

