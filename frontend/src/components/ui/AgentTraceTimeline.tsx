import { ChevronDown, ChevronRight, Cpu } from "lucide-react";
import { useState } from "react";
import type { AgentTraceStep } from "../../types/api";
import { AgentStepRow } from "./AgentStepRow";

export interface AgentTraceTimelineProps {
  steps: AgentTraceStep[];
  defaultExpanded?: boolean;
}

export function AgentTraceTimeline({
  steps,
  defaultExpanded = false,
}: AgentTraceTimelineProps) {
  const [expanded, setExpanded] = useState<boolean>(defaultExpanded);

  const totalLatencyMs = steps.reduce(
    (acc, step) => acc + (step.latency_ms ?? 0),
    0,
  );

  return (
    <div
      style={{
        backgroundColor: "var(--bg-surface-subtle)",
        borderColor: "var(--border-subtle)",
        borderWidth: "1px",
        borderStyle: "solid",
        borderRadius: "var(--radius-md)",
        padding: "var(--space-2) var(--space-3)",
      }}
    >
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between cursor-pointer"
        style={{
          background: "transparent",
          border: "none",
          padding: 0,
          color: "var(--text-secondary)",
        }}
      >
        <div className="flex items-center gap-2">
          <Cpu size={14} style={{ color: "var(--accent-primary)" }} />
          <span style={{ fontSize: "var(--text-xs)", fontWeight: 600 }}>
            ADK 5-Agent Execution Trace ({String(steps.length)} steps)
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="font-mono-tabular"
            style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)" }}
          >
            {String(totalLatencyMs)} ms total
          </span>
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {expanded && (
        <div
          className="flex flex-col gap-2"
          style={{ marginTop: "var(--space-2)" }}
        >
          {steps.map((step) => (
            <AgentStepRow key={step.log_id} step={step} />
          ))}
        </div>
      )}
    </div>
  );
}

