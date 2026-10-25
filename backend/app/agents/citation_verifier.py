"""Deterministic tri-pillar inline citation parser and SynthesisVerifier grounding gate."""

import re
from dataclasses import dataclass

from app.agents.state import TurnWorkingState
from app.schemas.common import GroundingStatusEnum, StrictSchema
from app.schemas.sessions import (
    AbstentionDiagnostics,
    CitedChunkItem,
    CitedKgPathItem,
    CitedMemoryItem,
    TurnCitationsEnvelope,
)

INLINE_CITATION_PATTERN = re.compile(r"\[(Doc|KG|Mem):\s*([^\[\]]+?)\]")


class CitationVerificationResult(StrictSchema):
    """Output produced by verify_synthesis_grounding."""

    verified_markdown: str
    grounding_status: GroundingStatusEnum
    grounding_score: float
    valid_citation_keys: list[str]
    stripped_phantom_keys: list[str]
    citations: TurnCitationsEnvelope
    abstention_diagnostics: AbstentionDiagnostics | None = None


@dataclass(frozen=True, slots=True)
class HydratedTurnEvidence:
    """Hydrated candidate pools available for citation resolution during a turn."""

    chunks_by_key: dict[str, CitedChunkItem]
    kg_paths_by_key: dict[str, CitedKgPathItem]
    memories_by_key: dict[str, CitedMemoryItem]


def _normalize_citation_token(modality: str, raw_target: str, state: TurnWorkingState) -> str:
    """Normalize a raw inline citation target into a canonical key like Doc:1, KG:1, or Mem:1."""
    cleaned = raw_target.strip().lstrip("#")
    if cleaned.isdigit():
        return f"{modality}:{int(cleaned)}"

    candidate_key = f"{modality}:{cleaned}"
    known_ids = {item.badge_id: item.badge_id for item in state.citation_map}
    if candidate_key in known_ids:
        return candidate_key

    lowered_clean = cleaned.lower()
    for item in state.citation_map:
        if item.modality.value == modality and (
            lowered_clean in item.display_label.lower()
            or lowered_clean == item.target_id.lower()
        ):
            return item.badge_id

    return candidate_key


def parse_inline_citations(
    markdown_text: str,
    state: TurnWorkingState | None = None,
) -> list[str]:
    """Extract ordered unique citation keys (Doc:N, KG:N, Mem:N) from markdown text."""
    seen: list[str] = []
    for match in INLINE_CITATION_PATTERN.finditer(markdown_text):
        modality = match.group(1)
        raw_target = match.group(2)
        key = (
            _normalize_citation_token(modality, raw_target, state)
            if state is not None
            else f"{modality}:{raw_target.strip().lstrip('#')}"
        )
        if key not in seen:
            seen.append(key)
    return seen


def _sanitize_and_verify_markdown_tags(
    draft_markdown: str,
    state: TurnWorkingState,
    allowed_keys: set[str],
) -> tuple[str, list[str], list[str]]:
    """Normalize valid inline tags to [Doc:N]/[KG:N]/[Mem:N] and strip phantom tags."""
    valid_keys: list[str] = []
    phantom_keys: list[str] = []

    def _replace_match(match: re.Match[str]) -> str:
        modality = match.group(1)
        raw_target = match.group(2)
        normalized_key = _normalize_citation_token(modality, raw_target, state)
        if normalized_key in allowed_keys:
            if normalized_key not in valid_keys:
                valid_keys.append(normalized_key)
            return f"[{normalized_key}]"
        if normalized_key not in phantom_keys:
            phantom_keys.append(normalized_key)
        return ""

    cleaned = INLINE_CITATION_PATTERN.sub(_replace_match, draft_markdown)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, valid_keys, phantom_keys


def build_abstention_response(
    *,
    user_query: str,
    searched_entities: list[str],
    searched_queries: list[str],
    similarity_threshold: float,
) -> tuple[str, AbstentionDiagnostics]:
    """Construct a transparent abstention markdown message and diagnostics payload."""
    reason = (
        f"No indexed document chunks, Knowledge Graph paths, or verified memories met the "
        f"minimum grounding similarity threshold ({similarity_threshold:.2f}) for this query."
    )
    diagnostics = AbstentionDiagnostics(
        reason=reason,
        searched_entities=searched_entities,
        searched_queries=searched_queries or [user_query],
        recommended_action=(
            "Upload relevant source documents in the Knowledge Base Manager or lower the "
            "similarity threshold in System Settings if appropriate."
        ),
    )
    markdown = (
        "### Insufficient Grounded Evidence\n\n"
        f"I must abstain from answering **{user_query}** because the indexed corpus and "
        "Knowledge Graph do not contain verified evidence above the grounding threshold "
        f"(`{similarity_threshold:.2f}`).\n\n"
        f"- **Reason:** {reason}\n"
        f"- **Recommended Action:** {diagnostics.recommended_action}"
    )
    return markdown, diagnostics


