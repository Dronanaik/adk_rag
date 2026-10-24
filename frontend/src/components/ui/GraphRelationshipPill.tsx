import { ArrowRight } from "lucide-react";
import type { GraphEdgeItem } from "../../types/api";

export interface GraphRelationshipPillProps {
  edge: GraphEdgeItem;
}

export function GraphRelationshipPill({ edge }: GraphRelationshipPillProps) {
  return (
    <div
      className="flex flex-col gap-1"
      style={{
        padding: "var(--space-2) var(--space-3)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--bg-surface-subtle)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          style={{
            fontSize: "var(--text-xs)",
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          {edge.source_name}
        </span>
        <span
          className="font-mono-tabular inline-flex items-center gap-1"
          style={{
            fontSize: "var(--text-xs)",
            padding: "1px 6px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--provenance-kg-bg)",
            color: "var(--provenance-kg-fg)",
            border: "1px solid var(--provenance-kg-border)",
          }}
        >
          {edge.relation_type}
          <ArrowRight size={11} />
        </span>
        <span
          style={{
            fontSize: "var(--text-xs)",
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          {edge.target_name}
        </span>
      </div>
      <p
        style={{
          margin: 0,
          fontSize: "var(--text-xs)",
          color: "var(--text-secondary)",
        }}
      >
        “{edge.evidence_quote}”
      </p>
    </div>
  );
}

