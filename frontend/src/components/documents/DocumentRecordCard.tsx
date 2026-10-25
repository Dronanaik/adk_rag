import { RefreshCw, Trash2 } from "lucide-react";
import type { DocumentSummary } from "../../types/api";
import { IngestionStatusStepper } from "../ui";

export interface DocumentRecordCardProps {
  doc: DocumentSummary;
  isAdmin: boolean;
  onRetry: (docId: string) => void;
  onDelete: (docId: string) => void;
}

export function DocumentRecordCard({
  doc,
  isAdmin,
  onRetry,
  onDelete,
}: DocumentRecordCardProps) {
  return (
    <div
      className="flex flex-col gap-3"
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2
            style={{
              margin: 0,
              fontSize: "var(--text-base)",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            {doc.title}
          </h2>
          <span
            className="font-mono-tabular"
            style={{
              fontSize: "var(--text-xs)",
              color: "var(--text-muted)",
            }}
          >
            {doc.file_name} · {String(doc.chunk_count)} chunks ·{" "}
            {String(doc.entity_count)} KG entities
          </span>
        </div>

        {isAdmin && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onRetry(doc.id)}
              aria-label={`Retry ingestion for ${doc.title}`}
              className="inline-flex items-center gap-1 cursor-pointer"
              style={{
                fontSize: "var(--text-xs)",
                padding: "4px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--bg-surface-subtle)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <RefreshCw size={12} />
              <span>Retry Ingestion</span>
            </button>
            <button
              type="button"
              onClick={() => onDelete(doc.id)}
              aria-label={`Delete document ${doc.title}`}
              className="inline-flex items-center gap-1 cursor-pointer"
              style={{
                fontSize: "var(--text-xs)",
                padding: "4px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--status-abstained-bg)",
                color: "var(--status-abstained-fg)",
                border: "1px solid var(--status-abstained-border)",
              }}
            >
              <Trash2 size={12} />
              <span>Delete</span>
            </button>
          </div>
        )}
      </div>
      <IngestionStatusStepper
        status={doc.status}
        errorMessage={doc.error_message}
      />
    </div>
  );
}

