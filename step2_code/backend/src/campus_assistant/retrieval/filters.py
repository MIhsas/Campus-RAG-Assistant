"""Applicability filters for document admission (T011).

Lightweight predicate over parsed document metadata — not a rule platform.

口径（counting rules）：
- 统计对象是文档，不是 chunk 或命中条目。
- 每份被排除文档只计入一个原因，优先级：scope_unknown → scope_mismatch
  → date_unknown_from → not_yet_effective → expired。各原因计数互斥。
- scope 空数组表示未知；被筛维度为未知时排除，不解释为适用所有人。
- 日期区间两端包含；effective_to=null 表示未标注截止，不证明永久有效；
  effective_from=null 时无法确认适用日期，被日期筛选时排除。
- 未提供任何筛选字段时 allowed_document_ids 为 None（不限制），
  与筛选后空集合（无任何文档通过）语义不同。
"""

from __future__ import annotations

from typing import Any

FILTER_FIELDS = ("campus", "student_type", "admission_year", "as_of_date")

EXCLUDE_REASONS = (
    "scope_unknown",
    "scope_mismatch",
    "date_unknown_from",
    "not_yet_effective",
    "expired",
)

COUNTING_RULES = (
    "统计对象为文档；每份被排除文档只计入首个命中原因，优先级为 "
    "scope_unknown（被筛维度未标注）→ scope_mismatch（被筛维度不匹配）→ "
    "date_unknown_from（effective_from 未标注）→ not_yet_effective（查询日早于生效日）→ "
    "expired（查询日晚于失效日）；各原因计数互斥，之和等于被排除文档数。"
)


def empty_normalized_filters() -> dict[str, Any]:
    """All fields None = no restriction."""
    return {f: None for f in FILTER_FIELDS}


def is_active(filters: dict[str, Any] | None) -> bool:
    if not filters:
        return False
    return any(filters.get(f) is not None for f in FILTER_FIELDS)


def extract_filter_options(documents: list[dict[str, Any]]) -> dict[str, list]:
    """Extract deduplicated filter options from parsed documents for UI."""
    campus: set[str] = set()
    student_type: set[str] = set()
    admission_years: set[int] = set()
    for doc in documents or []:
        scope = (doc.get("metadata") or {}).get("scope") or {}
        campus.update(scope.get("campus") or [])
        student_type.update(scope.get("student_type") or [])
        admission_years.update(scope.get("admission_years") or [])
    return {
        "campus": sorted(campus),
        "student_type": sorted(student_type),
        "admission_year": sorted(admission_years),
    }


def _scope_reason(meta: dict[str, Any], filters: dict[str, Any]) -> str | None:
    """Return exclusion reason for scope dimensions, or None if admitted.

    Unknown (empty array) in any filtered dimension wins over mismatch,
    matching the documented reason precedence.
    """
    scope = meta.get("scope") or {}
    checks = (
        ("campus", "campus"),
        ("student_type", "student_type"),
        ("admission_year", "admission_years"),
    )
    unknown = False
    mismatch = False
    for field, key in checks:
        want = filters.get(field)
        if want is None:
            continue
        values = scope.get(key) or []
        if not values:
            unknown = True
        elif want not in values:
            mismatch = True
    if unknown:
        return "scope_unknown"
    if mismatch:
        return "scope_mismatch"
    return None


def _date_reason(meta: dict[str, Any], as_of_date: str) -> str | None:
    """Return exclusion reason for date checks, or None if admitted.

    Inclusive interval: effective_from <= as_of_date <= effective_to.
    published_at never substitutes effective_from.
    """
    eff_from = meta.get("effective_from")
    eff_to = meta.get("effective_to")
    if eff_from is None:
        return "date_unknown_from"
    if eff_from > as_of_date:
        return "not_yet_effective"
    if eff_to is not None and as_of_date > eff_to:
        return "expired"
    return None


def compute_allowed_document_ids(
    documents: list[dict[str, Any]],
    filters: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compute the admitted document_id set and exclusion accounting.

    Args:
        documents: Parsed documents (document_id + metadata).
        filters: Normalized filters dict (FILTER_FIELDS → value|None).

    Returns:
        {
          "active": bool,
          "allowed_document_ids": set[str] | None,  # None = unrestricted
          "document_total": int,
          "allowed_count": int,
          "excluded_counts": {reason: int},         # mutually exclusive
          "counting_rules": str,
          "notes": [str],
        }
    """
    documents = documents or []
    active = is_active(filters)
    excluded_counts = {r: 0 for r in EXCLUDE_REASONS}
    allowed: set[str] = set()
    no_end_date = 0

    if not active:
        return {
            "active": False,
            "allowed_document_ids": None,
            "document_total": len(documents),
            "allowed_count": len(documents),
            "excluded_counts": excluded_counts,
            "counting_rules": COUNTING_RULES,
            "notes": [],
        }

    filters = filters or empty_normalized_filters()
    as_of_date = filters.get("as_of_date")

    for doc in documents:
        meta = doc.get("metadata") or {}
        doc_id = doc.get("document_id", "")
        reason = _scope_reason(meta, filters)
        if reason is None and as_of_date is not None:
            reason = _date_reason(meta, as_of_date)
        if reason is not None:
            excluded_counts[reason] += 1
            continue
        allowed.add(doc_id)
        if as_of_date is not None and meta.get("effective_to") is None:
            no_end_date += 1

    notes: list[str] = []
    if as_of_date is not None and no_end_date > 0:
        notes.append(
            f"{no_end_date} 份适用文档未标注截止日期（effective_to=null），"
            "不证明永久有效。"
        )

    return {
        "active": True,
        "allowed_document_ids": allowed,
        "document_total": len(documents),
        "allowed_count": len(allowed),
        "excluded_counts": excluded_counts,
        "counting_rules": COUNTING_RULES,
        "notes": notes,
    }
