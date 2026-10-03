"""Shared retrieval pipeline for /search and /ask (T012).

One implementation of mode dispatch + T011 applicability filters + hit
formatting, so routes never call each other over HTTP or duplicate the
filter logic. Reuses the indexes built at app creation — never re-parses,
re-chunks or re-encodes documents. Ranking and hit fields are identical
to the /search contract (T011): admission before truncation, None/empty-set
semantics, stable ordering, preview_url from server-side mapping.
"""

from __future__ import annotations

from typing import Any

FILTER_SUMMARY_KEYS = (
    "active",
    "document_total",
    "allowed_count",
    "excluded_counts",
    "counting_rules",
    "notes",
)


def format_hit(h: dict) -> dict:
    """Format a raw hit dict for API responses."""
    return {
        "rank": h.get("rank", 0),
        "score": h.get("score", 0.0),
        "chunk": h.get("chunk", {}),
        "preview_url": h.get("preview_url", ""),
        "matched_terms": h.get("matched_terms", []),
        "bm25_rank": h.get("bm25_rank"),
        "dense_rank": h.get("dense_rank"),
        "bm25_score": h.get("bm25_score"),
        "dense_score": h.get("dense_score"),
    }


def execute_search(
    *,
    query: str,
    mode: str,
    top_k: int,
    filters_norm: dict[str, Any] | None,
    documents: list[dict[str, Any]],
    bm25_index: Any,
    dense_index: Any,
    embedding_service: Any,
) -> dict[str, Any]:
    """Run the shared retrieval pipeline.

    Args:
        query: Query text.
        mode: "bm25" | "dense" | "hybrid".
        top_k: Maximum hits (caller validates range).
        filters_norm: Normalized T011 filters (or None = unrestricted).
        documents: Parsed documents for applicability filtering.
        bm25_index / dense_index / embedding_service: Built at app creation.

    Returns:
        {"query_tokens": [...], "hits": [...], "filter_summary": {...}}
    """
    from campus_assistant.retrieval.filters import compute_allowed_document_ids
    from campus_assistant.retrieval.tokenize import tokenize

    query_tokens = tokenize(query)
    filter_result = compute_allowed_document_ids(documents, filters_norm)
    allowed = filter_result["allowed_document_ids"]
    filter_summary = {k: filter_result[k] for k in FILTER_SUMMARY_KEYS}

    # Admission is applied inside each retriever BEFORE Top-K truncation;
    # an empty allowed set returns empty hits and never falls back to
    # excluded documents.
    hits = []
    if allowed is None or len(allowed) > 0:
        if mode == "bm25":
            if bm25_index:
                hits_raw = bm25_index.search(
                    query, top_k=top_k, allowed_document_ids=allowed
                )
                hits = [format_hit(h) for h in hits_raw]

        elif mode == "dense":
            if embedding_service and dense_index:
                q_emb = embedding_service.encode_query(query)
                hits_raw = dense_index.search(
                    q_emb, top_k=top_k, allowed_document_ids=allowed
                )
                hits = [format_hit(h) for h in hits_raw]

        elif mode == "hybrid":
            if bm25_index and embedding_service and dense_index:
                from campus_assistant.retrieval.hybrid import rrf_fusion

                # Each path takes its Top-20 from the admitted set only;
                # ranks restart at 1 within that set before RRF.
                bm25_hits = bm25_index.search(
                    query, top_k=20, allowed_document_ids=allowed
                )
                q_emb = embedding_service.encode_query(query)
                dense_hits = dense_index.search(
                    q_emb, top_k=20, allowed_document_ids=allowed
                )
                fused = rrf_fusion(bm25_hits, dense_hits, top_k=top_k)
                hits = [format_hit(h) for h in fused]

    return {
        "query_tokens": query_tokens,
        "hits": hits,
        "filter_summary": filter_summary,
    }
