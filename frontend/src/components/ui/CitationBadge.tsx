import type { CSSProperties } from "react";
import type { ProvenanceModality } from "../../types/api";

export interface CitationBadgeProps {
  modality: ProvenanceModality;
  index: number;
  isActive?: boolean;
  onClick?: () => void;
}

const MODALITY_TOKEN_STYLES: Record<ProvenanceModality, CSSProperties> = {
  Doc: {
    color: "var(--provenance-doc-fg)",
    backgroundColor: "var(--provenance-doc-bg)",
    borderColor: "var(--provenance-doc-border)",
  },
  KG: {
    color: "var(--provenance-kg-fg)",
    backgroundColor: "var(--provenance-kg-bg)",
    borderColor: "var(--provenance-kg-border)",
  },
  Mem: {
    color: "var(--provenance-mem-fg)",
    backgroundColor: "var(--provenance-mem-bg)",
    borderColor: "var(--provenance-mem-border)",
  },
};

export function CitationBadge({
  modality,
  index,
  isActive = false,
  onClick,
}: CitationBadgeProps) {
  const badgeText = `[${modality}:${String(index)}]`;
  const tokenStyle = MODALITY_TOKEN_STYLES[modality];

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`Inspect ${modality} provenance citation ${String(index)}`}
      aria-pressed={isActive}
      className="font-mono-tabular inline-flex items-center cursor-pointer transition-transform select-none"
      style={{
        ...tokenStyle,
        fontSize: "var(--text-xs)",
        fontWeight: 600,
        padding: "1px 6px",
        borderRadius: "var(--radius-sm)",
        borderWidth: "1px",
        borderStyle: "solid",
        boxShadow: isActive ? "0 0 0 2px var(--border-focus)" : "none",
      }}
    >
      {badgeText}
    </button>
  );
}

