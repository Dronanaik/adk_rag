import { BrainCircuit, FileStack, MessageSquareText, Network } from "lucide-react";
import { NavLink } from "react-router-dom";

interface NavItemConfig {
  to: string;
  label: string;
  subtitle: string;
  icon: typeof MessageSquareText;
}

const NAV_ITEMS: NavItemConfig[] = [
  {
    to: "/workspace",
    label: "Research Workspace",
    subtitle: "Multi-Agent Chat & Citations",
    icon: MessageSquareText,
  },
  {
    to: "/documents",
    label: "Knowledge Base",
    subtitle: "Corpus & 6-Stage Ingestion",
    icon: FileStack,
  },
  {
    to: "/graph",
    label: "Knowledge Graph",
    subtitle: "2D Subgraph & Hop Paths",
    icon: Network,
  },
  {
    to: "/memory",
    label: "Memory Inspector",
    subtitle: "Verified Semantic & Episodic",
    icon: BrainCircuit,
  },
];

export function LeftSidebarNav() {
  return (
    <nav
      aria-label="Primary Workspace Navigation"
      className="flex flex-col justify-between shrink-0 h-full"
      style={{
        width: "var(--sidebar-width)",
        backgroundColor: "var(--bg-surface)",
        borderRight: "1px solid var(--border-subtle)",
        padding: "var(--space-3)",
      }}
    >
      <div className="flex flex-col gap-1">
        <div
          className="font-mono-tabular uppercase"
          style={{
            fontSize: "var(--text-xs)",
            color: "var(--text-muted)",
            padding: "var(--space-1) var(--space-2)",
            letterSpacing: "0.05em",
          }}
        >
          4 Core Screens
        </div>

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
                padding: "var(--space-2) var(--space-3)",
                borderRadius: "var(--radius-md)",
                textDecoration: "none",
                backgroundColor: isActive
                  ? "var(--accent-primary-subtle)"
                  : "transparent",
                color: isActive
                  ? "var(--accent-primary)"
                  : "var(--text-secondary)",
                border: isActive
                  ? "1px solid var(--provenance-doc-border)"
                  : "1px solid transparent",
              })}
            >
              <Icon size={17} />
              <div className="flex flex-col">
                <span
                  style={{
                    fontSize: "var(--text-sm)",
                    fontWeight: 600,
                    lineHeight: 1.25,
                  }}
                >
                  {item.label}
                </span>
                <span
                  style={{
                    fontSize: "var(--text-xs)",
                    color: "var(--text-muted)",
                  }}
                >
                  {item.subtitle}
                </span>
              </div>
            </NavLink>
          );
        })}
      </div>

      <div
        style={{
          padding: "var(--space-3)",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--bg-surface-subtle)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div
          className="font-mono-tabular"
          style={{
            fontSize: "var(--text-xs)",
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          Tri-Pillar Legend
        </div>
        <div
          className="flex flex-wrap items-center gap-2"
          style={{ marginTop: "var(--space-2)" }}
        >
          <span
            className="font-mono-tabular"
            style={{
              fontSize: "var(--text-xs)",
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--provenance-doc-bg)",
              color: "var(--provenance-doc-fg)",
              border: "1px solid var(--provenance-doc-border)",
            }}
          >
            [Doc:N]
          </span>
          <span
            className="font-mono-tabular"
            style={{
              fontSize: "var(--text-xs)",
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--provenance-kg-bg)",
              color: "var(--provenance-kg-fg)",
              border: "1px solid var(--provenance-kg-border)",
            }}
          >
            [KG:N]
          </span>
          <span
            className="font-mono-tabular"
            style={{
              fontSize: "var(--text-xs)",
              padding: "1px 6px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--provenance-mem-bg)",
              color: "var(--provenance-mem-fg)",
              border: "1px solid var(--provenance-mem-border)",
            }}
          >
            [Mem:N]
          </span>
        </div>
      </div>
    </nav>
  );
}

