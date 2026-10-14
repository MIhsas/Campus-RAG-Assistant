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
    *,
    include_unknown_student_type: bool = False,
) -> dict[str, Any]:
    """Compute the admitted document_id set and exclusion accounting.

    Args:
        documents: Parsed documents (document_id + metadata).
        filters: Normalized filters dict (FILTER_FIELDS → value|None).
        include_unknown_student_type: T043 参考准入策略开关（**默认 False=
            旧 strict**，保护办事/自查/旧 evaluation 调用方）。为 True 且
            student_type 筛选生效时：仅 student_type 维度「未标注（空数组）」
            的文档可进入参考集合（标注为未核实参考）；**已知类型冲突仍排除**，
            campus/admission_year 未知或冲突、日期未知/未生效/失效等其它维度
            检查一律保持。仅影响 student_type 一个维度，不代表适用性已确认。

    Returns:
        {
          "active": bool,
          "allowed_document_ids": set[str] | None,  # None = unrestricted
          "document_total": int,
          "allowed_count": int,
          "excluded_counts": {reason: int},         # mutually exclusive（旧语义）
          "counting_rules": str,
          "notes": [str],
          "include_unknown_student_type": bool,
          "unknown_student_type_document_ids": set[str],  # 以参考纳入的文档
          "confirmed_count": int,                   # 学生类型已匹配
          "reference_count": int,                   # 学生类型未标注、作为参考
        }
    """
    documents = documents or []
    active = is_active(filters)
    excluded_counts = {r: 0 for r in EXCLUDE_REASONS}
    allowed: set[str] = set()
    unknown_type_ids: set[str] = set()
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
            "include_unknown_student_type": bool(include_unknown_student_type),
            "unknown_student_type_document_ids": set(),
            "confirmed_count": len(documents),
            "reference_count": 0,
        }

    filters = filters or empty_normalized_filters()
    as_of_date = filters.get("as_of_date")
    want_type = filters.get("student_type")
    # 参考准入仅在 student_type 筛选生效且显式开启时有意义；其余维度永不放宽
    admit_unknown_type = (
        bool(include_unknown_student_type) and want_type is not None
    )

    for doc in documents:
        meta = doc.get("metadata") or {}
        doc_id = doc.get("document_id", "")
        scope = meta.get("scope") or {}
        type_unknown = bool(want_type is not None and not (scope.get("student_type") or []))
        reason = _scope_reason(meta, filters)
        if (
            reason == "scope_unknown"
            and admit_unknown_type
            and type_unknown
            and _other_scope_dims_ok(meta, filters)
        ):
            # 仅 student_type 未标注且其余 scope 维度已通过 → 参考准入
            # （campus/admission_year 未知或冲突仍会在此被拦下，见 _other_scope_dims_ok）
            reason = None
            unknown_type_ids.add(doc_id)
        if reason is None and as_of_date is not None:
            reason = _date_reason(meta, as_of_date)
            if reason is not None and doc_id in unknown_type_ids:
                unknown_type_ids.discard(doc_id)
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
    if unknown_type_ids:
        notes.append(
            f"{len(unknown_type_ids)} 份学生类型未标注资料作为参考纳入"
            "（适用范围尚未核实，不代表适用性已确认）。"
        )

    return {
        "active": True,
        "allowed_document_ids": allowed,
        "document_total": len(documents),
        "allowed_count": len(allowed),
        "excluded_counts": excluded_counts,
        "counting_rules": COUNTING_RULES,
        "notes": notes,
        "include_unknown_student_type": bool(include_unknown_student_type),
        "unknown_student_type_document_ids": unknown_type_ids,
        "confirmed_count": len(allowed) - len(unknown_type_ids),
        "reference_count": len(unknown_type_ids),
    }


def _other_scope_dims_ok(meta: dict[str, Any], filters: dict[str, Any]) -> bool:
    """campus/admission_year 两维必须按旧规则通过（未知或冲突均不允许）。"""
    scope = meta.get("scope") or {}
    want_campus = filters.get("campus")
    if want_campus is not None:
        vals = scope.get("campus") or []
        if not vals or want_campus not in vals:
            return False
    want_year = filters.get("admission_year")
    if want_year is not None:
        vals = scope.get("admission_years") or []
        if not vals or want_year not in vals:
            return False
    return True


UNCERTAINTY_DIMENSIONS = ("date", "student_type")

CANDIDATE_RULES = (
    "候选=用户显式选择的不确定性维度上「实际未知」的资料，且逐文档独立复核其余条件："
    "已知 scope 不匹配、未选放宽维度的未知 scope、已知尚未生效/已失效均排除；"
    "campus/admission_year 严格保留；effective_from 未知但 effective_to 早于查询日同样排除；"
    "date+student_type 双未知须两项均由用户选中。候选集合排除严格已准入集合；"
    "不放宽任何已知冲突，不以排除原因优先级代替独立检查。"
)


