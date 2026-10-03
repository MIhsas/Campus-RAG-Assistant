"""Deterministic self-check evaluation service (T019).

The rule configuration binds every item to exact original-text citations
(document/block/span/quote/sha256) with a rule version, and is explicitly
injected at app creation — ordinary services never auto-enable it.

Judgment is pure deterministic mapping of the user's three-state answers
(yes / no / unknown):
- unknown is NEVER counted as satisfied;
- any explicit "no"  →  summary "存在未满足项";
- no "no" but unknown →  "仍有待核实项";
- all "yes"           →  "按自填信息满足本演示列出的条件"（仍需学校审核）；
- any citation failing admission/span/hash checks →
  "依据不足，无法完成自查"（不利用失效原文算通过）。

Citation admission reuses the T011 filter logic and the procedures
citation checker — no second copy of admission rules. User answers are
processed only within the request; nothing is persisted.
"""

from __future__ import annotations

from typing import Any

from campus_assistant.procedures.service import (
    _check_citation,
    _index_documents,
    _preview_url,
)
from campus_assistant.retrieval.filters import (
    FILTER_FIELDS,
    compute_allowed_document_ids,
)

RULE_SCHEMA_VERSION = "1.0"
ANSWER_VALUES = ("yes", "no", "unknown")

ITEM_STATUS = {
    "yes": "satisfied",
    "no": "unsatisfied",
    "unknown": "unknown",
}

SUMMARY_TEXT = {
    "all_satisfied": "按自填信息满足本演示列出的条件；仍需学校审核，不构成录取、批准或申请成功。",
    "has_unsatisfied": "存在未满足项（依据自填信息与合成演示规则）。",
    "has_unknown": "仍有待核实项：存在不确定/未填写的必要条件，不能按满足处理。",
    "insufficient_basis": "依据不足，无法完成自查（规则原文未通过准入或缺失/内容变化）。",
}

DISCLAIMER = (
    "个人自查演示（合成资料、确定性规则）：不代表学校审核结果，不受理申请；"
    "不收集姓名、学号或违纪详情；填报内容仅在本次请求内处理，不保存。"
)


def load_rule(path) -> dict[str, Any]:
    """Load and minimally validate the rule configuration."""
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != RULE_SCHEMA_VERSION:
        raise ValueError("self-check 规则 schema_version 必须是 1.0")
    if not data.get("rule_id") or not data.get("rule_version"):
        raise ValueError("self-check 规则缺少 rule_id/rule_version")
    citations = data.get("citations")
    if not isinstance(citations, list) or not citations:
        raise ValueError("self-check 规则缺少 citations")
    for c in citations:
        for key in ("document_id", "document_sha256", "block_id", "char_start", "char_end", "quote"):
            if key not in c:
                raise ValueError(f"规则引用缺少 {key}")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("self-check 规则缺少 items")
    seen: set[str] = set()
    for it in items:
        iid = it.get("item_id")
        if not iid or iid in seen:
            raise ValueError("规则 item_id 缺失或重复")
        seen.add(iid)
        if it.get("satisfied_when") != "yes":
            raise ValueError(f"{iid} 的 satisfied_when 必须是 yes（肯否方向与原文一致）")
        idx = it.get("citation_index")
        if not isinstance(idx, int) or not (0 <= idx < len(citations)):
            raise ValueError(f"{iid} 的 citation_index 无效")
    return data


def evaluate_self_check(
    rule: dict[str, Any],
    answers: dict[str, Any],
    filters_norm: dict[str, Any] | None,
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate the four three-state answers deterministically."""
    filter_result = compute_allowed_document_ids(documents, filters_norm)
    allowed = filter_result["allowed_document_ids"]
    documents_by_id, blocks_by_doc = _index_documents(documents)

    # 引用核查（复用 procedures 的核查逻辑与 T011 准入）
    basis_citations = []
    basis_ok = True
    for c in rule.get("citations", []):
        status = _check_citation(c, documents_by_id, blocks_by_doc, allowed)
        usable = status == "ok"
        if not usable:
            basis_ok = False
        meta = ((documents_by_id.get(c["document_id"]) or {}).get("metadata") or {})
        basis_citations.append({
            "usable": usable,
            "status": status,
            "document_id": c["document_id"],
            "block_id": c["block_id"],
            "char_start": c["char_start"],
            "char_end": c["char_end"],
            # 失效引用不携带原文（与 T016-R1 一致）
            "quote": c["quote"] if usable else None,
            "document_sha256": c["document_sha256"],
            "preview_url": _preview_url(c["document_id"], c["block_id"]),
            "document_title": meta.get("title"),
            "note": None if usable else {
                "source_missing": "来源文档或原文块在当前语料中缺失",
                "hash_changed": "来源文档内容哈希已变化",
                "span_mismatch": "引用跨度与当前原文不一致",
                "source_excluded": "来源不符合当前筛选条件（不放宽筛选）",
            }.get(status, "未通过核对"),
        })

    items_out = []
    has_unsatisfied = False
    has_unknown = False
    for it in rule.get("items", []):
        raw = (answers or {}).get(it["answer_field"])
        answer = raw if raw in ANSWER_VALUES else "unknown"
        if not basis_ok:
            items_out.append({
                "item_id": it["item_id"],
                "title": it["title"],
                "question": it["question"],
                "answer": answer,
                "status": "basis_unavailable",
                "explanation": "依据不足，本项不参与判断（不利用失效原文算通过）。",
                "citation": basis_citations[it["citation_index"]],
            })
            continue
        status = ITEM_STATUS[answer]
        if status == "unsatisfied":
            has_unsatisfied = True
        elif status == "unknown":
            has_unknown = True
        explanation = it["explanation"]
        if answer == "unknown":
            # T019-R1：未知＝用户尚未确认（原文已明确条件），不用“资料未说明”
            explanation += "您尚未确认该项，请核实个人情况（未知不计为满足）。"
        items_out.append({
            "item_id": it["item_id"],
            "title": it["title"],
            "question": it["question"],
            "answer": answer,
            "status": status,
            "explanation": explanation,
            "citation": basis_citations[it["citation_index"]],
        })

    if not basis_ok:
        summary_status = "insufficient_basis"
    elif has_unsatisfied:
        summary_status = "has_unsatisfied"
    elif has_unknown:
        summary_status = "has_unknown"
    else:
        summary_status = "all_satisfied"

    return {
        "rule_id": rule["rule_id"],
        "rule_version": rule["rule_version"],
        "rule_title": rule.get("title"),
        "is_synthetic": bool(rule.get("is_synthetic", True)),
        "filters": filters_norm or {f: None for f in FILTER_FIELDS},
        "filter_summary": {
            "active": filter_result["active"],
            "allowed_count": filter_result["allowed_count"],
            "counting_rules": filter_result["counting_rules"],
        },
        "basis": {
            "status": "ok" if basis_ok else "insufficient",
            "citations": basis_citations,
        },
        "answers": {
            it["answer_field"]: (answers or {}).get(it["answer_field"])
            for it in rule.get("items", [])
        },
        "items": items_out,
        "summary_status": summary_status,
        "summary_text": SUMMARY_TEXT[summary_status],
        "not_collected": list(rule.get("not_collected", [])),
        "disclaimer": DISCLAIMER,
    }
