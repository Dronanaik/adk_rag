import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import type { CSSProperties } from "react";
import type { GroundingStatus } from "../../types/api";

export interface GroundingStatusBannerProps {
  status: GroundingStatus;
  confidenceScore?: number;
  citationCount?: number;
  explanation?: string;
}

interface StatusVisualConfig {
  label: string;
  defaultExplanation: string;
  style: CSSProperties;
}

const STATUS_CONFIG: Record<GroundingStatus, StatusVisualConfig> = {
  GROUNDED: {
    label: "VERIFIED GROUNDED",
    defaultExplanation: "All claims verified against indexed document chunks, KG edges, or memory.",
    style: {
      color: "var(--status-grounded-fg)",
      backgroundColor: "var(--status-grounded-bg)",
      borderColor: "var(--status-grounded-border)",
    },
  },
  PARTIAL: {
    label: "PARTIAL GROUNDING",
    defaultExplanation: "Some retrieval modalities returned partial evidence; unverified claims omitted.",
    style: {
      color: "var(--status-partial-fg)",
      backgroundColor: "var(--status-partial-bg)",
      borderColor: "var(--status-partial-border)",
    },
  },
  ABSTAINED: {
    label: "ABSTAINED — INSUFFICIENT EVIDENCE",
    defaultExplanation: "SynthesisVerifierAgent abstained to prevent ungrounded fabrication.",
    style: {
      color: "var(--status-abstained-fg)",
      backgroundColor: "var(--status-abstained-bg)",
      borderColor: "var(--status-abstained-border)",
    },
  },
  INSUFFICIENT_EVIDENCE: {
    label: "INSUFFICIENT EVIDENCE",
    defaultExplanation: "No indexed chunks or graph entities exceeded the minimum similarity threshold.",
    style: {
      color: "var(--status-abstained-fg)",
      backgroundColor: "var(--status-abstained-bg)",
      borderColor: "var(--status-abstained-border)",
    },
  },
};

export function GroundingStatusBanner({
  status,
  confidenceScore,
  citationCount = 0,
  explanation,
}: GroundingStatusBannerProps) {
  const config = STATUS_CONFIG[status];
  const Icon =
    status === "GROUNDED"
      ? CheckCircle2
      : status === "PARTIAL"
        ? AlertTriangle
        : ShieldAlert;

  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-2"
      style={{
        ...config.style,
        padding: "var(--space-2) var(--space-3)",
        borderRadius: "var(--radius-md)",
        borderWidth: "1px",
        borderStyle: "solid",
      }}
    >
      <div className="flex items-center gap-2">
        <Icon size={16} aria-hidden="true" />
        <span
          className="font-mono-tabular uppercase tracking-wider"
          style={{ fontSize: "var(--text-xs)", fontWeight: 600 }}
        >
          {config.label}
        </span>
        <span style={{ fontSize: "var(--text-sm)" }}>
          {explanation ?? config.defaultExplanation}
        </span>
      </div>
      <div
        className="font-mono-tabular flex items-center gap-3"
        style={{ fontSize: "var(--text-xs)" }}
      >
        <span>Citations: {String(citationCount)}</span>
        {confidenceScore !== undefined && (
          <span>Score: {(confidenceScore * 100).toFixed(0)}%</span>
        )}
      </div>
    </div>
  );
}

