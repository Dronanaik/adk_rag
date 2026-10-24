import type { ProvenanceModality } from "../types/api";

export type ParsedTextSegment =
  | { kind: "text"; text: string }
  | {
      kind: "citation";
      badgeId: string;
      modality: ProvenanceModality;
      badgeIndex: number;
    };

const CITATION_BADGE_REGEX = /\[(Doc|KG|Mem):(\d+)\]/g;

export function parseInlineCitations(content: string): ParsedTextSegment[] {
  const segments: ParsedTextSegment[] = [];
  let lastIndex = 0;

  for (const match of content.matchAll(CITATION_BADGE_REGEX)) {
    const matchIndex = match.index;
    const rawModality = match[1];
    const rawNumber = match[2];

    if (matchIndex === undefined || !rawModality || !rawNumber) {
      continue;
    }

    if (matchIndex > lastIndex) {
      segments.push({
        kind: "text",
        text: content.slice(lastIndex, matchIndex),
      });
    }

    const modality = rawModality as ProvenanceModality;
    const badgeIndex = Number.parseInt(rawNumber, 10);
    segments.push({
      kind: "citation",
      badgeId: `[${modality}:${String(badgeIndex)}]`,
      modality,
      badgeIndex,
    });

    lastIndex = matchIndex + match[0].length;
  }

  if (lastIndex < content.length) {
    segments.push({
      kind: "text",
      text: content.slice(lastIndex),
    });
  }

  return segments;
}

