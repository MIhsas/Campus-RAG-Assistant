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
    "include_unknown_student_type",
    "unknown_student_type_document_ids",
    "confirmed_count",
    "reference_count",
)

# T043：学生类型未标注资料以参考纳入时的固定状态说明（搜索/证据/复制/消息一致）
UNKNOWN_STUDENT_TYPE_STATUS = "学生类型未标注，适用范围尚未核实"
CONFIRMED_STUDENT_TYPE_STATUS = "学生类型已匹配"


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



def _search_mode(
    mode: str,
    query: str,
    top_k: int,
    allowed: set[str] | None,
    bm25_index: Any,
    dense_index: Any,
    embedding_service: Any,
) -> list[dict]:
    """Shared mode dispatch used by strict search AND T038 candidates.

    Admission sets are decided by the caller and applied inside each
    retriever BEFORE Top-K truncation. Ranking/indexes/query encoding are
    shared — documents are never re-indexed per call.
    """
    hits: list[dict] = []
    if allowed is not None and len(allowed) == 0:
        return hits
    if mode == "bm25":
        if bm25_index:
            hits = [format_hit(h) for h in bm25_index.search(
                query, top_k=top_k, allowed_document_ids=allowed)]
    elif mode == "dense":
        if embedding_service and dense_index:
            q_emb = embedding_service.encode_query(query)
            hits = [format_hit(h) for h in dense_index.search(
                q_emb, top_k=top_k, allowed_document_ids=allowed)]
    elif mode == "hybrid":
        if bm25_index and embedding_service and dense_index:
            from campus_assistant.retrieval.hybrid import rrf_fusion

            # Each path takes its Top-20 from the admitted set only;
            # ranks restart at 1 within that set before RRF.
            bm25_hits = bm25_index.search(query, top_k=20, allowed_document_ids=allowed)
            q_emb = embedding_service.encode_query(query)
            dense_hits = dense_index.search(q_emb, top_k=20, allowed_document_ids=allowed)
            fused = rrf_fusion(bm25_hits, dense_hits, top_k=top_k)
            hits = [format_hit(h) for h in fused]
    return hits


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
    document_id: str | None = None,
    include_unknown_student_type: bool = False,
) -> dict[str, Any]:
    """Run the shared retrieval pipeline.

    Args:
        query: Query text.
        mode: "bm25" | "dense" | "hybrid".
        top_k: Maximum hits (caller validates range).
        filters_norm: Normalized T011 filters (or None = unrestricted).
        documents: Parsed documents for applicability filtering.
        bm25_index / dense_index / embedding_service: Built at app creation.
        document_id: Optional user-selected single source document (T031).
            None = previous behaviour. Intersected with the filter-admitted
            set BEFORE Top-K; never relaxes filters or falls back to other
            documents when the intersection is empty.
        include_unknown_student_type: T043 参考准入开关（默认 False=strict；
            正式 search/ask 显式传 True）。仅 student_type 未标注资料可作为
            参考纳入并逐命中携带状态说明；已知冲突与其它维度检查不变。

    Returns:
        {"query_tokens": [...], "hits": [...], "filter_summary": {...},
         "source_selection": {...}}
    """
    from campus_assistant.retrieval.filters import compute_allowed_document_ids
    from campus_assistant.retrieval.source_selection import (
        build_source_selection,
        intersect_allowed,
    )
    from campus_assistant.retrieval.tokenize import tokenize

    query_tokens = tokenize(query)
    filter_result = compute_allowed_document_ids(
        documents, filters_norm,
        include_unknown_student_type=include_unknown_student_type,
    )
    allowed_by_filters = filter_result["allowed_document_ids"]
    filter_summary = {k: filter_result[k] for k in FILTER_SUMMARY_KEYS}
    # 集合 → 可序列化列表（统计分列；不冒充适用性已确认）
    filter_summary["unknown_student_type_document_ids"] = sorted(
        filter_result.get("unknown_student_type_document_ids") or []
    )
    reference_ids = filter_result.get("unknown_student_type_document_ids") or set()

    # T031: user-selected source ∩ four-condition admission, before Top-K.
    allowed = intersect_allowed(allowed_by_filters, document_id)
    source_selection = build_source_selection(
        document_id=document_id,
        documents=documents,
        allowed_document_ids=allowed_by_filters,
    )

    # Admission is applied inside each retriever BEFORE Top-K truncation;
    # an empty allowed set returns empty hits and never falls back to
    # excluded documents (including when the selected file is excluded).
    hits = _search_mode(mode, query, top_k, allowed, bm25_index, dense_index, embedding_service)

    # T043：仅参考纳入的未知命中携带固定未核实说明；普通命中继续旧协议（无新状态字段）
    for h in hits:
        doc_id = (h.get("chunk") or {}).get("document_id", "")
        if doc_id in reference_ids:
            h["student_type_status"] = UNKNOWN_STUDENT_TYPE_STATUS

    return {
        "query_tokens": query_tokens,
        "hits": hits,
        "filter_summary": filter_summary,
        "source_selection": source_selection,
    }


