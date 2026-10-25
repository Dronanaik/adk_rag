import { AlertTriangle, MessageSquare } from "lucide-react";
import { parseInlineCitations } from "../../hooks/useInlineCitations";
import type { ChatTurnMessage, CitationItem } from "../../types/api";
import {
  AgentTraceTimeline,
  CitationBadge,
  GroundingStatusBanner,
} from "../ui";

export interface ChatTurnCardProps {
  turn: ChatTurnMessage;
  activeCitationId: string | null;
  onSelectCitation: (citation: CitationItem) => void;
}

export function ChatTurnCard({
  turn,
  activeCitationId,
  onSelectCitation,
}: ChatTurnCardProps) {
  const parsedSegments = parseInlineCitations(turn.assistant_response);

  const handleBadgeClick = (badgeId: string) => {
    const match = turn.citations.find((item) => item.badge_id === badgeId);
    if (match) {
      onSelectCitation(match);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div
        className="flex items-center gap-2 self-end"
        style={{
          padding: "var(--space-2) var(--space-4)",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--accent-primary-subtle)",
          color: "var(--text-primary)",
          border: "1px solid var(--provenance-doc-border)",
          maxWidth: "85%",
        }}
      >
        <MessageSquare size={14} style={{ color: "var(--accent-primary)" }} />
        <span style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>
          {turn.user_query}
        </span>
      </div>

      <GroundingStatusBanner
        status={turn.grounding_status}
        confidenceScore={turn.grounding_score}
        citationCount={turn.citations.length}
      />

      <AgentTraceTimeline steps={turn.trace_steps} defaultExpanded />

      {turn.abstention_reason && (
        <div
          role="alert"
          className="flex items-center gap-2"
          style={{
            padding: "var(--space-3)",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--status-abstained-bg)",
            color: "var(--status-abstained-fg)",
            border: "1px solid var(--status-abstained-border)",
            fontSize: "var(--text-xs)",
          }}
        >
          <AlertTriangle size={14} />
          <span>Abstention Diagnostics: {turn.abstention_reason}</span>
        </div>
      )}

      <article
        style={{
          padding: "var(--space-5)",
          borderRadius: "var(--radius-lg)",
          backgroundColor: "var(--bg-surface)",
          border: "1px solid var(--border-subtle)",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: "var(--text-md)",
            lineHeight: 1.65,
            color: "var(--text-primary)",
          }}
        >
          {parsedSegments.map((seg, idx) =>
            seg.kind === "text" ? (
              <span key={idx}>{seg.text}</span>
            ) : (
              <span key={idx} style={{ margin: "0 2px" }}>
                <CitationBadge
                  modality={seg.modality}
                  index={seg.badgeIndex}
                  isActive={activeCitationId === seg.badgeId}
                  onClick={() => handleBadgeClick(seg.badgeId)}
                />
              </span>
            ),
          )}
        </p>
      </article>
    </div>
  );
}

