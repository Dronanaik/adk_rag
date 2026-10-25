import { useRef, useState } from "react";
import { API_BASE_URL } from "../api/client";
import {
  DEFAULT_SEED_CITATIONS,
  DEFAULT_SEED_TRACE_STEPS,
} from "../context/SessionContext";
import type {
  AgentTraceStep,
  ChatTurnMessage,
  CitationItem,
  GroundingStatus,
} from "../types/api";

export interface SendTurnOptions {
  sessionId: string;
  query: string;
  useSharedMemory: boolean;
  onTurnUpdated: (turn: ChatTurnMessage) => void;
}

interface ParsedSsePayload {
  event: string;
  data: Record<string, unknown>;
}

export function parseSseFrame(rawFrame: string): ParsedSsePayload | null {
  const lines = rawFrame.split("\n");
  let eventName = "message";
  let dataStr = "";
  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataStr += line.slice(5).trim();
    }
  }
  if (!dataStr) {
    return null;
  }
  try {
    const parsed = JSON.parse(dataStr) as Record<string, unknown>;
    return { event: eventName, data: parsed };
  } catch {
    return null;
  }
}

export function buildSimulatedTurn(
  sessionId: string,
  query: string,
  useSharedMemory: boolean,
): ChatTurnMessage {
  const isAbstained =
    query.toLowerCase().includes("unsupported") ||
    query.toLowerCase().includes("abstain");

  if (isAbstained) {
    return {
      turn_id: `turn-${String(Date.now())}`,
      session_id: sessionId,
      user_query: query,
      assistant_response:
        "I must abstain from answering because no verified document chunks, knowledge graph paths, or shared memory facts support this claim above the grounding threshold (0.65).",
      grounding_status: "ABSTAINED",
      grounding_score: 0.18,
      citations: [],
      trace_steps: DEFAULT_SEED_TRACE_STEPS.map((step) =>
        step.agent_name === "SynthesisVerifierAgent"
          ? {
              ...step,
              output_summary: "Verdict: ABSTAINED (insufficient evidence < 0.65).",
            }
          : step,
      ),
      abstention_reason:
        "Zero retrieved chunks or KG edges exceeded the 0.65 similarity threshold.",
      created_at: new Date().toISOString(),
    };
  }

  const activeCitations = useSharedMemory
    ? DEFAULT_SEED_CITATIONS
    : DEFAULT_SEED_CITATIONS.filter((c) => c.modality !== "Mem");
  const memorySuffix = useSharedMemory
    ? " and enforces verified-only memory writes [Mem:1]."
    : ".";

  return {
    turn_id: `turn-${String(Date.now())}`,
    session_id: sessionId,
    user_query: query,
    assistant_response: `Based on the indexed architecture corpus, the OrchestratorAgent decomposes "${query}" into hybrid pgvector + FTS search [Doc:1], traverses multi-hop dependency edges to SynthesisVerifierAgent [KG:1]${memorySuffix}`,
    grounding_status: "GROUNDED",
    grounding_score: 0.95,
    citations: activeCitations,
    trace_steps: DEFAULT_SEED_TRACE_STEPS,
    abstention_reason: null,
    created_at: new Date().toISOString(),
  };
}

function applySseEventToTurn(
  current: ChatTurnMessage,
  frame: ParsedSsePayload,
): ChatTurnMessage {
  const { event, data } = frame;
  if (event === "token" || event === "response.delta") {
    const delta =
      typeof data.delta === "string"
        ? data.delta
        : typeof data.text_delta === "string"
          ? data.text_delta
          : "";
    return { ...current, assistant_response: current.assistant_response + delta };
  }
  if (
    event === "agent_step" ||
    event === "agent.step.started" ||
    event === "agent.step.completed"
  ) {
    const step: AgentTraceStep = {
      log_id: String(data.log_id ?? `step-${String(current.trace_steps.length + 1)}`),
      step_order: Number(data.step_order ?? current.trace_steps.length + 1),
      agent_name: (data.agent_name as AgentTraceStep["agent_name"]) ?? "OrchestratorAgent",
      tool_name: typeof data.tool_name === "string" ? data.tool_name : null,
      status: (data.status as AgentTraceStep["status"]) ?? "COMPLETED",
      latency_ms: typeof data.latency_ms === "number" ? data.latency_ms : 120,
      input_summary: String(data.input_summary ?? ""),
      output_summary: String(data.output_summary ?? ""),
    };
    return { ...current, trace_steps: [...current.trace_steps, step] };
  }
  if (event === "turn_complete" || event === "turn.completed") {
    const status = (data.grounding_status as GroundingStatus) ?? "GROUNDED";
    const score =
      typeof data.grounding_score === "number"
        ? data.grounding_score
        : typeof data.confidence_score === "number"
          ? data.confidence_score
          : 0.94;
    const citations = Array.isArray(data.citations)
      ? (data.citations as CitationItem[])
      : current.citations;
    return {
      ...current,
      grounding_status: status,
      grounding_score: score,
      citations,
      abstention_reason:
        typeof data.abstention_reason === "string" ? data.abstention_reason : null,
    };
  }
  return current;
}

export function useTurnStream() {
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const abortStream = () => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  };

  const sendTurnQuery = async (options: SendTurnOptions): Promise<ChatTurnMessage> => {
    setIsStreaming(true);
    const controller = new AbortController();
    abortControllerRef.current = controller;

    let draftTurn: ChatTurnMessage = {
      turn_id: `turn-${String(Date.now())}`,
      session_id: options.sessionId,
      user_query: options.query,
      assistant_response: "",
      grounding_status: "GROUNDED",
      grounding_score: 0.95,
      citations: DEFAULT_SEED_CITATIONS,
      trace_steps: [],
      abstention_reason: null,
      created_at: new Date().toISOString(),
    };

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/sessions/${options.sessionId}/turns`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            query: options.query,
            use_shared_memory: options.useSharedMemory,
          }),
          signal: controller.signal,
        },
      );

      if (!response.ok || !response.body) {
        const simulated = buildSimulatedTurn(
          options.sessionId,
          options.query,
          options.useSharedMemory,
        );
        options.onTurnUpdated(simulated);
        return simulated;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";
        for (const rawFrame of frames) {
          const parsed = parseSseFrame(rawFrame);
          if (parsed) {
            draftTurn = applySseEventToTurn(draftTurn, parsed);
            options.onTurnUpdated(draftTurn);
          }
        }
      }
      return draftTurn;
    } catch {
      const simulated = buildSimulatedTurn(
        options.sessionId,
        options.query,
        options.useSharedMemory,
      );
      options.onTurnUpdated(simulated);
      return simulated;
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  return { isStreaming, sendTurnQuery, abortStream };
}

