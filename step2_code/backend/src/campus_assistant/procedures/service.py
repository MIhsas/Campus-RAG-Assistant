"""Procedure draft and verification service (T016).

Each template step binds exact citations (document_id / block_id / char span
/ quote / document sha256) taken verbatim from parsed corpus text. Draft
building reuses the T011 applicability filters for source admission and
checks every citation against the CURRENT parsed corpus:

- required-citation failure (source excluded by filters / missing / hash
  changed / span mismatch) makes the draft NOT saveable — the guide is never
  presented as a complete, saveable list in that case;
- optional-citation failure degrades that step's information to
  "资料未说明，请向办理部门核实" instead of inventing content;
- filters are never relaxed.

This is a fixed source-verifiable workflow: no retrieval ranking and no
model calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from campus_assistant.retrieval.filters import (
    FILTER_FIELDS,
    compute_allowed_document_ids,
)

TEMPLATE_SCHEMA_VERSION = "1.0"
UNSPECIFIED_FALLBACK = "资料未说明，请向办理部门核实。"

CITATION_STATUSES = ("ok", "source_missing", "hash_changed", "span_mismatch", "source_excluded")

_CITATION_REASON = {
    "source_missing": "来源文档或原文块在当前语料中缺失",
    "hash_changed": "来源文档内容哈希已变化（与模板绑定版本不一致）",
    "span_mismatch": "引用跨度与当前原文不一致",
    "source_excluded": "来源不符合当前筛选条件（不放宽筛选）",
}


def load_procedures(path: Path) -> dict[str, Any]:
    """Load and minimally validate a procedures template file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != TEMPLATE_SCHEMA_VERSION:
        raise ValueError("procedures 模板 schema_version 必须是 1.0")
    procedures = data.get("procedures")
    if not isinstance(procedures, list) or not procedures:
        raise ValueError("procedures 模板缺少事项列表")
    seen: set[str] = set()
    for p in procedures:
        pid = p.get("procedure_id")
        if not isinstance(pid, str) or not pid or pid in seen:
            raise ValueError("procedure_id 缺失或重复")
        seen.add(pid)
        if not isinstance(p.get("template_version"), str) or not p.get("template_version"):
            raise ValueError(f"{pid} 缺少 template_version")
        steps = p.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ValueError(f"{pid} 缺少步骤")
        for s in steps:
            if not isinstance(s.get("step_id"), str) or not s.get("step_id"):
                raise ValueError(f"{pid} 步骤缺少 step_id")
            for c in s.get("citations", []):
                for key in ("document_id", "document_sha256", "block_id", "char_start", "char_end", "quote"):
                    if key not in c:
                        raise ValueError(f"{pid}/{s['step_id']} 引用缺少 {key}")
    return data


def _preview_url(document_id: str, block_id: str) -> str:
    return f"/preview#{quote(document_id, safe='')}/{quote(block_id, safe='')}"


def _check_citation(
    citation: dict[str, Any],
    documents_by_id: dict[str, dict[str, Any]],
    blocks_by_doc: dict[str, dict[str, dict[str, Any]]],
    allowed: set[str] | None,
) -> str:
    """Return 'ok' or one of the failure statuses (existence/hash/span/filters)."""
    doc_id = citation.get("document_id", "")
    doc = documents_by_id.get(doc_id)
    if doc is None:
        return "source_missing"
    meta = doc.get("metadata") or {}
    if meta.get("sha256") != citation.get("document_sha256"):
        return "hash_changed"
    block = blocks_by_doc.get(doc_id, {}).get(citation.get("block_id", ""))
    if block is None:
        return "source_missing"
    start, end = citation.get("char_start", -1), citation.get("char_end", -1)
    text = block.get("text", "")
    if not (0 <= start < end <= len(text)) or text[start:end] != citation.get("quote"):
        return "span_mismatch"
    if allowed is not None and doc_id not in allowed:
        return "source_excluded"
    return "ok"


def _index_documents(documents: list[dict[str, Any]]):
    by_id = {d.get("document_id"): d for d in documents}
    blocks: dict[str, dict[str, dict[str, Any]]] = {}
    for d in documents:
        blocks[d.get("document_id")] = {b.get("block_id"): b for b in d.get("blocks", [])}
    return by_id, blocks


