"""Retrieval evaluation metrics — pure functions.

Implements Evidence Recall@K, Hit@K, and MRR@K over character-interval
intersection. No I/O, no network, no side effects.
"""

from __future__ import annotations

from typing import Any, Optional


def _interval_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    """Length of overlap between two half-open intervals [a_start, a_end) and [b_start, b_end).
    Returns 0 if no overlap."""
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    return max(0, end - start)


def _intervals_cover_target(
    intervals: list[tuple[int, int]], target_start: int, target_end: int
) -> bool:
    """Check if the union of intervals fully covers [target_start, target_end).

    Intervals are half-open [start, end). Adjacent intervals can be merged.
    Returns True only if every character in the target range is covered.
    """
    if target_start >= target_end:
        return True  # empty target is trivially covered

    # Filter to intervals that overlap the target
    relevant = []
    for s, e in intervals:
        os = max(s, target_start)
        oe = min(e, target_end)
        if os < oe:
            relevant.append((os, oe))

    if not relevant:
        return False

    # Sort by start
    relevant.sort()

    # Merge and check coverage
    current_end = target_start
    for s, e in relevant:
        if s > current_end:
            return False  # gap
        current_end = max(current_end, e)

    return current_end >= target_end


def evaluate_question(
    question: dict[str, Any],
    hits: list[dict[str, Any]],
    *,
    top_k: int = 5,
) -> dict[str, Any]:
    """Evaluate a single question against retrieval hits.

    Args:
        question: Question dict with question_id, query, answerable, evidence.
        hits: List of hit dicts from BM25Index.search(), each with
              document_id, block_id, char_start, char_end in chunk.
        top_k: Number of top hits to consider.

    Returns:
        Dict with question_id, query, answerable, hit_summary, gold_count,
        covered_evidence_ids, recall, hit, mrr, returned_count.
    """
    qid = question["question_id"]
    query = question["query"]
    answerable = question["answerable"]
    evidence_list = question.get("evidence", [])
    gold_count = len(evidence_list)

    # Take top-K positive-score hits
    top_hits = [h for h in hits if h.get("score", 0) > 0][:top_k]

    # Build hit summary
    hit_summary = []
    for rank, h in enumerate(top_hits, start=1):
        chunk = h.get("chunk", {})
        hit_summary.append({
            "rank": rank,
            "score": h.get("score", 0),
            "document_id": chunk.get("document_id", ""),
            "block_id": chunk.get("block_id", ""),
            "chunk_id": chunk.get("chunk_id", ""),
            "char_start": chunk.get("char_start", 0),
            "char_end": chunk.get("char_end", 0),
            "preview_url": h.get("preview_url", ""),
        })

    if not answerable:
        return {
            "question_id": qid,
            "query": query,
            "answerable": False,
            "hit_summary": hit_summary,
            "gold_count": 0,
            "covered_evidence_ids": [],
            "recall": None,
            "hit": None,
            "mrr": None,
            "returned_count": len(top_hits),
        }

    # For answerable questions, evaluate each evidence unit
    covered_ids: list[str] = []
    first_relevant_rank: Optional[int] = None

    for ev in evidence_list:
        ev_doc = ev["document_id"]
        ev_block = ev["block_id"]
        ev_start = ev["char_start"]
        ev_end = ev["char_end"]
        ev_len = ev_end - ev_start

        # Find all hit intervals that are in the same document+block
        same_block_intervals = []
        for rank, h in enumerate(top_hits, start=1):
            chunk = h.get("chunk", {})
            if chunk.get("document_id") == ev_doc and chunk.get("block_id") == ev_block:
                h_start = chunk.get("char_start", 0)
                h_end = chunk.get("char_end", 0)
                same_block_intervals.append((h_start, h_end))
                # Check if this hit has any overlap with the evidence (for Hit/MRR)
                if _interval_overlap(h_start, h_end, ev_start, ev_end) > 0:
                    if first_relevant_rank is None or rank < first_relevant_rank:
                        first_relevant_rank = rank

        # Check if the union of same-block intervals fully covers the evidence
        if _intervals_cover_target(same_block_intervals, ev_start, ev_end):
            covered_ids.append(ev["evidence_id"])

    # T027-R1 fact grouping（可替代证据组）：同 fact_id 的来源互为替代（组内 OR——
    # 任一来源被完整覆盖即该事实满足）；不同 fact_id 是不同必要事实（组间 AND）。
    # 未标 fact_id 的旧数据：每条证据自成一组（事实），与原逐证据口径完全一致。
    facts: list[dict] = []
    fact_index: dict[str, dict] = {}
    for ev in evidence_list:
        fid = ev.get("fact_id") or f"__ev_{ev['evidence_id']}"
        if fid not in fact_index:
            fact_index[fid] = {
                "fact_id": ev.get("fact_id"),
                "evidence_ids": [],
                "covered": False,
            }
            facts.append(fact_index[fid])
        fact_index[fid]["evidence_ids"].append(ev["evidence_id"])

    covered_set = set(covered_ids)
    for ev in evidence_list:
        fid = ev.get("fact_id") or f"__ev_{ev['evidence_id']}"
        if ev["evidence_id"] in covered_set:
            fact_index[fid]["covered"] = True

    fact_count = len(facts)
    covered_fact_count = sum(1 for f in facts if f["covered"])
    # recall 分母 = 必要事实数（组间 AND；重复来源不作为多个必须找齐的事实）
    recall = covered_fact_count / fact_count if fact_count > 0 else 0.0
    hit = 1.0 if first_relevant_rank is not None else 0.0
    mrr = (1.0 / first_relevant_rank) if first_relevant_rank is not None else 0.0

    return {
        "question_id": qid,
        "query": query,
        "answerable": True,
        "hit_summary": hit_summary,
        "gold_count": gold_count,
        "fact_count": fact_count,
        "covered_fact_count": covered_fact_count,
        "facts": facts,
        "covered_evidence_ids": covered_ids,
        "recall": recall,
        "hit": hit,
        "mrr": mrr,
        "returned_count": len(top_hits),
    }


def compute_summary(
    per_question: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute aggregate metrics across all questions.

    Returns dict with evidence_recall, hit, mrr (macro-averaged over
    answerable questions), unanswerable_count, empty_result_rate.
    """
    answerable = [q for q in per_question if q.get("answerable") is True]
    unanswerable = [q for q in per_question if q.get("answerable") is False]

    n_answerable = len(answerable)
    n_unanswerable = len(unanswerable)

    if n_answerable == 0:
        evidence_recall = None
        hit = None
        mrr = None
    else:
        evidence_recall = sum(q["recall"] for q in answerable) / n_answerable
        hit = sum(q["hit"] for q in answerable) / n_answerable
        mrr = sum(q["mrr"] for q in answerable) / n_answerable

    if n_unanswerable == 0:
        empty_result_rate = None
    else:
        empty_count = sum(1 for q in unanswerable if q.get("returned_count", 0) == 0)
        empty_result_rate = empty_count / n_unanswerable

    return {
        "evidence_recall": evidence_recall,
        "hit": hit,
        "mrr": mrr,
        "answerable_count": n_answerable,
        "unanswerable_count": n_unanswerable,
        "empty_result_rate": empty_result_rate,
    }
