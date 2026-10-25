import { UploadCloud } from "lucide-react";
import { useState, type FormEvent } from "react";

export interface DocumentUploadPanelProps {
  isUploading: boolean;
  onUploadDocument: (title: string, file: File | null) => void;
}

export function DocumentUploadPanel({
  isUploading,
  onUploadDocument,
}: DocumentUploadPanelProps) {
  const [title, setTitle] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const effectiveTitle =
      title.trim() || selectedFile?.name || "Uploaded Architecture Specification";
    onUploadDocument(effectiveTitle, selectedFile);
    setTitle("");
    setSelectedFile(null);
  };

  return (
    <form
      onSubmit={handleSubmit}
      aria-label="Admin Document Ingestion Form"
      className="flex flex-col gap-3"
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-md)",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--provenance-doc-border)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div className="flex items-center justify-between">
        <span
          style={{
            fontSize: "var(--text-sm)",
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          Ingest New Corpus Document (.pdf, .md, .txt · Max 20 MB)
        </span>
        <span
          className="font-mono-tabular"
          style={{
            fontSize: "var(--text-xs)",
            color: "var(--provenance-doc-fg)",
          }}
        >
          SHA-256 Deduplicated
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-center">
        <input
          type="text"
          aria-label="Document Title"
          placeholder="Document title (e.g., Security Governance Policy)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{
            padding: "var(--space-2) var(--space-3)",
            fontSize: "var(--text-sm)",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--bg-canvas)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-strong)",
          }}
        />

        <input
          type="file"
          aria-label="Upload Document File"
          accept=".pdf,.md,.txt,application/pdf,text/markdown,text/plain"
          onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          style={{
            fontSize: "var(--text-xs)",
            color: "var(--text-secondary)",
          }}
        />

        <button
          type="submit"
          disabled={isUploading}
          aria-label="Upload & Index Document"
          className="inline-flex items-center justify-center gap-2 cursor-pointer"
          style={{
            padding: "var(--space-2) var(--space-4)",
            fontSize: "var(--text-xs)",
            fontWeight: 600,
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--accent-primary)",
            color: "var(--text-on-brand)",
            border: "none",
          }}
        >
          <UploadCloud size={14} />
          <span>{isUploading ? "Ingesting..." : "Upload & Index Document"}</span>
        </button>
      </div>
    </form>
  );
}

