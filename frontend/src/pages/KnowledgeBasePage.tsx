import { IngestionStatusStepper } from "../components/ui";
import { useRoleContext } from "../hooks/useRoleContext";
import type { DocumentSummary } from "../types/api";

const SEED_DOCUMENTS: DocumentSummary[] = [
  {
    id: "00000000-0000-4000-8000-000000000001",
    title: "Agentic RAG Architecture Reference Guide",
    file_name: "architecture-reference.md",
    mime_type: "text/markdown",
    file_size_bytes: 1420,
    status: "INDEXED",
    chunk_count: 1,
    entity_count: 2,
    edge_count: 1,
    error_message: null,
    created_at: "2026-10-24T18:00:00Z",
    updated_at: "2026-10-24T18:00:05Z",
  },
];

export function KnowledgeBasePage() {
  const { isAdmin } = useRoleContext();

  return (
    <div
      className="flex flex-col gap-4 mx-auto"
      style={{ maxWidth: "1040px", padding: "var(--space-6)" }}
    >
      <div className="flex items-center justify-between">
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
            Knowledge Base &amp; Ingestion Manager
          </h1>
          <p
            style={{
              margin: "var(--space-1) 0 0",
              fontSize: "var(--text-sm)",
              color: "var(--text-secondary)",
            }}
          >
            Screen 2 — 6-Stage Ingestion Pipeline (QUEUED → PARSING → CHUNKING → EMBEDDING → EXTRACTING_KG → INDEXED)
          </p>
        </div>
        <span
          className="font-mono-tabular"
          style={{
            fontSize: "var(--text-xs)",
            padding: "4px 10px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: isAdmin
              ? "var(--status-grounded-bg)"
              : "var(--bg-surface-subtle)",
            color: isAdmin
              ? "var(--status-grounded-fg)"
              : "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          {isAdmin ? "Admin Write Mode Enabled" : "Read-Only Researcher Mode"}
        </span>
      </div>

      <div className="flex flex-col gap-3">
        {SEED_DOCUMENTS.map((doc) => (
          <div
            key={doc.id}
            className="flex flex-col gap-3"
            style={{
              padding: "var(--space-4)",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <div className="flex items-center justify-between">
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
            </div>
            <IngestionStatusStepper
              status={doc.status}
              errorMessage={doc.error_message}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

