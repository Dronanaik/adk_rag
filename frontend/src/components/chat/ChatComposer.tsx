import { Send, Square, Sparkles } from "lucide-react";
import { useState, type FormEvent } from "react";

export interface ChatComposerProps {
  isStreaming: boolean;
  onSubmitQuery: (query: string) => void;
  onAbortStream: () => void;
}

const STARTER_PROMPTS: string[] = [
  "How does the 5-agent hierarchy enforce tri-pillar grounding?",
  "Trace the dependency path from OrchestratorAgent to SynthesisVerifierAgent.",
  "What happens when a query has unsupported out-of-corpus claims?",
];

export function ChatComposer({
  isStreaming,
  onSubmitQuery,
  onAbortStream,
}: ChatComposerProps) {
  const [queryText, setQueryText] = useState<string>("");

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = queryText.trim();
    if (!trimmed || isStreaming) {
      return;
    }
    onSubmitQuery(trimmed);
    setQueryText("");
  };

  return (
    <section
      aria-label="Research Query Composer"
      className="flex flex-col gap-3"
      style={{
        padding: "var(--space-4)",
        borderRadius: "var(--radius-lg)",
        backgroundColor: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="inline-flex items-center gap-1 font-mono-tabular"
          style={{
            fontSize: "var(--text-xs)",
            color: "var(--text-muted)",
          }}
        >
          <Sparkles size={12} />
          Prompts:
        </span>
        {STARTER_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            disabled={isStreaming}
            onClick={() => onSubmitQuery(prompt)}
            className="cursor-pointer"
            style={{
              fontSize: "var(--text-xs)",
              padding: "3px 8px",
              borderRadius: "var(--radius-pill)",
              backgroundColor: "var(--bg-surface-subtle)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <input
          type="text"
          aria-label="Ask a multi-hop research question"
          placeholder="Ask a multi-hop question across Documents, Knowledge Graph & Shared Memory..."
          value={queryText}
          onChange={(e) => setQueryText(e.target.value)}
          disabled={isStreaming}
          className="flex-1"
          style={{
            padding: "var(--space-2) var(--space-3)",
            fontSize: "var(--text-sm)",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--bg-canvas)",
            color: "var(--text-primary)",
            border: "1px solid var(--border-strong)",
            outline: "none",
          }}
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={onAbortStream}
            aria-label="Stop streaming response"
            className="inline-flex items-center gap-1 cursor-pointer"
            style={{
              padding: "var(--space-2) var(--space-3)",
              fontSize: "var(--text-xs)",
              fontWeight: 600,
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--status-abstained-bg)",
              color: "var(--status-abstained-fg)",
              border: "1px solid var(--status-abstained-border)",
            }}
          >
            <Square size={13} />
            Stop
          </button>
        ) : (
          <button
            type="submit"
            aria-label="Send research query"
            className="inline-flex items-center gap-1 cursor-pointer"
            style={{
              padding: "var(--space-2) var(--space-4)",
              fontSize: "var(--text-xs)",
              fontWeight: 600,
              borderRadius: "var(--radius-md)",
              backgroundColor: "var(--accent-primary)",
              color: "var(--text-on-brand)",
              border: "none",
            }}
          >
            <Send size={13} />
            Send Query
          </button>
        )}
      </form>
    </section>
  );
}

