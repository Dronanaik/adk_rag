import { Pencil, ShieldCheck, Trash2 } from "lucide-react";
import type { MemoryFactItem } from "../../types/api";

export interface MemoryFactCardProps {
  memory: MemoryFactItem;
  canManage?: boolean;
  onEdit?: (memory: MemoryFactItem) => void;
  onDelete?: (memoryId: string) => void;
}

export function MemoryFactCard({
  memory,
  canManage = false,
  onEdit,
  onDelete,
}: MemoryFactCardProps) {
  return (
    <div
      className="flex flex-col gap-2"
      style={{
        padding: "var(--space-3) var(--space-4)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className="font-mono-tabular"
            style={{
              fontSize: "var(--text-xs)",
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--provenance-mem-bg)",
              color: "var(--provenance-mem-fg)",
              border: "1px solid var(--provenance-mem-border)",
            }}
          >
            {memory.memory_tier}
          </span>
          <span
            className="font-mono-tabular"
            style={{
              fontSize: "var(--text-sm)",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            {memory.key_name}
          </span>
          {memory.is_verified && (
            <span
              className="inline-flex items-center gap-1"
              style={{
                fontSize: "var(--text-xs)",
                color: "var(--status-grounded-fg)",
              }}
            >
              <ShieldCheck size={13} />
              Verified
            </span>
          )}
        </div>

        {canManage && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onEdit?.(memory)}
              aria-label={`Edit memory ${memory.key_name}`}
              className="cursor-pointer inline-flex items-center gap-1"
              style={{
                fontSize: "var(--text-xs)",
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface-subtle)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <Pencil size={12} />
              Edit
            </button>
            <button
              type="button"
              onClick={() => onDelete?.(memory.id)}
              aria-label={`Delete memory ${memory.key_name}`}
              className="cursor-pointer inline-flex items-center gap-1"
              style={{
                fontSize: "var(--text-xs)",
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--status-abstained-bg)",
                color: "var(--status-abstained-fg)",
                border: "1px solid var(--status-abstained-border)",
              }}
            >
              <Trash2 size={12} />
              Delete
            </button>
          </div>
        )}
      </div>

      <p
        style={{
          margin: 0,
          fontSize: "var(--text-sm)",
          color: "var(--text-secondary)",
        }}
      >
        {memory.content}
      </p>

      <div
        className="font-mono-tabular flex items-center justify-between"
        style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
      >
        <span>Confidence: {(memory.confidence * 100).toFixed(0)}%</span>
        <span>Updated: {memory.updated_at}</span>
      </div>
    </div>
  );
}