CANDIDATE_DISCLAIMER = (
    "未通过所选日期或学生类型条件核实，仅供原文核对，不作为已确认适用的答案依据"
)


def execute_candidates(
    *,
    query: str,
    mode: str,
    top_k: int,
    filters_norm: dict[str, Any] | None,
    document_id: str | None,
    uncertainty_dimensions: list[str],
    documents: list[dict[str, Any]],
    bm25_index: Any,
    dense_index: Any,
    embedding_service: Any,
    include_unknown_student_type: bool = False,
) -> dict[str, Any]:
    """T038: user-explicit uncertain-source candidate search (read-only).

    Shares the same retrievers/indexes/query encoding/ranking as strict
    search (see _search_mode); documents are never re-indexed. The candidate
    set is computed independently per document (filters.compute_candidate_
    document_ids) and excludes the admitted set. This path NEVER
    calls AnswerProvider/Planner/ASR, and its hits never enter ask evidence,
    generation messages, agent tools, item recommendations or saved templates.

    T043: `include_unknown_student_type` 与正式检索同模式——候选排除**本次
    模式实际已准入**的文档（含参考纳入者，不重复显示）；关闭该开关时保持
    T038 原 strict 候选（仅排除 strict 已准入集合）。
    """
    from campus_assistant.retrieval.filters import (
        compute_allowed_document_ids,
        compute_candidate_document_ids,
    )
    from campus_assistant.retrieval.source_selection import intersect_allowed

    if include_unknown_student_type:
        admitted = compute_allowed_document_ids(
            documents, filters_norm, include_unknown_student_type=True
        )["allowed_document_ids"]
        exclude_ids = admitted
    else:
        exclude_ids = None  # 原 strict 候选行为
    cand = compute_candidate_document_ids(
        documents, filters_norm, uncertainty_dimensions,
        exclude_document_ids=exclude_ids,
    )
    # 单文件 document_id 仍求交（不回退其他文件）；document_id=None 才是全部
    allowed = intersect_allowed(cand["candidate_document_ids"], document_id)
    cand_meta = {k: v for k, v in cand["candidates_by_doc"].items()
                 if allowed is None or k in allowed}
    # 候选准入先于各路 TopK；空候选直接返回（不找全库补齐）
    hits = _search_mode(mode, query, top_k, allowed, bm25_index, dense_index, embedding_service)
    for h in hits:
        doc_id = (h.get("chunk") or {}).get("document_id", "")
        info = cand_meta.get(doc_id, {})
        h["unknown_dimensions"] = info.get("unknown_dimensions", [])
        h["uncertainty_note"] = "未通过所选维度（" + "、".join(h["unknown_dimensions"]) + "）核实"
    return {
        "query_tokens": tokenize_query(query),
        "hits": hits,
        "uncertainty_dimensions": list(cand["requested_dimensions"]),
        "active_dimensions": list(cand["active_dimensions"]),
        "candidate_summary": {
            "document_total": cand["document_total"],
            "strict_allowed_count": cand["strict_allowed_count"],
            "candidate_document_count": len(allowed) if allowed is not None else cand["candidate_count"],
            "counting_rules": cand["counting_rules"],
        },
        "disclaimer": CANDIDATE_DISCLAIMER,
    }


def tokenize_query(query: str) -> list[str]:
    from campus_assistant.retrieval.tokenize import tokenize

    return tokenize(query)
