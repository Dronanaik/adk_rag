import { Shield, UserCheck } from "lucide-react";
import type { AppRole } from "../../types/api";

export interface RoleSwitcherPillProps {
  role: AppRole;
  onChangeRole: (nextRole: AppRole) => void;
}

export function RoleSwitcherPill({
  role,
  onChangeRole,
}: RoleSwitcherPillProps) {
  return (
    <div
      role="group"
      aria-label="Active application role"
      className="inline-flex items-center"
      style={{
        backgroundColor: "var(--bg-surface-subtle)",
        border: "1px solid var(--border-subtle)",
        borderRadius: "var(--radius-pill)",
        padding: "2px",
      }}
    >
      <button
        type="button"
        onClick={() => onChangeRole("researcher")}
        aria-pressed={role === "researcher"}
        className="inline-flex items-center gap-1 cursor-pointer"
        style={{
          fontSize: "var(--text-xs)",
          fontWeight: role === "researcher" ? 600 : 500,
          padding: "4px 10px",
          borderRadius: "var(--radius-pill)",
          border: "none",
          backgroundColor:
            role === "researcher" ? "var(--bg-surface)" : "transparent",
          color:
            role === "researcher"
              ? "var(--text-primary)"
              : "var(--text-secondary)",
          boxShadow: role === "researcher" ? "var(--shadow-sm)" : "none",
        }}
      >
        <UserCheck size={13} />
        <span>Researcher</span>
      </button>

      <button
        type="button"
        onClick={() => onChangeRole("admin")}
        aria-pressed={role === "admin"}
        className="inline-flex items-center gap-1 cursor-pointer"
        style={{
          fontSize: "var(--text-xs)",
          fontWeight: role === "admin" ? 600 : 500,
          padding: "4px 10px",
          borderRadius: "var(--radius-pill)",
          border: "none",
          backgroundColor:
            role === "admin" ? "var(--accent-primary)" : "transparent",
          color:
            role === "admin" ? "var(--text-on-brand)" : "var(--text-secondary)",
        }}
      >
        <Shield size={13} />
        <span>Knowledge Admin</span>
      </button>
    </div>
  );
}

