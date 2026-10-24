import { CheckCircle2, Clock, Loader2, XCircle } from "lucide-react";
import type { AgentTraceStep } from "../../types/api";

export interface AgentStepRowProps {
  step: AgentTraceStep;
}

export function AgentStepRow({ step }: AgentStepRowProps) {
  const statusIcon = () => {
    if (step.status === "COMPLETED") {
      return <CheckCircle2 size={14} style={{ color: "var(--status-grounded-fg)" }} />;
    }
    if (step.status === "RUNNING") {
      return <Loader2 size={14} className="animate-spin" style={{ color: "var(--accent-primary)" }} />;
    }
    if (step.status === "FAILED") {
      return <XCircle size={14} style={{ color: "var(--status-abstained-fg)" }} />;
    }
    return <Clock size={14} style={{ color: "var(--text-muted)" }} />;
  };

  return (
    <div
      className="flex flex-col gap-1"
      style={{
        padding: "var(--space-2) var(--space-3)",
        backgroundColor: "var(--bg-surface)",
        borderColor: "var(--border-subtle)",
        borderWidth: "1px",
        borderStyle: "solid",
        borderRadius: "var(--radius-sm)",
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {statusIcon()}
          <span
            className="font-mono-tabular"
            style={{
              fontSize: "var(--text-xs)",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            {step.agent_name}
          </span>
          {step.tool_name && (
            <span
              className="font-mono-tabular"
              style={{
                fontSize: "var(--text-xs)",
                color: "var(--text-muted)",
              }}
            >
              → {step.tool_name}
            </span>
          )}
        </div>
        {step.latency_ms !== null && (
          <span
            className="font-mono-tabular"
            style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
          >
            {String(step.latency_ms)} ms
          </span>
        )}
      </div>
      <p
        style={{
          margin: 0,
          fontSize: "var(--text-xs)",
          color: "var(--text-secondary)",
        }}
      >
        {step.output_summary || step.input_summary}
      </p>
    </div>
  );
}

