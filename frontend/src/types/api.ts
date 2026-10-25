/**
 * Canonical TypeScript interfaces matching API.md and DATABASE.md contracts.
 * Zero `any` escape hatches permitted per AGENTS.md Section 6.2.
 */

export type AppRole = "researcher" | "admin";

export type DocumentStatus =
  | "QUEUED"
  | "PARSING"
  | "CHUNKING"
  | "EMBEDDING"
  | "EXTRACTING_KG"
  | "INDEXED"
  | "FAILED";

export type GroundingStatus =
  | "GROUNDED"
  | "PARTIAL"
  | "ABSTAINED"
  | "INSUFFICIENT_EVIDENCE";

export type ProvenanceModality = "Doc" | "KG" | "Mem";

export type AgentName =
  | "OrchestratorAgent"
  | "DocumentRetrievalAgent"
  | "KnowledgeGraphAgent"
  | "MemoryAgent"
  | "SynthesisVerifierAgent";

export type EntityType =
  | "System"
  | "Component"
  | "Organization"
  | "Person"
  | "Concept"
  | "Process"
  | "Policy"
  | "Location"
  | "Event"
  | "Technology"
  | "Metric"
  | "DocumentTopic";

export type RelationType =
  | "DEPENDS_ON"
  | "PART_OF"
  | "MANAGED_BY"
  | "AUTHORED_BY"
  | "CAUSES"
  | "MITIGATES"
  | "COMMUNICATES_WITH"
  | "GOVERNED_BY"
  | "LOCATED_IN"
  | "RELATED_TO"
  | "USES"
  | "DEFINES"
  | "AFFECTS"
  | "PRECEDES";

export type MemoryTier =
  | "SHORT_TERM"
  | "EPISODIC"
  | "SEMANTIC"
  | "LONG_TERM_EPISODIC"
  | "LONG_TERM_SEMANTIC";

export interface ApiErrorDetail {
  code: string;
  message: string;
  details: Record<string, string | number | boolean | string[] | null>;
  request_id: string;
}

export interface ApiErrorEnvelope {
  error: ApiErrorDetail;
}

export interface PaginationMeta {
  next_cursor: string | null;
  has_more: boolean;
  limit: number;
}

export interface HealthData {
  status: string;
  version: string;
  dependencies: {
    database_pgvector: string;
    gemini_api: string;
  };
  models: {
    fast_model: string;
    reasoning_model: string;
    embedding_model: string;
    embedding_dimension: number;
  };
}

export interface HealthResponse {
  data: HealthData;
  request_id: string;
}

export interface CitationItem {
  badge_id: string;
  modality: ProvenanceModality;
  badge_index: number;
  target_id: string;
  title: string;
  excerpt: string;
  score: number;
  section_title?: string | null;
  page_number?: number | null;
  hop_depth?: number | null;
  memory_tier?: MemoryTier | null;
}

export interface AgentTraceStep {
  log_id: string;
  step_order: number;
  agent_name: AgentName;
  tool_name: string | null;
  status: "RUNNING" | "COMPLETED" | "FAILED" | "SKIPPED";
  latency_ms: number | null;
  input_summary: string;
  output_summary: string;
}

export interface SessionSummary {
  id: string;
  title: string;
  turn_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatTurnMessage {
  turn_id: string;
  session_id: string;
  user_query: string;
  assistant_response: string;
  grounding_status: GroundingStatus;
  grounding_score: number;
  citations: CitationItem[];
  trace_steps: AgentTraceStep[];
  abstention_reason: string | null;
  created_at: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  status: DocumentStatus;
  chunk_count: number;
  entity_count: number;
  edge_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface GraphNodeItem {
  id: string;
  canonical_name: string;
  entity_type: EntityType;
  description: string | null;
  aliases: string[];
  confidence: number;
  primary_document_id: string | null;
}

export interface GraphEdgeItem {
  id: string;
  source_node_id: string;
  source_name: string;
  target_node_id: string;
  target_name: string;
  relation_type: RelationType;
  evidence_quote: string;
  confidence: number;
  source_chunk_id: string | null;
}

export interface SubgraphSupportingChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  section_title: string | null;
  content_snippet: string;
}

export interface SubgraphResponseData {
  center_node: GraphNodeItem;
  nodes: GraphNodeItem[];
  edges: GraphEdgeItem[];
  supporting_chunks: SubgraphSupportingChunk[];
}

export interface MemoryFactItem {
  id: string;
  memory_tier: MemoryTier;
  key_name: string;
  content: string;
  confidence: number;
  is_verified: boolean;
  is_edited_by_user: boolean;
  source_chunk_id: string | null;
  source_node_id: string | null;
  updated_at: string;
}

export interface MemoryUpdatePayload {
  content?: string;
  confidence?: number;
  is_verified?: boolean;
}

export type TurnSseEvent =
  | {
      event: "turn.started";
      data: { turn_id: string; session_id: string; request_id: string };
    }
  | {
      event: "agent.step.started" | "agent.step.completed" | "agent_step";
      data: AgentTraceStep;
    }
  | {
      event: "response.delta" | "token";
      data: { text_delta?: string; delta?: string };
    }
  | {
      event: "response.citations";
      data: { citations: CitationItem[] };
    }
  | {
      event: "turn.completed" | "turn_complete";
      data: {
        turn_id: string;
        grounding_status: GroundingStatus;
        grounding_score: number;
        total_latency_ms: number;
        citations?: CitationItem[];
        trace_steps?: AgentTraceStep[];
        abstention_reason?: string | null;
      };
    }
  | {
      event: "turn.error" | "error";
      data: ApiErrorDetail;
    };
