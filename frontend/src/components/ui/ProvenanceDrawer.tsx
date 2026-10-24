import { BookOpen, Cpu, GitBranch, Sparkles, X } from "lucide-react";
import type { ProvenanceDrawerTab } from "../../context/SessionContext";
import type { AgentTraceStep, CitationItem } from "../../types/api";
import { AgentStepRow } from "./AgentStepRow";
import { CitationBadge } from "./CitationBadge";

export interface ProvenanceDrawerProps {
  isOpen: boolean;
  activeTab: ProvenanceDrawerTab;
  activeCitationId: string | null;
  citations: CitationItem[];
  traceSteps: AgentTraceStep[];
  onTabChange: (tab: ProvenanceDrawerTab) => void;
  onSelectCitation: (citation: CitationItem) => void;
  onClose: () => void;
}

const DRAWER_TABS: Array<{ id: ProvenanceDrawerTab; label: string }> = [
  { id: "Doc", label: "Documents" },
  { id: "KG", label: "KG Paths" },
  { id: "Mem", label: "Shared Memory" },
  { id: "Trace", label: "Agent Trace" },
];

export function ProvenanceDrawer({
  isOpen,
  activeTab,
  activeCitationId,
  citations,
  traceSteps,
  onTabChange,
  onSelectCitation,
  onClose,
}: ProvenanceDrawerProps) {
  if (!isOpen) {
    return null;
  }

  const filteredCitations =
    activeTab === "Trace"
      ? []
      : citations.filter((item) => item.modality === activeTab);

  const tabIcon = (tab: ProvenanceDrawerTab) => {
    if (tab === "Doc") return <BookOpen size={14} />;
    if (tab === "KG") return <GitBranch size={14} />;
    if (tab === "Mem") return <Sparkles size={14} />;
    return <Cpu size={14} />;
  };

  return (
    <aside
      aria-label="Provenance & Evidence Inspector"
      className="flex flex-col shrink-0 h-full overflow-hidden"
      style={{
        width: "var(--drawer-width-desktop)",
        backgroundColor: "var(--bg-surface)",
        borderLeft: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-drawer)",
      }}
    >
      <div
        className="flex items-center justify-between"
        style={{
          padding: "var(--space-3) var(--space-4)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div>
          <h2
            className="font-display"
            style={{
              margin: 0,
              fontSize: "var(--text-base)",
              fontWeight: 600,
              color: "var(--text-primary)",
            }}
          >
            Provenance Inspector
          </h2>
          <p
            style={{
              margin: 0,
              fontSize: "var(--text-xs)",
              color: "var(--text-muted)",
            }}
          >
            Tri-pillar grounding evidence &amp; ADK trace
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close Provenance Inspector"
          className="cursor-pointer"
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
            padding: "var(--space-1)",
          }}
        >
          <X size={16} />
        </button>
      </div>

      <div
        role="tablist"
        className="grid grid-cols-4"
        style={{
          backgroundColor: "var(--bg-surface-subtle)",
          borderBottom: "1px solid var(--border-subtle)",
          padding: "var(--space-1)",
          gap: "var(--space-1)",
        }}
      >
        {DRAWER_TABS.map((tab) => {
          const isSelected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isSelected}
              onClick={() => onTabChange(tab.id)}
              className="flex items-center justify-center gap-1 cursor-pointer"
              style={{
                padding: "var(--space-2) var(--space-1)",
                fontSize: "var(--text-xs)",
                fontWeight: isSelected ? 600 : 500,
                borderRadius: "var(--radius-sm)",
                border: "none",
                backgroundColor: isSelected ? "var(--bg-surface)" : "transparent",
                color: isSelected ? "var(--accent-primary)" : "var(--text-secondary)",
                boxShadow: isSelected ? "var(--shadow-sm)" : "none",
              }}
            >
              {tabIcon(tab.id)}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      <div
        className="flex-1 overflow-y-auto flex flex-col gap-3"
        style={{ padding: "var(--space-4)" }}
      >
        {activeTab === "Trace" ? (
          traceSteps.length > 0 ? (
            traceSteps.map((step) => <AgentStepRow key={step.log_id} step={step} />)
          ) : (
            <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
              No agent trace steps recorded for this turn yet.
            </p>
          )
        ) : filteredCitations.length > 0 ? (
          filteredCitations.map((item) => {
            const isHighlighted = activeCitationId === item.badge_id;
            return (
              <div
                key={item.badge_id}
                onClick={() => onSelectCitation(item)}
                className="flex flex-col gap-2 cursor-pointer"
                style={{
                  padding: "var(--space-3)",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: isHighlighted
                    ? "var(--accent-primary-subtle)"
                    : "var(--bg-surface-subtle)",
                  borderWidth: "1px",
                  borderStyle: "solid",
                  borderColor: isHighlighted
                    ? "var(--border-focus)"
                    : "var(--border-subtle)",
                }}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <CitationBadge
                      modality={item.modality}
                      index={item.badge_index}
                      isActive={isHighlighted}
                    />
                    <span
                      style={{
                        fontSize: "var(--text-sm)",
                        fontWeight: 600,
                        color: "var(--text-primary)",
                      }}
                    >
                      {item.title}
                    </span>
                  </div>
                  <span
                    className="font-mono-tabular"
                    style={{
                      fontSize: "var(--text-xs)",
                      color: "var(--text-muted)",
                    }}
                  >
                    {(item.score * 100).toFixed(0)}% match
                  </span>
                </div>
                <p
                  style={{
                    margin: 0,
                    fontSize: "var(--text-xs)",
                    color: "var(--text-secondary)",
                    lineHeight: 1.5,
                  }}
                >
                  “{item.excerpt}”
                </p>
              </div>
            );
          })
        ) : (
          <p style={{ fontSize: "var(--text-sm)", color: "var(--text-muted)" }}>
            No {activeTab} provenance items cited in the active response.
          </p>
        )}
      </div>
    </aside>
  );
}

