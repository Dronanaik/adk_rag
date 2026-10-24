import { Moon, PanelRight, Sparkles, Sun } from "lucide-react";
import { useRoleContext } from "../../hooks/useRoleContext";
import { useSessionContext } from "../../hooks/useSessionContext";
import { useThemeContext } from "../../hooks/useThemeContext";
import { RoleSwitcherPill } from "./RoleSwitcherPill";

export function TopHeaderBar() {
  const { role, setRole } = useRoleContext();
  const { isDrawerOpen, setIsDrawerOpen } = useSessionContext();
  const { theme, toggleTheme } = useThemeContext();

  return (
    <header
      className="flex items-center justify-between shrink-0"
      style={{
        height: "var(--header-height)",
        padding: "0 var(--space-4)",
        backgroundColor: "var(--bg-glass-header)",
        borderBottom: "1px solid var(--border-subtle)",
        backdropFilter: "blur(8px)",
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="flex items-center justify-center"
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--accent-primary)",
            color: "var(--text-on-brand)",
          }}
        >
          <Sparkles size={16} />
        </div>
        <div>
          <span
            className="font-display"
            style={{
              fontSize: "var(--text-base)",
              fontWeight: 700,
              color: "var(--text-primary)",
            }}
          >
            Agentic RAG Workbench
          </span>
          <span
            className="font-mono-tabular hidden sm:inline-block"
            style={{
              marginLeft: "var(--space-2)",
              fontSize: "var(--text-xs)",
              color: "var(--text-muted)",
            }}
          >
            Google ADK · pgvector · Tri-Pillar Provenance
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <RoleSwitcherPill role={role} onChangeRole={setRole} />

        <button
          type="button"
          onClick={toggleTheme}
          aria-label="Toggle color theme"
          className="inline-flex items-center justify-center cursor-pointer"
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--bg-surface-subtle)",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
        </button>

        <button
          type="button"
          onClick={() => setIsDrawerOpen(!isDrawerOpen)}
          aria-label="Toggle Provenance Inspector Drawer"
          aria-pressed={isDrawerOpen}
          className="inline-flex items-center gap-1 cursor-pointer"
          style={{
            fontSize: "var(--text-xs)",
            fontWeight: 600,
            padding: "6px 10px",
            borderRadius: "var(--radius-md)",
            backgroundColor: isDrawerOpen
              ? "var(--accent-primary-subtle)"
              : "var(--bg-surface-subtle)",
            color: isDrawerOpen
              ? "var(--accent-primary)"
              : "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <PanelRight size={14} />
          <span className="hidden md:inline">Provenance</span>
        </button>
      </div>
    </header>
  );
}

