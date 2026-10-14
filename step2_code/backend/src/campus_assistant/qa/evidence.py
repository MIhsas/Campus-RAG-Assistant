"""Evidence pack construction (T012).

Turns ranked retrieval hits into request-scoped evidence items:

- evidence_id E1, E2, … assigned in rank order over deduplicated chunks.
  IDs are valid only within one request and must never be reused across
  requests for unrelated material.
- Excerpts are exact chunk text — half-open char spans stay consistent
  with the original; nothing is rewritten or stitched into a fake span.
- Character budget (NOT a token budget): whole item in or whole item out,
  with skipped_items counted. An included item is sent in full — a budget
  exclusion must never let citations claim support over unsent text, and
  no summary is fabricated for overlong items.
- evidence_state distinguishes budget_empty from no retrieval hits and
  from no admissible documents.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MAX_ITEMS = 5
DEFAULT_MAX_TOTAL_CHARS = 6000


def build_evidence_pack(
    hits: list[dict[str, Any]],
    *,
    filter_summary: dict[str, Any] | None = None,
    source_selection: dict[str, Any] | None = None,
    max_items: int = DEFAULT_MAX_ITEMS,
    max_total_chars: int = DEFAULT_MAX_TOTAL_CHARS,
) -> dict[str, Any]:
    """Build the evidence pack from formatted hits.

    Args:
        hits: Formatted hits from retrieval.service.execute_search.
        filter_summary: The request's filter_summary (for empty-state split).
        source_selection: T031 source-selection summary; when the selected
            file is excluded by the applicability conditions the empty state
            is "no_admissible_docs" (no admissible material), not "no_hits"
            (searched and found nothing inside an admitted file).
        max_items / max_total_chars: context budget; whole items only.

    Returns:
        {"evidence": [...], "budget": {...}, "evidence_state": str}
    """
    evidence: list[dict[str, Any]] = []
    seen_chunks: set[str] = set()
    skipped_items = 0
    used_chars = 0
    dup_chunks = 0

    for hit in hits:
        chunk = hit.get("chunk", {})
        chunk_id = chunk.get("chunk_id", "")
        if chunk_id in seen_chunks:
            dup_chunks += 1
            continue
        seen_chunks.add(chunk_id)

        text = chunk.get("text", "")
        item_fits = (
            len(evidence) < max_items
            and used_chars + len(text) <= max_total_chars
        )
        if not item_fits:
            skipped_items += 1
            continue

        meta = chunk.get("metadata") or {}
        used_chars += len(text)
        evidence.append({
            "evidence_id": f"E{len(evidence) + 1}",
            "text": text,
            "document_id": chunk.get("document_id", ""),
            "block_id": chunk.get("block_id", ""),
            "chunk_id": chunk_id,
            "char_start": chunk.get("char_start", 0),
            "char_end": chunk.get("char_end", 0),
            "document_sha256": meta.get("sha256"),
            "title": meta.get("title"),
            "source_url": meta.get("source_url"),
            "version_label": meta.get("version_label"),
            "scope": meta.get("scope"),
            "published_at": meta.get("published_at"),
            "effective_from": meta.get("effective_from"),
            "effective_to": meta.get("effective_to"),
            "is_synthetic": meta.get("is_synthetic", False),
            "locator": chunk.get("locator"),
            "preview_url": hit.get("preview_url", ""),
            # T043：仅学生类型未标注的参考证据携带状态；普通证据为 None（旧协议）
            "student_type_status": hit.get("student_type_status"),
        })

    budget = {
        "max_items": max_items,
        "max_total_chars": max_total_chars,
        "included_items": len(evidence),
        "included_chars": used_chars,
        "skipped_items": skipped_items,
        "duplicate_chunks": dup_chunks,
    }

    if evidence:
        state = "ok"
    elif skipped_items > 0:
        state = "budget_empty"
    else:
        ss = source_selection or {}
        selected = bool(ss.get("selected"))
        selected_excluded = selected and not ss.get("is_admitted", False)
        fs = filter_summary or {}
        if selected_excluded:
            state = "no_admissible_docs"
        elif selected and ss.get("allowed_after_selection", 0) == 0:
            state = "no_admissible_docs"
        elif fs.get("active") and fs.get("allowed_count", 0) == 0:
            state = "no_admissible_docs"
        else:
            state = "no_hits"

    return {"evidence": evidence, "budget": budget, "evidence_state": state}
