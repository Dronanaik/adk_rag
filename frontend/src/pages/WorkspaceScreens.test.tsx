import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { App } from "../App";
import { RoleProvider } from "../context/RoleContext";
import { SessionProvider } from "../context/SessionContext";
import { ThemeProvider } from "../context/ThemeContext";
import { buildSimulatedTurn, parseSseFrame } from "../hooks/useTurnStream";
import { KnowledgeBasePage } from "./KnowledgeBasePage";
import { KnowledgeGraphExplorerPage } from "./KnowledgeGraphExplorerPage";
import { MemoryInspectorPage } from "./MemoryInspectorPage";
import { ResearchWorkspacePage } from "./ResearchWorkspacePage";

function renderWithProviders(ui: React.ReactNode) {
  return render(
    <ThemeProvider>
      <RoleProvider>
        <SessionProvider>
          <MemoryRouter>{ui}</MemoryRouter>
        </SessionProvider>
      </RoleProvider>
    </ThemeProvider>,
  );
}

describe("Phase 7 — Screens 1–4 & End-to-End Integration", () => {
  it("parses SSE frames and builds grounded vs abstained simulated turns", () => {
    const frame = parseSseFrame(
      'event: token\ndata: {"delta": "Verified claim [Doc:1]"}',
    );
    expect(frame).toEqual({
      event: "token",
      data: { delta: "Verified claim [Doc:1]" },
    });

    const grounded = buildSimulatedTurn(
      "session-01",
      "Explain OrchestratorAgent",
      true,
    );
    expect(grounded.grounding_status).toBe("GROUNDED");
    expect(grounded.citations).toHaveLength(3);

    const abstained = buildSimulatedTurn(
      "session-01",
      "Tell me an unsupported rumor",
      true,
    );
    expect(abstained.grounding_status).toBe("ABSTAINED");
    expect(abstained.citations).toHaveLength(0);
    expect(abstained.abstention_reason).toContain("0.65");
  });

  it("Screen 1 (ResearchWorkspacePage) submits queries and handles abstention", async () => {
    renderWithProviders(<ResearchWorkspacePage />);

    expect(
      screen.getByText("How does the 5-agent hierarchy enforce grounding?"),
    ).toBeInTheDocument();

    const input = screen.getByLabelText("Ask a multi-hop research question");
    fireEvent.change(input, {
      target: { value: "What happens with unsupported claims?" },
    });
    fireEvent.click(screen.getByLabelText("Send research query"));

    await waitFor(() => {
      expect(
        screen.getByText(/Abstention Diagnostics:/i),
      ).toBeInTheDocument();
    });
  });

  it("Screen 2 (KnowledgeBasePage) filters documents and supports Admin upload, retry, and delete", () => {
    render(<App />);

    // Navigate to Knowledge Base (Screen 2)
    fireEvent.click(screen.getByText("Knowledge Base"));
    expect(
      screen.getByText("Knowledge Base & Ingestion Manager"),
    ).toBeInTheDocument();
    expect(screen.getByText("Read-Only Researcher Mode")).toBeInTheDocument();

    // Switch to Knowledge Admin role in TopHeaderBar
    fireEvent.click(
      screen.getByRole("button", { name: "Knowledge Admin" }),
    );
    expect(screen.getByText("Admin Write Mode Enabled")).toBeInTheDocument();

    // Admin upload new document
    const titleInput = screen.getByLabelText("Document Title");
    fireEvent.change(titleInput, {
      target: { value: "Zero Trust Grounding Standard" },
    });
    fireEvent.click(screen.getByLabelText("Upload & Index Document"));
    expect(
      screen.getByText("Zero Trust Grounding Standard"),
    ).toBeInTheDocument();

    // Admin retry failed document
    const retryBtn = screen.getByLabelText(
      "Retry ingestion for Legacy System Runbook Draft",
    );
    fireEvent.click(retryBtn);

    // Admin delete document
    const deleteBtn = screen.getByLabelText(
      "Delete document Legacy System Runbook Draft",
    );
    fireEvent.click(deleteBtn);
    expect(
      screen.queryByText("Legacy System Runbook Draft"),
    ).not.toBeInTheDocument();
  });

  it("Screen 3 (KnowledgeGraphExplorerPage) filters entities by type and hop depth", () => {
    renderWithProviders(<KnowledgeGraphExplorerPage />);

    expect(
      screen.getByText("Interactive Knowledge Graph Explorer"),
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText("Knowledge graph node-link diagram"),
    ).toBeInTheDocument();

    // Filter by Policy entity type
    fireEvent.click(screen.getByRole("button", { name: "Policy" }));
    expect(screen.getByText("Canonical Entities (1)")).toBeInTheDocument();

    // Switch to 1 Hop traversal depth
    fireEvent.click(
      screen.getByRole("button", { name: "Set traversal depth to 1 hop" }),
    );
    expect(
      screen.getByText(/2D Ego-Network Topology \(1-Hop Bounded Traversal\)/i),
    ).toBeInTheDocument();
  });

  it("Screen 4 (MemoryInspectorPage) filters memory tiers and supports Admin edit & delete", () => {
    render(<App />);

    // Navigate to Memory Inspector (Screen 4)
    fireEvent.click(screen.getByText("Memory Inspector"));
    expect(
      screen.getByText("Centralized Memory Inspector"),
    ).toBeInTheDocument();

    // Switch to Knowledge Admin role
    fireEvent.click(
      screen.getByRole("button", { name: "Knowledge Admin" }),
    );

    // Open Edit modal for system.grounding_policy
    fireEvent.click(
      screen.getByLabelText("Edit memory system.grounding_policy"),
    );
    const contentArea = screen.getByLabelText("Memory Fact Content");
    fireEvent.change(contentArea, {
      target: {
        value:
          "Updated D-04 policy: Every claim requires verified tri-pillar citations.",
      },
    });
    fireEvent.click(screen.getByLabelText("Save Memory Changes"));

    expect(
      screen.getByText(
        "Updated D-04 policy: Every claim requires verified tri-pillar citations.",
      ),
    ).toBeInTheDocument();

    // Delete episodic memory entry
    fireEvent.click(
      screen.getByLabelText("Delete memory session.prior_retrieval_focus"),
    );
    expect(
      screen.queryByText("session.prior_retrieval_focus"),
    ).not.toBeInTheDocument();
  });

  it("renders KnowledgeBasePage and MemoryInspectorPage in standalone provider wrapper", () => {
    renderWithProviders(<KnowledgeBasePage />);
    expect(
      screen.getByText("Agentic RAG Architecture Reference Guide"),
    ).toBeInTheDocument();

    renderWithProviders(<MemoryInspectorPage />);
    expect(screen.getByText("system.grounding_policy")).toBeInTheDocument();
  });
});
