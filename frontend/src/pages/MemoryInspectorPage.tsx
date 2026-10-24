import { MemoryFactCard } from "../components/ui";
import { useRoleContext } from "../hooks/useRoleContext";
import type { MemoryFactItem } from "../types/api";

const SEED_MEMORIES: MemoryFactItem[] = [
  {
    id: "44444444-4444-4444-8444-444444444401",
    memory_tier: "SEMANTIC",
    key_name: "system.grounding_policy",
    content:
      "Every synthesized claim must cite at least one verified Document chunk, Knowledge Graph edge, or Memory entry.",
    confidence: 0.98,
    is_verified: true,
    is_edited_by_user: false,
    source_chunk_id: "11111111-1111-4111-8111-111111111101",
    source_node_id: "22222222-2222-4222-8222-222222222202",
    updated_at: "2026-10-24T18:00:00Z",
  },
];

export function MemoryInspectorPage() {
  const { isAdmin } = useRoleContext();

  return (
    <div
      className="flex flex-col gap-4 mx-auto"
      style={{ maxWidth: "1040px", padding: "var(--space-6)" }}
    >
      <div>
        <h1
          className="font-display"
          style={{
            margin: 0,
            fontSize: "var(--text-xl)",
            fontWeight: 700,
            color: "var(--text-primary)",
          }}
        >
          Centralized Memory Inspector
        </h1>
        <p
          style={{
            margin: "var(--space-1) 0 0",
            fontSize: "var(--text-sm)",
            color: "var(--text-secondary)",
          }}
        >
          Screen 4 — Verified-Only Long-Term Semantic &amp; Episodic Memory Store (Decision D-04)
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {SEED_MEMORIES.map((mem) => (
          <MemoryFactCard key={mem.id} memory={mem} canManage={isAdmin} />
        ))}
      </div>
    </div>
  );
}

