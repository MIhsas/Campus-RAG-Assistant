"""Deterministic policy version comparison service (T017).

Alignment (in order):
1. clauses sharing the same 第X条 identifier are paired first — inserting one
   clause never shifts later clauses into false "modified" pairs;
2. remaining unnumbered blocks are paired by order-preserving exact-text
   matching (LCS);
3. remaining unnumbered blocks are paired by order-preserving similarity
   (difflib ratio >= MODIFIED_SIMILARITY) as "modified";
4. anything left over is deleted (left) / added (right).

Modified entries carry character-level diff segments, but left/right texts
are always stored verbatim (full paragraph, never truncated).

Known limitations (documented, not solved here): only paragraph blocks are
compared (table blocks do not take part — table differences are NOT shown);
renumbering a clause is seen as delete+add of two different identifiers;
moving a clause across positions may pair it as added+deleted; for duplicate
identifiers within one document only the first occurrence takes part in
identifier pairing, later ones go straight to added/deleted (no text
matching).
"""

from __future__ import annotations

import difflib
import re
from typing import Any
from urllib.parse import quote

CLAUSE_KEY_PATTERN = re.compile(r"^(第[一二三四五六七八九十百千零〇两]+条)")
MODIFIED_SIMILARITY = 0.6

CHANGE_TYPES = ("added", "deleted", "modified", "unchanged")

ALGORITHM_NOTE = (
    "对齐顺序：① 第X条标识优先配对（新增条款不会使后续条款错位）；"
    "② 未编号正文按保持顺序的精确文本匹配；③ 未编号剩余按保持顺序的相似度配对为修改；"
    "④ 其余为新增/删除。"
)
LIMITATIONS = [
    "当前仅比较段落（paragraph）块，表格块不参与对比——不含表格差异；用于 DOCX 时请勿把未展示的表格变化当作无变化。",
    "条款重编号（如第三条改为第四条）会被识别为删除+新增两条，而不是同一条款的修改。",
    "条款跨位置移动可能被识别为删除+新增，而非移动。",
    "同一文档内重复的条款标识仅首个参与标识配对，其余同号条款直接归入新增/删除，不做正文匹配。",
    "文字差异不代表版本适用性；日期较新不等于现行有效。",
]


def _clause_key(text: str) -> str | None:
    m = CLAUSE_KEY_PATTERN.match(text.strip())
    return m.group(1) if m else None


def _block_ref(doc_id: str, sha256: str | None, block: dict[str, Any]) -> dict[str, Any]:
    block_id = block.get("block_id", "")
    text = block.get("text", "")
    # 解析块本身不带字符区间；对比单位即整块，跨度取块内全量 [0, len)
    return {
        "document_id": doc_id,
        "block_id": block_id,
        "char_start": 0,
        "char_end": len(text),
        "text": text,
        "kind": block.get("kind"),
        "document_sha256": sha256,
        "preview_url": f"/preview#{quote(doc_id, safe='')}/{quote(block_id, safe='')}",
    }


def _side_meta(doc: dict[str, Any]) -> dict[str, Any]:
    meta = doc.get("metadata") or {}
    return {
        "document_id": doc.get("document_id"),
        "policy_group_id": meta.get("policy_group_id"),
        "title": meta.get("title"),
        "version_label": meta.get("version_label"),
        "published_at": meta.get("published_at"),
        "effective_from": meta.get("effective_from"),
        "effective_to": meta.get("effective_to"),
        "scope": meta.get("scope"),
        "document_sha256": meta.get("sha256"),
        "is_synthetic": meta.get("is_synthetic", False),
        "source_url": meta.get("source_url"),
    }


def group_versions(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """List policy groups with their parsed versions (document order kept)."""
    groups: dict[str, list] = {}
    for doc in documents or []:
        meta = doc.get("metadata") or {}
        gid = meta.get("policy_group_id") or "(未标注)"
        groups.setdefault(gid, []).append({
            **_side_meta(doc),
            "block_count": len(doc.get("blocks", [])),
        })
    return [
        {"policy_group_id": gid, "versions": versions}
        for gid, versions in groups.items()
    ]


def _lcs_pairs(left_texts: list[str], right_texts: list[str]) -> list[tuple[int, int]]:
    """Order-preserving exact-text matching (LCS) over remaining blocks."""
    matcher = difflib.SequenceMatcher(None, left_texts, right_texts, autojunk=False)
    pairs = []
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            pairs.append((block.a + k, block.b + k))
    return pairs


def _diff_segments(left_text: str, right_text: str) -> list[dict[str, Any]]:
    """Character-level in-clause diff; full texts remain verbatim elsewhere."""
    segments = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, left_text, right_text, autojunk=False
    ).get_opcodes():
        if op == "equal":
            segments.append({"op": "equal", "text": left_text[i1:i2]})
        elif op == "delete":
            segments.append({"op": "delete", "text": left_text[i1:i2]})
        elif op == "insert":
            segments.append({"op": "insert", "text": right_text[j1:j2]})
        else:  # replace
            segments.append({"op": "delete", "text": left_text[i1:i2]})
            segments.append({"op": "insert", "text": right_text[j1:j2]})
    return segments