def build_draft(
    procedures: dict[str, Any],
    procedure_id: str,
    filters_norm: dict[str, Any] | None,
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a citation-checked draft for one procedure.

    Returns status 'ready' (saveable) only when every required citation
    passes against the CURRENT corpus under the requested filters.
    """
    proc = next((p for p in procedures["procedures"] if p["procedure_id"] == procedure_id), None)
    if proc is None:
        raise KeyError(procedure_id)

    filter_result = compute_allowed_document_ids(documents, filters_norm)
    allowed = filter_result["allowed_document_ids"]
    documents_by_id, blocks_by_doc = _index_documents(documents)

    steps_out = []
    issues: list[str] = []
    saveable = True

    for step in proc.get("steps", []):
        citations_out = []
        step_failed = False
        step_degraded = False
        for c in step.get("citations", []):
            status = _check_citation(c, documents_by_id, blocks_by_doc, allowed)
            usable = status == "ok"
            doc_meta = ((documents_by_id.get(c["document_id"]) or {}).get("metadata") or {})
            item = {
                "required": bool(c.get("required", True)),
                "usable": usable,
                "status": status,
                "document_id": c["document_id"],
                "block_id": c["block_id"],
                "char_start": c["char_start"],
                "char_end": c["char_end"],
                # 原文内容只在核对通过时作为可用依据给出；被筛除/失效的
                # 引用仅保留状态与来源标识供诊断，不携带原文要求。
                "quote": c["quote"] if usable else None,
                "document_sha256": c["document_sha256"],
                "preview_url": _preview_url(c["document_id"], c["block_id"]),
                "document_title": doc_meta.get("title"),
                "version_label": doc_meta.get("version_label"),
                "scope": doc_meta.get("scope"),
                "effective_from": doc_meta.get("effective_from"),
                "effective_to": doc_meta.get("effective_to"),
                "is_synthetic": doc_meta.get("is_synthetic", False),
                "note": None if usable else _CITATION_REASON[status],
            }
            citations_out.append(item)
            if not usable:
                if item["required"]:
                    step_failed = True
                    saveable = False
                    issues.append(
                        f"步骤「{step.get('title')}」：{_CITATION_REASON[status]}"
                        f"（{c['document_id']}/{c['block_id']}）"
                    )
                else:
                    step_degraded = True

        steps_out.append({
            "step_id": step.get("step_id"),
            "title": step.get("title"),
            # 步骤必要依据失效时不再展示具体办理要求（未经当前依据支持）
            "detail": None if step_failed else step.get("detail"),
            "citations": citations_out,
            "unspecified": list(step.get("unspecified", [])),
            "status": "failed" if step_failed else ("degraded" if step_degraded else "ok"),
            "fallback": (
                UNSPECIFIED_FALLBACK
                if step_failed or step_degraded
                else None
            ),
        })

    return {
        "procedure_id": proc["procedure_id"],
        "title": proc.get("title"),
        "summary": proc.get("summary"),
        "template_version": proc["template_version"],
        "is_synthetic": bool(proc.get("is_synthetic", procedures.get("is_synthetic", False))),
        "filters": filters_norm or {f: None for f in FILTER_FIELDS},
        "filter_summary": {
            "active": filter_result["active"],
            "allowed_count": filter_result["allowed_count"],
            "counting_rules": filter_result["counting_rules"],
        },
        "steps": steps_out,
        "saveable": saveable,
        "status": "ready" if saveable else "insufficient",
        "issues": issues,
        "disclaimer": "合成演示清单，不代表学校受理或资格认证；政策步骤来自原文引用，缺失信息不编造。",
    }


def verify_snapshot(
    procedures: dict[str, Any],
    procedure_id: str,
    snapshot: dict[str, Any],
    documents: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare a saved list's basis against the current template + corpus.

    Never touches user progress: returns a verdict only.
    'unchanged' | 'changed' | 'unavailable'
    """
    proc = next((p for p in procedures["procedures"] if p["procedure_id"] == procedure_id), None)
    if proc is None:
        return {"status": "unavailable", "issues": ["模板中已无此事项"], "current_template_version": None}

    issues: list[str] = []
    saved_version = snapshot.get("template_version")
    if saved_version != proc["template_version"]:
        issues.append(
            f"模板版本已变化（保存时 {saved_version}，当前 {proc['template_version']}）"
        )

    filters_norm = snapshot.get("filters")
    filter_result = compute_allowed_document_ids(documents, filters_norm)
    allowed = filter_result["allowed_document_ids"]
    documents_by_id, blocks_by_doc = _index_documents(documents)

    try:
        saved_steps = snapshot.get("steps") or []
        for s in saved_steps:
            for c in s.get("citations", []):
                # 快照只含保存时实际采用的引用（可选引用一经采用同样跟踪）；
                # required 决定缺资料能否生成草稿，不代表可免于核查。
                status = _check_citation(c, documents_by_id, blocks_by_doc, allowed)
                if status != "ok":
                    issues.append(
                        f"步骤「{s.get('title')}」依据变化：{_CITATION_REASON[status]}"
                        f"（{c.get('document_id')}/{c.get('block_id')}）"
                    )
    except Exception as e:
        return {"status": "unavailable", "issues": [f"无法解析保存的依据快照：{type(e).__name__}"], "current_template_version": proc["template_version"]}

    return {
        "status": "changed" if issues else "unchanged",
        "issues": issues,
        "current_template_version": proc["template_version"],
    }
