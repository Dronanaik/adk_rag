import { Save, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import type { MemoryFactItem } from "../../types/api";

export interface MemoryEditModalProps {
  memory: MemoryFactItem;
  onSave: (memoryId: string, updatedContent: string, updatedConfidence: number) => void;
  onCancel: () => void;
}

export function MemoryEditModal({
  memory,
  onSave,
  onCancel,
}: MemoryEditModalProps) {
  const [content, setContent] = useState<string>(memory.content);
  const [confidence, setConfidence] = useState<number>(memory.confidence);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed) {
      return;
    }
    onSave(memory.id, trimmed, confidence);
  };

  return (
    <div
      role="dialog"
      aria-label="Edit Memory Entry"
      className="flex flex-col gap-3"
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--bg-surface-elevated)",
        border: "1px solid var(--provenance-mem-border)",
        boxShadow: "var(--shadow-md)",
      }}
    >
      <div className="flex items-center justify-between">
        <span
          className="font-mono-tabular"
          style={{
            fontSize: "var(--text-sm)",
            fontWeight: 600,
            color: "var(--provenance-mem-fg)",
          }}
        >
          Editing Memory Fact: {memory.key_name}
        </span>
        <button
          type="button"
          onClick={onCancel}
          aria-label="Cancel memory edit"
          className="cursor-pointer"
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
          }}
        >
          <X size={15} />
        </button>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <textarea
          aria-label="Memory Fact Content"
          rows={3}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          style={{
            padding: "var(--space-2) var(--space-3)",
            fontSize: "var(--text-sm)",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--bg-canvas)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-strong)",
          }}
        />

        <div className="flex items-center justify-between gap-3">
          <label
            className="font-mono-tabular flex items-center gap-2"
            style={{ fontSize: "var(--text-xs)", color: "var(--text-secondary)" }}
          >
            <span>Confidence (0.0 – 1.0):</span>
            <input
              type="number"
              aria-label="Memory Confidence"
              min="0"
              max="1"
              step="0.01"
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
              style={{
                width: "72px",
                padding: "2px 6px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-canvas)",
                color: "var(--text-primary)",
                border: "1px solid var(--border-strong)",
              }}
            />
          </label>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="cursor-pointer"
              style={{
                fontSize: "var(--text-xs)",
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface-subtle)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              aria-label="Save Memory Changes"
              className="inline-flex items-center gap-1 cursor-pointer"
              style={{
                fontSize: "var(--text-xs)",
                fontWeight: 600,
                padding: "4px 12px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--accent-primary)",
                color: "var(--text-on-brand)",
                border: "none",
              }}
            >
              <Save size={12} />
              <span>Save Memory Changes</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