def compare_documents(left_doc: dict[str, Any], right_doc: dict[str, Any]) -> dict[str, Any]:
    """Compare two versions of one policy group deterministically."""
    left_meta = left_doc.get("metadata") or {}
    right_meta = right_doc.get("metadata") or {}
    if left_doc.get("document_id") == right_doc.get("document_id"):
        raise ValueError("LEFT_RIGHT_SAME")
    if (left_meta.get("policy_group_id") or "") != (right_meta.get("policy_group_id") or ""):
        raise ValueError("CROSS_POLICY_GROUP")

    left_blocks = sorted(left_doc.get("blocks", []), key=lambda b: b.get("ordinal", 0))
    right_blocks = sorted(right_doc.get("blocks", []), key=lambda b: b.get("ordinal", 0))
    # 合并/嵌套等非正文块不参与条款对比（合成夹具为纯段落）
    left_units = [b for b in left_blocks if b.get("kind") == "paragraph"]
    right_units = [b for b in right_blocks if b.get("kind") == "paragraph"]

    left_keys: dict[str, int] = {}
    right_keys: dict[str, int] = {}
    for i, b in enumerate(left_units):
        k = _clause_key(b.get("text", ""))
        if k and k not in left_keys:
            left_keys[k] = i
    for i, b in enumerate(right_units):
        k = _clause_key(b.get("text", ""))
        if k and k not in right_keys:
            right_keys[k] = i

    used_left: set[int] = set()
    used_right: set[int] = set()
    pairs: list[tuple[int | None, int | None]] = []

    # 1) 条款标识优先配对
    for k, li in left_keys.items():
        if k in right_keys:
            ri = right_keys[k]
            pairs.append((li, ri))
            used_left.add(li)
            used_right.add(ri)
    keyed_left = [i for i in range(len(left_units)) if i not in used_left and _clause_key(left_units[i].get("text", ""))]
    keyed_right = [i for i in range(len(right_units)) if i not in used_right and _clause_key(right_units[i].get("text", ""))]
    # 只在一侧出现的条款标识 → 删除 / 新增
    for li in keyed_left:
        pairs.append((li, None))
    for ri in keyed_right:
        pairs.append((None, ri))
    used_left.update(keyed_left)
    used_right.update(keyed_right)

    # 2) 未编号正文：保持顺序的精确文本匹配
    rem_left = [i for i in range(len(left_units)) if i not in used_left]
    rem_right = [i for i in range(len(right_units)) if i not in used_right]
    lcs = _lcs_pairs(
        [left_units[i].get("text", "") for i in rem_left],
        [right_units[i].get("text", "") for i in rem_right],
    )
    for a, b in lcs:
        li, ri = rem_left[a], rem_right[b]
        pairs.append((li, ri))
        used_left.add(li)
        used_right.add(ri)

    # 3) 未编号剩余：保持顺序的相似度配对 → 修改
    rem_left = [i for i in range(len(left_units)) if i not in used_left]
    rem_right = [i for i in range(len(right_units)) if i not in used_right]
    i = j = 0
    while i < len(rem_left) and j < len(rem_right):
        li, ri = rem_left[i], rem_right[j]
        ratio = difflib.SequenceMatcher(
            None, left_units[li].get("text", ""), right_units[ri].get("text", ""), autojunk=False
        ).ratio()
        if ratio >= MODIFIED_SIMILARITY:
            pairs.append((li, ri))
            i += 1
            j += 1
        else:
            nxt_r = (
                difflib.SequenceMatcher(
                    None, left_units[li].get("text", ""), right_units[rem_right[j + 1]].get("text", ""), autojunk=False
                ).ratio()
                if j + 1 < len(rem_right) else -1.0
            )
            nxt_l = (
                difflib.SequenceMatcher(
                    None, left_units[rem_left[i + 1]].get("text", ""), right_units[ri].get("text", ""), autojunk=False
                ).ratio()
                if i + 1 < len(rem_left) else -1.0
            )
            # 前瞻判断“谁是游离段”：左当前更像右下一段 → 右当前是新增段，
            # 先记新增并推进 j，左当前留待与右下一段配对；反之记左当前删除并推进 i。
            if nxt_r >= nxt_l:
                pairs.append((None, ri))
                j += 1
            else:
                pairs.append((li, None))
                i += 1
    for li in rem_left[i:]:
        pairs.append((li, None))
    for ri in rem_right[j:]:
        pairs.append((None, ri))

    # 构造条目并按稳定顺序输出
    entries = []
    for li, ri in pairs:
        left_ref = (
            _block_ref(left_doc.get("document_id", ""), left_meta.get("sha256"), left_units[li])
            if li is not None else None
        )
        right_ref = (
            _block_ref(right_doc.get("document_id", ""), right_meta.get("sha256"), right_units[ri])
            if ri is not None else None
        )
        if left_ref is not None and right_ref is not None:
            if left_ref["text"] == right_ref["text"]:
                change = "unchanged"
            else:
                change = "modified"
        elif left_ref is not None:
            change = "deleted"
        else:
            change = "added"
        key = _clause_key((left_ref or right_ref)["text"])
        entry = {
            "change_type": change,
            "clause_key": key,
            "left": left_ref,
            "right": right_ref,
            "diff_segments": (
                _diff_segments(left_ref["text"], right_ref["text"])
                if change == "modified" else None
            ),
        }
        entry["_sort"] = li if li is not None else ri
        entries.append(entry)

    order = {"deleted": 0, "added": 1, "modified": 2, "unchanged": 3}
    entries.sort(key=lambda e: (e["_sort"], order[e["change_type"]]))
    for idx, e in enumerate(entries, start=1):
        e["diff_id"] = f"D{idx}"
        e.pop("_sort", None)

    counts = {t: 0 for t in CHANGE_TYPES}
    for e in entries:
        counts[e["change_type"]] += 1

    return {
        "left": _side_meta(left_doc),
        "right": _side_meta(right_doc),
        "counts": counts,
        "entries": entries,
        "algorithm": {"note": ALGORITHM_NOTE, "limitations": LIMITATIONS},
        "disclaimer": "文字差异对比：不判断哪个版本适用于某个学生；日期较新不等于现行有效；差异不构成资格或政策适用结论。",
    }
