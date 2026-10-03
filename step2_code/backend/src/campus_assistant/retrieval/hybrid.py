"""Hybrid retrieval with Reciprocal Rank Fusion (RRF).

Combines BM25 and dense retrieval results using RRF scoring.
No direct addition of BM25 scores with cosine scores.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote


def rrf_fusion(
    bm25_hits: list[dict[str, Any]],
    dense_hits: list[dict[str, Any]],
    *,
    top_k: int = 5,
    k: int = 60,
) -> list[dict[str, Any]]:
    """Fuse BM25 and dense hits using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank)) for each list where chunk appears.
    Ranking starts from 1. Missing from one list contributes 0.

    Args:
        bm25_hits: BM25 results (sorted by rank).
        dense_hits: Dense results (sorted by rank).
        top_k: Maximum results to return.
        k: RRF constant (default 60 per Cormack et al.).

    Returns:
        Fused hits sorted by rrf_score desc, chunk_id asc.
    """
    # Build chunk_id -> rank maps
    bm25_rank: dict[str, int] = {}
    for h in bm25_hits:
        cid = h["chunk"]["chunk_id"]
        if cid not in bm25_rank:  # first occurrence = best rank
            bm25_rank[cid] = h["rank"]

    dense_rank: dict[str, int] = {}
    for h in dense_hits:
        cid = h["chunk"]["chunk_id"]
        if cid not in dense_rank:
            dense_rank[cid] = h["rank"]

    # Collect all unique chunk_ids
    all_ids = set(bm25_rank.keys()) | set(dense_rank.keys())

    # Compute RRF scores
    scored: list[tuple[float, str]] = []
    for cid in all_ids:
        score = 0.0
        if cid in bm25_rank:
            score += 1.0 / (k + bm25_rank[cid])
        if cid in dense_rank:
            score += 1.0 / (k + dense_rank[cid])
        scored.append((score, cid))

    # Sort: score desc, chunk_id asc
    scored.sort(key=lambda x: (-x[0], x[1]))
    scored = scored[:top_k]

    # Build chunk lookup from both hit lists
    chunk_map: dict[str, dict] = {}
    bm25_score_map: dict[str, float] = {}
    dense_score_map: dict[str, float] = {}

    for h in bm25_hits:
        cid = h["chunk"]["chunk_id"]
        if cid not in chunk_map:
            chunk_map[cid] = h["chunk"]
        if cid not in bm25_score_map:
            bm25_score_map[cid] = h["score"]

    for h in dense_hits:
        cid = h["chunk"]["chunk_id"]
        if cid not in chunk_map:
            chunk_map[cid] = h["chunk"]
        if cid not in dense_score_map:
            dense_score_map[cid] = h["score"]

    # Build output
    hits = []
    for rank, (rrf_score, cid) in enumerate(scored, start=1):
        chunk = chunk_map[cid]
        doc_id = chunk.get("document_id", "")
        block_id = chunk.get("block_id", "")
        preview_url = f"/preview#{quote(doc_id, safe='')}/{quote(block_id, safe='')}"

        hits.append({
            "rank": rank,
            "score": rrf_score,
            "chunk": chunk,
            "preview_url": preview_url,
            "matched_terms": [],  # RRF fusion doesn't produce term-level matches
            "bm25_rank": bm25_rank.get(cid),
            "dense_rank": dense_rank.get(cid),
            "bm25_score": bm25_score_map.get(cid),
            "dense_score": dense_score_map.get(cid),
        })

    return hits
