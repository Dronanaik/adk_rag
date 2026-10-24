import { GraphEntityCard, GraphRelationshipPill } from "../components/ui";
import type { GraphEdgeItem, GraphNodeItem } from "../types/api";

const SEED_NODES: GraphNodeItem[] = [
  {
    id: "22222222-2222-4222-8222-222222222201",
    canonical_name: "OrchestratorAgent",
    entity_type: "Component",
    description:
      "Root ADK agent that decomposes user queries and dispatches specialist sub-agents.",
    aliases: ["Root Orchestrator", "Orchestrator"],
    confidence: 0.98,
    primary_document_id: "00000000-0000-4000-8000-000000000001",
  },
  {
    id: "22222222-2222-4222-8222-222222222202",
    canonical_name: "SynthesisVerifierAgent",
    entity_type: "Component",
    description:
      "Verification agent enforcing inline citation coverage and abstention rules.",
    aliases: ["Synthesis Verifier"],
    confidence: 0.97,
    primary_document_id: "00000000-0000-4000-8000-000000000001",
  },
];

const SEED_EDGES: GraphEdgeItem[] = [
  {
    id: "33333333-3333-4333-8333-333333333301",
    source_node_id: "22222222-2222-4222-8222-222222222201",
    source_name: "OrchestratorAgent",
    target_node_id: "22222222-2222-4222-8222-222222222202",
    target_name: "SynthesisVerifierAgent",
    relation_type: "DEPENDS_ON",
    evidence_quote:
      "The OrchestratorAgent routes retrieved evidence to SynthesisVerifierAgent before emitting a grounded response.",
    confidence: 0.95,
    source_chunk_id: "11111111-1111-4111-8111-111111111101",
  },
];

export function KnowledgeGraphExplorerPage() {
  return (
    <div
      className="flex flex-col gap-4 mx-auto"
      style={{ maxWidth: "1040px", padding: "var(--space-6)" }}
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
          Interactive Knowledge Graph Explorer
        </h1>
        <p
          style={{
            margin: "var(--space-1) 0 0",
            fontSize: "var(--text-sm)",
            color: "var(--text-secondary)",
          }}
        >
          Screen 3 — Bounded 1–3 Hop Subgraph Exploration &amp; Provenance Evidence Quotes
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <section className="flex flex-col gap-3">
          <h2
            style={{
              margin: 0,
              fontSize: "var(--text-base)",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            Canonical Entities ({String(SEED_NODES.length)})
          </h2>
          {SEED_NODES.map((node) => (
            <GraphEntityCard key={node.id} node={node} />
          ))}
        </section>

        <section className="flex flex-col gap-3">
          <h2
            style={{
              margin: 0,
              fontSize: "var(--text-base)",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            Directed Relationships ({String(SEED_EDGES.length)})
          </h2>
          {SEED_EDGES.map((edge) => (
            <GraphRelationshipPill key={edge.id} edge={edge} />
          ))}
        </section>
      </div>
    </div>
  );
}

