import { Search } from "lucide-react";
import { useState } from "react";
import { deleteMemoryById, updateMemoryById } from "../api/client";
import { MemoryEditModal } from "../components/memory";
import { MemoryFactCard } from "../components/ui";
import { useRoleContext } from "../hooks/useRoleContext";
import type { MemoryFactItem, MemoryTier } from "../types/api";

export const SEED_MEMORIES: MemoryFactItem[] = [
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
  {
    id: "44444444-4444-4444-8444-444444444402",
    memory_tier: "EPISODIC",
    key_name: "session.prior_retrieval_focus",
    content:
      "Prior turn audited multi-hop dependency edges between OrchestratorAgent and SynthesisVerifierAgent.",
    confidence: 0.94,
    is_verified: true,
    is_edited_by_user: false,
    source_chunk_id: "11111111-1111-4111-8111-111111111101",
    source_node_id: "22222222-2222-4222-8222-222222222201",
    updated_at: "2026-10-24T18:05:00Z",
  },
];

const TIER_FILTERS: Array<"ALL" | MemoryTier> = [
  "ALL",
  "SEMANTIC",
  "EPISODIC",
  "SHORT_TERM",
];

export function MemoryInspectorPage() {
  const { isAdmin, adminApiKey } = useRoleContext();
  const [memories, setMemories] = useState<MemoryFactItem[]>(SEED_MEMORIES);
  const [tierFilter, setTierFilter] = useState<"ALL" | MemoryTier>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [editingMemory, setEditingMemory] = useState<MemoryFactItem | null>(
    null,
  );

  const filteredMemories = memories.filter((mem) => {
    const matchesTier = tierFilter === "ALL" || mem.memory_tier === tierFilter;
    const q = searchQuery.trim().toLowerCase();
    const matchesSearch =
      !q ||
      mem.key_name.toLowerCase().includes(q) ||
      mem.content.toLowerCase().includes(q);
    return matchesTier && matchesSearch;
  });

  const handleSaveEdit = (
    memoryId: string,
    updatedContent: string,
    updatedConfidence: number,
  ) => {
    void updateMemoryById(
      memoryId,
      { content: updatedContent, confidence: updatedConfidence },
      adminApiKey,
    ).catch(() => undefined);

    setMemories((prev) =>
      prev.map((m) =>
        m.id === memoryId
          ? {
              ...m,
              content: updatedContent,
              confidence: updatedConfidence,
              is_edited_by_user: true,
              updated_at: new Date().toISOString(),
            }
          : m,
      ),
    );
    setEditingMemory(null);
  };

  const handleDeleteMemory = (memoryId: string) => {
    void deleteMemoryById(memoryId, adminApiKey).catch(() => undefined);
    setMemories((prev) => prev.filter((m) => m.id !== memoryId));
  };

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

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div
          className="flex items-center gap-2 flex-1"
          style={{
            padding: "var(--space-2) var(--space-3)",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <Search size={14} style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            aria-label="Search memory facts"
            placeholder="Search verified memory facts by key or content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1"
            style={{
              border: "none",
              outline: "none",
              background: "transparent",
              fontSize: "var(--text-sm)",
              color: "var(--text-primary)",
            }}
          />
        </div>

        <div className="flex items-center gap-1">
          {TIER_FILTERS.map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => setTierFilter(tier)}
              className="font-mono-tabular cursor-pointer"
              style={{
                fontSize: "var(--text-xs)",
                padding: "4px 10px",
                borderRadius: "var(--radius-sm)",
                backgroundColor:
                  tierFilter === tier
                    ? "var(--provenance-mem-fg)"
                    : "var(--bg-surface-subtle)",
                color:
                  tierFilter === tier
                    ? "var(--text-on-brand)"
                    : "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      {editingMemory && (
        <MemoryEditModal
          memory={editingMemory}
          onSave={handleSaveEdit}
          onCancel={() => setEditingMemory(null)}
        />
      )}

      <div className="flex flex-col gap-3">
        {filteredMemories.map((mem) => (
          <MemoryFactCard
            key={mem.id}
            memory={mem}
            canManage={isAdmin}
            onEdit={(m) => setEditingMemory(m)}
            onDelete={handleDeleteMemory}
          />
        ))}
      </div>
    </div>
  );
}
