import {
  AgentTraceTimeline,
  CitationBadge,
  GroundingStatusBanner,
} from "../components/ui";
import { parseInlineCitations } from "../hooks/useInlineCitations";
import { useSessionContext } from "../hooks/useSessionContext";
import type { AgentTraceStep, CitationItem } from "../types/api";

export const SEED_CITATIONS: CitationItem[] = [
  {
    badge_id: "[Doc:1]",
    modality: "Doc",
    badge_index: 1,
    target_id: "11111111-1111-4111-8111-111111111101",
    title: "Agentic RAG Architecture Reference Guide",
    excerpt:
      "The OrchestratorAgent coordinates specialist sub-agents for hybrid document retrieval, multi-hop knowledge graph traversal, and centralized memory lookup.",
    score: 0.94,
    section_title: "Multi-Agent Orchestration",
    page_number: 1,
  },
  {
    badge_id: "[KG:1]",
    modality: "KG",
    badge_index: 1,
    target_id: "33333333-3333-4333-8333-333333333301",
    title: "OrchestratorAgent → SynthesisVerifierAgent",
    excerpt:
      "The OrchestratorAgent routes retrieved evidence to SynthesisVerifierAgent before emitting a grounded response.",
    score: 0.95,
    hop_depth: 1,
  },
  {
    badge_id: "[Mem:1]",
    modality: "Mem",
    badge_index: 1,
    target_id: "44444444-4444-4444-8444-444444444401",
    title: "system.grounding_policy",
    excerpt:
      "Every synthesized claim must cite at least one verified Document chunk, Knowledge Graph edge, or Memory entry.",
    score: 0.98,
    memory_tier: "SEMANTIC",
  },
];

export const SEED_TRACE_STEPS: AgentTraceStep[] = [
  {
    log_id: "trace-01",
    step_order: 1,
    agent_name: "OrchestratorAgent",
    tool_name: "decompose_intent",
    status: "COMPLETED",
    latency_ms: 140,
    input_summary: "How does the 5-agent hierarchy enforce grounding?",
    output_summary: "Dispatched DocumentRetrieval, KnowledgeGraph, and Memory tools.",
  },
  {
    log_id: "trace-02",
    step_order: 2,
    agent_name: "DocumentRetrievalAgent",
    tool_name: "search_document_chunks",
    status: "COMPLETED",
    latency_ms: 215,
    input_summary: "Hybrid RRF (k=60) query for OrchestratorAgent grounding",
    output_summary: "Retrieved 1 top chunk [Doc:1] (similarity 0.94).",
  },
  {
    log_id: "trace-03",
    step_order: 3,
    agent_name: "KnowledgeGraphAgent",
    tool_name: "traverse_kg_subgraph",
    status: "COMPLETED",
    latency_ms: 180,
    input_summary: "seed=['OrchestratorAgent'], max_hops=2",
    output_summary: "Traversed 1 verified edge [KG:1].",
  },
  {
    log_id: "trace-04",
    step_order: 4,
    agent_name: "MemoryAgent",
    tool_name: "query_centralized_memory",
    status: "COMPLETED",
    latency_ms: 95,
    input_summary: "scope=SEMANTIC, query='grounding policy'",
    output_summary: "Matched verified fact [Mem:1].",
  },
  {
    log_id: "trace-05",
    step_order: 5,
    agent_name: "SynthesisVerifierAgent",
    tool_name: "verify_claim_grounding",
    status: "COMPLETED",
    latency_ms: 310,
    input_summary: "Audit 3 inline claims against retrieved evidence",
    output_summary: "Verdict: GROUNDED (score 0.96).",
  },
];

const SAMPLE_SYNTHESIZED_TEXT =
  "The OrchestratorAgent decomposes incoming research queries and dispatches specialist retrieval tools [Doc:1]. Retrieved evidence is routed along verified dependency edges to the SynthesisVerifierAgent [KG:1], which enforces the system grounding policy before any response or long-term memory write occurs [Mem:1].";

export function ResearchWorkspacePage() {
  const { activeCitationId, openProvenanceForCitation } = useSessionContext();
  const parsedSegments = parseInlineCitations(SAMPLE_SYNTHESIZED_TEXT);

  const handleCitationClick = (badgeId: string) => {
    const match = SEED_CITATIONS.find((item) => item.badge_id === badgeId);
    if (match) {
      openProvenanceForCitation(match);
    }
  };

  return (
    <div
      className="flex flex-col gap-4 mx-auto"
      style={{
        maxWidth: "840px",
        padding: "var(--space-6)",
      }}
    >
      <div>
        <h1
          className="font-display"
          style={{
            margin: 0,
            fontSize: "var(--text-xl)",
            fontWeight: 700,
            color: "var(--text-primary)",
          }}
        >
          Research Workspace
        </h1>
        <p
          style={{
            margin: "var(--space-1) 0 0",
            fontSize: "var(--text-sm)",
            color: "var(--text-secondary)",
          }}
        >
          Screen 1 — Multi-Agent Chat, Inline Tri-Pillar Citations &amp; Live ADK Trace
        </p>
      </div>

      <GroundingStatusBanner
        status="GROUNDED"
        confidenceScore={0.96}
        citationCount={SEED_CITATIONS.length}
      />

      <AgentTraceTimeline steps={SEED_TRACE_STEPS} defaultExpanded />

      <article
        style={{
          padding: "var(--space-5)",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: "var(--text-md)",
            lineHeight: 1.65,
            color: "var(--text-primary)",
          }}
        >
          {parsedSegments.map((seg, idx) =>
            seg.kind === "text" ? (
              <span key={idx}>{seg.text}</span>
            ) : (
              <span key={idx} style={{ margin: "0 2px" }}>
                <CitationBadge
                  modality={seg.modality}
                  index={seg.badgeIndex}
                  isActive={activeCitationId === seg.badgeId}
                  onClick={() => handleCitationClick(seg.badgeId)}
                />
              </span>
            ),
          )}
        </p>
      </article>
    </div>
  );
}

