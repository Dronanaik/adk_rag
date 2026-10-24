import type { GraphNodeItem } from "../../types/api";

export interface GraphEntityCardProps {
  node: GraphNodeItem;
  isSelected?: boolean;
  onSelect?: (node: GraphNodeItem) => void;
}

export function GraphEntityCard({
  node,
  isSelected = false,
  onSelect,
}: GraphEntityCardProps) {
  return (
    <div
      onClick={() => onSelect?.(node)}
      className="flex flex-col gap-2 cursor-pointer"
      style={{
        padding: "var(--space-3)",
        borderRadius: "var(--radius-md)",
        backgroundColor: isSelected
          ? "var(--provenance-kg-bg)"
          : "var(--bg-surface)",
        borderWidth: "1px",
        borderStyle: "solid",
        borderColor: isSelected
          ? "var(--provenance-kg-border)"
          : "var(--border-subtle)",
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span
          style={{
            fontSize: "var(--text-sm)",
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          {node.canonical_name}
        </span>
        <span
          className="font-mono-tabular"
          style={{
            fontSize: "var(--text-xs)",
            padding: "1px 6px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--provenance-kg-bg)",
            color: "var(--provenance-kg-fg)",
            border: "1px solid var(--provenance-kg-border)",
          }}
        >
          {node.entity_type}
        </span>
      </div>
      {node.description && (
        <p
          style={{
            margin: 0,
            fontSize: "var(--text-xs)",
            color: "var(--text-secondary)",
          }}
        >
          {node.description}
        </p>
      )}
      <div
        className="font-mono-tabular flex items-center justify-between"
        style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
      >
        <span>Aliases: {node.aliases.length > 0 ? node.aliases.join(", ") : "none"}</span>
        <span>Conf: {(node.confidence * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}

