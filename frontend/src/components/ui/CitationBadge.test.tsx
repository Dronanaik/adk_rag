import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { parseInlineCitations } from "../../hooks/useInlineCitations";
import { CitationBadge } from "./CitationBadge";
import { GroundingStatusBanner } from "./GroundingStatusBanner";
import { IngestionStatusStepper } from "./IngestionStatusStepper";

describe("Tri-Pillar Provenance Primitives & Citation Parser", () => {
  it("parses inline [Doc:N], [KG:N], and [Mem:N] badges deterministically", () => {
    const sample = "Claim A [Doc:1] links to entity B [KG:2] and policy C [Mem:3].";
    const segments = parseInlineCitations(sample);
    const citations = segments.filter((s) => s.kind === "citation");
    expect(citations).toHaveLength(3);
    expect(citations[0]).toEqual({
      kind: "citation",
      badgeId: "[Doc:1]",
      modality: "Doc",
      badgeIndex: 1,
    });
    expect(citations[1]).toEqual({
      kind: "citation",
      badgeId: "[KG:2]",
      modality: "KG",
      badgeIndex: 2,
    });
    expect(citations[2]).toEqual({
      kind: "citation",
      badgeId: "[Mem:3]",
      modality: "Mem",
      badgeIndex: 3,
    });
  });

  it("renders CitationBadge with accessible label and click handler", () => {
    const handleClick = vi.fn();
    render(<CitationBadge modality="KG" index={4} isActive onClick={handleClick} />);
    const button = screen.getByRole("button", {
      name: "Inspect KG provenance citation 4",
    });
    expect(button).toHaveTextContent("[KG:4]");
    expect(button).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(button);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("renders GroundingStatusBanner states accurately", () => {
    render(
      <GroundingStatusBanner
        status="GROUNDED"
        confidenceScore={0.95}
        citationCount={3}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("VERIFIED GROUNDED");
    expect(screen.getByRole("status")).toHaveTextContent("Citations: 3");
    expect(screen.getByRole("status")).toHaveTextContent("Score: 95%");
  });

  it("renders IngestionStatusStepper 6-stage badges", () => {
    render(<IngestionStatusStepper status="EMBEDDING" />);
    expect(screen.getByText("QUEUED")).toBeInTheDocument();
    expect(screen.getByText("EMBEDDING")).toBeInTheDocument();
    expect(screen.getByText("INDEXED")).toBeInTheDocument();
  });
});