class CandidateRequestError(ValueError):
    """Invalid candidate request (mapped to 422 by the API)."""

    def __init__(self, message: str, code: str = "UNCERTAINTY_DIMENSIONS_INVALID"):
        super().__init__(message)
        self.code = code


def compute_candidate_document_ids(
    documents: list[dict[str, Any]],
    filters: dict[str, Any] | None,
    uncertainty_dimensions: list[str],
    exclude_document_ids: set[str] | None = None,
) -> dict[str, Any]:
    """T038: independent, user-explicit uncertain-source candidate set.

    Strict admission semantics (compute_allowed_document_ids) are NOT changed.
    This function only answers: which documents are actually unknown on a
    dimension the user explicitly chose to inspect, while every other
    condition is re-checked independently per document (no reason-priority
    masking). Candidates never replace strict results.

    T043: `exclude_document_ids` 默认 None=排除旧 strict 已准入集合（原行为）；
    正式 search/ask 传入**本次模式的实际准入集合**（含参考纳入文档），使候选
    不重复显示已正式准入的文档——按本次结果 snapshot 模式求候选。
    """
    dims = uncertainty_dimensions or []
    if not isinstance(dims, list) or not dims:
        raise CandidateRequestError("uncertainty_dimensions 不能为空；仅接受 date、student_type")
    if any(d not in UNCERTAINTY_DIMENSIONS for d in dims):
        raise CandidateRequestError("uncertainty_dimensions 仅接受 date、student_type")
    if len(set(dims)) != len(dims):
        raise CandidateRequestError("uncertainty_dimensions 不得重复")
    filters = filters or empty_normalized_filters()
    active: list[str] = []
    if "date" in dims and filters.get("as_of_date"):
        active.append("date")
    if "student_type" in dims and filters.get("student_type"):
        active.append("student_type")
    if not active:
        raise CandidateRequestError(
            "所选不确定性维度均无对应筛选条件（date 需 as_of_date、student_type 需 student_type）——没有可放宽的未知维度"
        )

    if exclude_document_ids is None:
        strict = compute_allowed_document_ids(documents, filters)
        strict_ids = strict.get("allowed_document_ids")
        strict_allowed_count = strict.get("allowed_count")
    else:
        strict_ids = set(exclude_document_ids)
        strict_allowed_count = len(strict_ids)
    candidates: dict[str, dict] = {}
    checked = 0
    for doc in documents:
        meta = doc.get("metadata") or {}
        doc_id = doc.get("document_id", "")
        checked += 1
        if strict_ids is None or doc_id in strict_ids:
            continue  # 已严格准入的不是候选
        scope = meta.get("scope") or {}
        # —— 独立逐维复核（不用 excluded_reason 优先级）——
        skip = False
        # campus / admission_year：严格保留
        want_campus = filters.get("campus")
        if want_campus is not None:
            vals = scope.get("campus") or []
            if not vals or want_campus not in vals:
                skip = True
        want_year = filters.get("admission_year")
        if not skip and want_year is not None:
            vals = scope.get("admission_years") or []
            if not vals or want_year not in vals:
                skip = True
        unknown_dims: list[str] = []
        # student_type
        want_type = filters.get("student_type")
        if not skip and want_type is not None:
            vals = scope.get("student_type") or []
            if not vals:
                unknown_dims.append("student_type")
            elif want_type not in vals:
                skip = True  # 已知不匹配——已知冲突不可放宽
        # date
        as_of = filters.get("as_of_date")
        if not skip and as_of is not None:
            eff_to = meta.get("effective_to")
            if eff_to is not None and as_of > eff_to:
                skip = True  # 已失效（即使 effective_from 未知）
            if not skip:
                eff_from = meta.get("effective_from")
                if eff_from is None:
                    unknown_dims.append("date")
                elif as_of < eff_from:
                    skip = True  # 已知尚未生效
        if skip or not unknown_dims:
            continue
        # 实际未知维度必须全部由用户选中（双未知须两项都选）
        if not set(unknown_dims) <= set(active):
            continue
        candidates[doc_id] = {
            "unknown_dimensions": unknown_dims,
            "title": meta.get("title"),
            "version_label": meta.get("version_label"),
        }

    return {
        "active_dimensions": active,
        "requested_dimensions": list(dims),
        "candidate_document_ids": set(candidates),
        "candidates_by_doc": candidates,
        "document_total": len(documents),
        "strict_allowed_count": strict_allowed_count,
        "candidate_count": len(candidates),
        "counting_rules": CANDIDATE_RULES,
    }
