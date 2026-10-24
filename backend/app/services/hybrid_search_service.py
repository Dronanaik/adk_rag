"""Canonical Reciprocal Rank Fusion (RRF) scoring service for hybrid retrieval."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Fused candidate result from dense vector search and PostgreSQL FTS."""

    item_id: str
    rrf_score: float
    vector_rank: int | None = None
    fts_rank: int | None = None


def compute_reciprocal_rank_fusion(
    vector_ordered_ids: list[str],
    fts_ordered_ids: list[str],
    k_constant: int = 60,
    top_k: int = 8,
) -> list[RankedCandidate]:
    """Fuse dense vector and full-text search rankings using RRF (k=60)."""
    if k_constant <= 0:
        raise ValueError("k_constant must be positive")
    if top_k <= 0:
        return []

    vector_ranks = {item_id: idx + 1 for idx, item_id in enumerate(vector_ordered_ids)}
    fts_ranks = {item_id: idx + 1 for idx, item_id in enumerate(fts_ordered_ids)}

    all_ids: list[str] = list(dict.fromkeys([*vector_ordered_ids, *fts_ordered_ids]))
    fused: list[RankedCandidate] = []

    for item_id in all_ids:
        v_rank = vector_ranks.get(item_id)
        f_rank = fts_ranks.get(item_id)
        score = 0.0
        if v_rank is not None:
            score += 1.0 / (k_constant + v_rank)
        if f_rank is not None:
            score += 1.0 / (k_constant + f_rank)
        fused.append(
            RankedCandidate(
                item_id=item_id,
                rrf_score=round(score, 6),
                vector_rank=v_rank,
                fts_rank=f_rank,
            )
        )

    fused.sort(key=lambda candidate: candidate.rrf_score, reverse=True)
    return fused[:top_k]

