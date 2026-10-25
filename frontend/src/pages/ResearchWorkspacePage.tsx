import { BrainCircuit, PlusCircle } from "lucide-react";
import { useState } from "react";
import { ChatComposer, ChatTurnCard } from "../components/chat";
import {
  DEFAULT_SEED_CITATIONS,
  DEFAULT_SEED_TRACE_STEPS,
} from "../context/SessionContext";
import { useSessionContext } from "../hooks/useSessionContext";
import { useTurnStream } from "../hooks/useTurnStream";
import type { ChatTurnMessage, CitationItem } from "../types/api";

export const SEED_CITATIONS = DEFAULT_SEED_CITATIONS;
export const SEED_TRACE_STEPS = DEFAULT_SEED_TRACE_STEPS;

const SAMPLE_SYNTHESIZED_TEXT =
  "The OrchestratorAgent decomposes incoming research queries and dispatches specialist retrieval tools [Doc:1]. Retrieved evidence is routed along verified dependency edges to the SynthesisVerifierAgent [KG:1], which enforces the system grounding policy before any response or long-term memory write occurs [Mem:1].";

const INITIAL_TURN: ChatTurnMessage = {
  turn_id: "turn-seed-001",
  session_id: "session-seed-001",
  user_query: "How does the 5-agent hierarchy enforce grounding?",
  assistant_response: SAMPLE_SYNTHESIZED_TEXT,
  grounding_status: "GROUNDED",
  grounding_score: 0.96,
  citations: SEED_CITATIONS,
  trace_steps: SEED_TRACE_STEPS,
  abstention_reason: null,
  created_at: "2026-10-24T18:00:00Z",
};

export function ResearchWorkspacePage() {
  const {
    activeSessionId,
    activeCitationId,
    setActiveSessionId,
    openProvenanceForCitation,
    setSessionCitations,
    setSessionTraceSteps,
  } = useSessionContext();
  const { isStreaming, sendTurnQuery, abortStream } = useTurnStream();

  const [useSharedMemory, setUseSharedMemory] = useState<boolean>(true);
  const [turns, setTurns] = useState<ChatTurnMessage[]>([INITIAL_TURN]);

  const handleCitationSelect = (citation: CitationItem, turn: ChatTurnMessage) => {
    setSessionCitations(turn.citations);
    setSessionTraceSteps(turn.trace_steps);
    openProvenanceForCitation(citation);
  };

  const handleSubmitQuery = (query: string) => {
    void sendTurnQuery({
      sessionId: activeSessionId,
      query,
      useSharedMemory,
      onTurnUpdated: (updatedTurn) => {
        setTurns((prev) => {
          const exists = prev.some((t) => t.turn_id === updatedTurn.turn_id);
          if (exists) {
            return prev.map((t) =>
              t.turn_id === updatedTurn.turn_id ? updatedTurn : t,
            );
          }
          return [...prev, updatedTurn];
        });
        setSessionCitations(updatedTurn.citations);
        setSessionTraceSteps(updatedTurn.trace_steps);
      },
    });
  };

  const handleNewSession = () => {
    const nextId = `session-${String(Date.now()).slice(-6)}`;
    setActiveSessionId(nextId);
    setTurns([INITIAL_TURN]);
    setSessionCitations(SEED_CITATIONS);
    setSessionTraceSteps(SEED_TRACE_STEPS);
  };

  return (
    <div
      className="flex flex-col gap-4 mx-auto"
      style={{
        maxWidth: "840px",
        padding: "var(--space-6)",
      }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
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
            Research Workspace
          </h1>
          <p
            style={{
              margin: "var(--space-1) 0 0",
              fontSize: "var(--text-sm)",
              color: "var(--text-secondary)",
            }}
          >
            Screen 1 — Multi-Agent Chat, Inline Tri-Pillar Citations &amp; Live ADK Trace
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label
            className="inline-flex items-center gap-2 cursor-pointer"
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-md)",
              backgroundColor: useSharedMemory
                ? "var(--provenance-mem-bg)"
                : "var(--bg-surface-subtle)",
              color: useSharedMemory
                ? "var(--provenance-mem-fg)"
                : "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
              fontSize: "var(--text-xs)",
              fontWeight: 600,
            }}
          >
            <input
              type="checkbox"
              checked={useSharedMemory}
              onChange={(e) => setUseSharedMemory(e.target.checked)}
              aria-label="Include Shared Memory"
            />
            <BrainCircuit size={13} />
            <span>Shared Memory</span>
          </label>

          <button
            type="button"
            onClick={handleNewSession}
            aria-label="Start new research session"
            className="inline-flex items-center gap-1 cursor-pointer"
            style={{
              padding: "4px 10px",
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--bg-surface-subtle)",
              color: "var(--text-primary)",
              border: "1px solid var(--border-subtle)",
              fontSize: "var(--text-xs)",
              fontWeight: 600,
            }}
          >
            <PlusCircle size={13} />
            <span>New Session ({activeSessionId})</span>
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        {turns.map((turn) => (
          <ChatTurnCard
            key={turn.turn_id}
            turn={turn}
            activeCitationId={activeCitationId}
            onSelectCitation={(citation) => handleCitationSelect(citation, turn)}
          />
        ))}
      </div>

      <ChatComposer
        isStreaming={isStreaming}
        onSubmitQuery={handleSubmitQuery}
        onAbortStream={abortStream}
      />
    </div>
  );
}
