import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import type { DocumentStatus } from "../../types/api";

export interface IngestionStatusStepperProps {
  status: DocumentStatus;
  errorMessage?: string | null;
}

const ORDERED_STAGES: DocumentStatus[] = [
  "QUEUED",
  "PARSING",
  "CHUNKING",
  "EMBEDDING",
  "EXTRACTING_KG",
  "INDEXED",
];

export function IngestionStatusStepper({
  status,
  errorMessage,
}: IngestionStatusStepperProps) {
  const currentStageIndex = ORDERED_STAGES.indexOf(status);
  const isFailed = status === "FAILED";

  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-center gap-1">
        {ORDERED_STAGES.map((stage, idx) => {
          const isCompleted =
            status === "INDEXED" || (currentStageIndex > idx && !isFailed);
          const isActive = status === stage && status !== "INDEXED";

          return (
            <span
              key={stage}
              className="font-mono-tabular inline-flex items-center gap-1"
              style={{
                fontSize: "var(--text-xs)",
                padding: "2px 6px",
                borderRadius: "var(--radius-sm)",
                borderWidth: "1px",
                borderStyle: "solid",
                backgroundColor: isCompleted
                  ? "var(--status-grounded-bg)"
                  : isActive
                    ? "var(--accent-primary-subtle)"
                    : "var(--bg-surface-subtle)",
                color: isCompleted
                  ? "var(--status-grounded-fg)"
                  : isActive
                    ? "var(--accent-primary)"
                    : "var(--text-muted)",
                borderColor: isCompleted
                  ? "var(--status-grounded-border)"
                  : isActive
                    ? "var(--border-focus)"
                    : "var(--border-subtle)",
              }}
            >
              {isCompleted && <CheckCircle2 size={11} />}
              {isActive && <Loader2 size={11} className="animate-spin" />}
              {stage}
            </span>
          );
        })}

        {isFailed && (
          <span
            className="font-mono-tabular inline-flex items-center gap-1"
            style={{
              fontSize: "var(--text-xs)",
              padding: "2px 6px",
              borderRadius: "var(--radius-sm)",
              borderWidth: "1px",
              borderStyle: "solid",
              backgroundColor: "var(--status-abstained-bg)",
              color: "var(--status-abstained-fg)",
              borderColor: "var(--status-abstained-border)",
            }}
          >
            <AlertCircle size={11} />
            FAILED
          </span>
        )}
      </div>
      {isFailed && errorMessage && (
        <span style={{ fontSize: "var(--text-xs)", color: "var(--status-abstained-fg)" }}>
          {errorMessage}
        </span>
      )}
    </div>
  );
}

