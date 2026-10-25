import { createContext, useState, type ReactNode } from "react";
import type { AgentTraceStep, CitationItem } from "../types/api";

export type ProvenanceDrawerTab = "Doc" | "KG" | "Mem" | "Trace";

export const DEFAULT_SEED_CITATIONS: CitationItem[] = [
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

export const DEFAULT_SEED_TRACE_STEPS: AgentTraceStep[] = [
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

export interface SessionContextValue {
  activeSessionId: string;
  activeCitationId: string | null;
  isDrawerOpen: boolean;
  activeDrawerTab: ProvenanceDrawerTab;
  sessionCitations: CitationItem[];
  sessionTraceSteps: AgentTraceStep[];
  setActiveSessionId: (id: string) => void;
  openProvenanceForCitation: (citation: CitationItem) => void;
  setActiveDrawerTab: (tab: ProvenanceDrawerTab) => void;
  setIsDrawerOpen: (open: boolean) => void;
  setSessionCitations: (citations: CitationItem[]) => void;
  setSessionTraceSteps: (steps: AgentTraceStep[]) => void;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [activeSessionId, setActiveSessionId] = useState<string>("session-seed-001");
  const [activeCitationId, setActiveCitationId] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(true);
  const [activeDrawerTab, setActiveDrawerTab] = useState<ProvenanceDrawerTab>("Doc");
  const [sessionCitations, setSessionCitations] =
    useState<CitationItem[]>(DEFAULT_SEED_CITATIONS);
  const [sessionTraceSteps, setSessionTraceSteps] = useState<AgentTraceStep[]>(
    DEFAULT_SEED_TRACE_STEPS,
  );

  const openProvenanceForCitation = (citation: CitationItem) => {
    setActiveCitationId(citation.badge_id);
    setActiveDrawerTab(citation.modality);
    setIsDrawerOpen(true);
  };

  return (
    <SessionContext.Provider
      value={{
        activeSessionId,
        activeCitationId,
        isDrawerOpen,
        activeDrawerTab,
        sessionCitations,
        sessionTraceSteps,
        setActiveSessionId,
        openProvenanceForCitation,
        setActiveDrawerTab,
        setIsDrawerOpen,
        setSessionCitations,
        setSessionTraceSteps,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}
