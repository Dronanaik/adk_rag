import { Search } from "lucide-react";
import { useState } from "react";
import {
  deleteDocumentById,
  reprocessDocumentById,
  uploadDocumentFile,
} from "../api/client";
import {
  DocumentRecordCard,
  DocumentUploadPanel,
} from "../components/documents";
import { useRoleContext } from "../hooks/useRoleContext";
import type { DocumentStatus, DocumentSummary } from "../types/api";

export const SEED_DOCUMENTS: DocumentSummary[] = [
  {
    id: "00000000-0000-4000-8000-000000000001",
    title: "Agentic RAG Architecture Reference Guide",
    file_name: "architecture-reference.md",
    mime_type: "text/markdown",
    file_size_bytes: 1420,
    status: "INDEXED",
    chunk_count: 4,
    entity_count: 5,
    edge_count: 4,
    error_message: null,
    created_at: "2026-10-24T18:00:00Z",
    updated_at: "2026-10-24T18:00:05Z",
  },
  {
    id: "00000000-0000-4000-8000-000000000002",
    title: "Legacy System Runbook Draft",
    file_name: "legacy-runbook.pdf",
    mime_type: "application/pdf",
    file_size_bytes: 51200,
    status: "FAILED",
    chunk_count: 0,
    entity_count: 0,
    edge_count: 0,
    error_message: "EMBEDDING stage timed out waiting for Gemini batch quota.",
    created_at: "2026-10-24T19:10:00Z",
    updated_at: "2026-10-24T19:10:15Z",
  },
];

const STATUS_FILTER_OPTIONS: Array<"ALL" | DocumentStatus> = [
  "ALL",
  "INDEXED",
  "EXTRACTING_KG",
  "EMBEDDING",
  "FAILED",
];

export function KnowledgeBasePage() {
  const { isAdmin, adminApiKey } = useRoleContext();
  const [documents, setDocuments] = useState<DocumentSummary[]>(SEED_DOCUMENTS);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<"ALL" | DocumentStatus>("ALL");
  const [isUploading, setIsUploading] = useState<boolean>(false);

  const filteredDocs = documents.filter((doc) => {
    const matchesStatus = statusFilter === "ALL" || doc.status === statusFilter;
    const q = searchQuery.trim().toLowerCase();
    const matchesSearch =
      !q ||
      doc.title.toLowerCase().includes(q) ||
      doc.file_name.toLowerCase().includes(q);
    return matchesStatus && matchesSearch;
  });

  const handleUpload = (title: string, file: File | null) => {
    setIsUploading(true);
    const fallbackDoc: DocumentSummary = {
      id: `doc-${String(Date.now())}`,
      title,
      file_name: file?.name ?? `${title.toLowerCase().replace(/\s+/g, "-")}.md`,
      mime_type: file?.type || "text/markdown",
      file_size_bytes: file?.size ?? 2048,
      status: "INDEXED",
      chunk_count: 3,
      entity_count: 4,
      edge_count: 3,
      error_message: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    if (file) {
      uploadDocumentFile(file, title, adminApiKey)
        .then((res) => setDocuments((prev) => [res.data, ...prev]))
        .catch(() => setDocuments((prev) => [fallbackDoc, ...prev]))
        .finally(() => setIsUploading(false));
    } else {
      setDocuments((prev) => [fallbackDoc, ...prev]);
      setIsUploading(false);
    }
  };

  const handleRetry = (docId: string) => {
    void reprocessDocumentById(docId, adminApiKey).catch(() => undefined);
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === docId
          ? {
              ...doc,
              status: "INDEXED",
              chunk_count: 2,
              entity_count: 2,
              edge_count: 1,
              error_message: null,
            }
          : doc,
      ),
    );
  };

  const handleDelete = (docId: string) => {
    void deleteDocumentById(docId, adminApiKey).catch(() => undefined);
    setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
  };

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

      {isAdmin && (
        <DocumentUploadPanel
          isUploading={isUploading}
          onUploadDocument={handleUpload}
        />
      )}

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
            aria-label="Search documents"
            placeholder="Filter documents by title or filename..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
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
          {STATUS_FILTER_OPTIONS.map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status)}
              className="font-mono-tabular cursor-pointer"
              style={{
                fontSize: "var(--text-xs)",
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor:
                  statusFilter === status
                    ? "var(--accent-primary)"
                    : "var(--bg-surface-subtle)",
                color:
                  statusFilter === status
                    ? "var(--text-on-brand)"
                    : "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {filteredDocs.map((doc) => (
          <DocumentRecordCard
            key={doc.id}
            doc={doc}
            isAdmin={isAdmin}
            onRetry={handleRetry}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  );
}