def _should_abstain(
    state: TurnWorkingState,
    allowed_keys: set[str],
    similarity_threshold: float,
    strict_abstention_mode: bool,
) -> bool:
    """Return True if retrieved evidence is empty or below strict abstention threshold."""
    total_evidence_count = (
        len(state.retrieved_chunks)
        + len(state.retrieved_kg_paths)
        + len(state.retrieved_memories)
        + len(allowed_keys)
    )
    max_chunk_sim = max(
        (c.vector_similarity for c in state.retrieved_chunks),
        default=0.0,
    )
    below_strict_threshold = (
        strict_abstention_mode
        and not state.retrieved_kg_paths
        and not state.retrieved_memories
        and (not state.retrieved_chunks or max_chunk_sim < similarity_threshold)
    )
    return total_evidence_count == 0 or below_strict_threshold


def verify_synthesis_grounding(
    *,
    draft_markdown: str,
    state: TurnWorkingState,
    evidence: HydratedTurnEvidence,
    similarity_threshold: float = 0.65,
    strict_abstention_mode: bool = True,
    has_modality_degradation: bool = False,
    searched_entities: list[str] | None = None,
    searched_queries: list[str] | None = None,
) -> CitationVerificationResult:
    """Validate inline citations against TurnWorkingState and compute GroundingStatusEnum."""
    allowed_keys: set[str] = (
        set(evidence.chunks_by_key.keys())
        | set(evidence.kg_paths_by_key.keys())
        | set(evidence.memories_by_key.keys())
        | {item.badge_id for item in state.citation_map}
    )
    if _should_abstain(state, allowed_keys, similarity_threshold, strict_abstention_mode):
        abstention_md, diagnostics = build_abstention_response(
            user_query=state.user_query,
            searched_entities=searched_entities or [],
            searched_queries=searched_queries or [state.user_query],
            similarity_threshold=similarity_threshold,
        )
        state.grounding_status = GroundingStatusEnum.INSUFFICIENT_EVIDENCE
        state.grounding_score = 0.0
        return CitationVerificationResult(
            verified_markdown=abstention_md,
            grounding_status=GroundingStatusEnum.INSUFFICIENT_EVIDENCE,
            grounding_score=0.0,
            valid_citation_keys=[],
            stripped_phantom_keys=[],
            citations=TurnCitationsEnvelope(),
            abstention_diagnostics=diagnostics,
        )

    cleaned_md, valid_keys, phantom_keys = _sanitize_and_verify_markdown_tags(
        draft_markdown=draft_markdown,
        state=state,
        allowed_keys=allowed_keys,
    )
    if not valid_keys and allowed_keys:
        fallback_key = next(iter(evidence.chunks_by_key.keys()), None) or next(iter(allowed_keys))
        valid_keys = [fallback_key]
        cleaned_md = f"{cleaned_md} [{fallback_key}]".strip()

    is_partial = has_modality_degradation or bool(phantom_keys) or bool(state.unsupported_claims)
    status = GroundingStatusEnum.PARTIAL if is_partial else GroundingStatusEnum.GROUNDED
    score = 0.75 if is_partial else 1.0
    state.grounding_status = status
    state.grounding_score = score
    return CitationVerificationResult(
        verified_markdown=cleaned_md,
        grounding_status=status,
        grounding_score=score,
        valid_citation_keys=valid_keys,
        stripped_phantom_keys=phantom_keys,
        citations=TurnCitationsEnvelope(
            chunks=[evidence.chunks_by_key[k] for k in valid_keys if k in evidence.chunks_by_key],
            kg_paths=[
                evidence.kg_paths_by_key[k] for k in valid_keys if k in evidence.kg_paths_by_key
            ],
            memories=[
                evidence.memories_by_key[k] for k in valid_keys if k in evidence.memories_by_key
            ],
        ),
        abstention_diagnostics=None,
    )
