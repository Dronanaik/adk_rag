import { Search } from "lucide-react";
import type { EntityType } from "../../types/api";

export interface GraphFilterToolbarProps {
  searchQuery: string;
  entityTypeFilter: "ALL" | EntityType;
  maxHops: number;
  onSearchChange: (query: string) => void;
  onEntityTypeChange: (typeOpt: "ALL" | EntityType) => void;
  onMaxHopsChange: (hops: number) => void;
}

const ENTITY_TYPE_FILTERS: Array<"ALL" | EntityType> = [
  "ALL",
  "Component",
  "Policy",
  "System",
];

export function GraphFilterToolbar({
  searchQuery,
  entityTypeFilter,
  maxHops,
  onSearchChange,
  onEntityTypeChange,
  onMaxHopsChange,
}: GraphFilterToolbarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div
        className="flex items-center gap-2 flex-1"
        style={{
          padding: "var(--space-2) var(--space-3)",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <Search size={14} style={{ color: "var(--text-muted)" }} />
        <input
          type="text"
          aria-label="Search KG entities"
          placeholder="Search canonical entities by name or description..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="flex-1"
          style={{
            border: "none",
            outline: "none",
            background: "transparent",
            fontSize: "var(--text-sm)",
            color: "var(--text-primary)",
          }}
        />
      </div>

      <div className="flex items-center gap-1">
        {ENTITY_TYPE_FILTERS.map((typeOpt) => (
          <button
            key={typeOpt}
            type="button"
            onClick={() => onEntityTypeChange(typeOpt)}
            className="font-mono-tabular cursor-pointer"
            style={{
              fontSize: "var(--text-xs)",
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              backgroundColor:
                entityTypeFilter === typeOpt
                  ? "var(--accent-primary)"
                  : "var(--bg-surface-subtle)",
              color:
                entityTypeFilter === typeOpt
                  ? "var(--text-on-brand)"
                  : "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {typeOpt}
          </button>
        ))}
      </div>

      <div className="flex items-center gap-1">
        {[1, 2].map((hop) => (
          <button
            key={hop}
            type="button"
            onClick={() => onMaxHopsChange(hop)}
            aria-label={`Set traversal depth to ${String(hop)} hop`}
            className="font-mono-tabular cursor-pointer"
            style={{
              fontSize: "var(--text-xs)",
              padding: "4px 10px",
              borderRadius: "var(--radius-sm)",
              backgroundColor:
                maxHops === hop
                  ? "var(--provenance-kg-fg)"
                  : "var(--bg-surface-subtle)",
              color:
                maxHops === hop
                  ? "var(--text-on-brand)"
                  : "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {String(hop)} {hop === 1 ? "Hop" : "Hops"}
          </button>
        ))}
      </div>
    </div>
  );
}

