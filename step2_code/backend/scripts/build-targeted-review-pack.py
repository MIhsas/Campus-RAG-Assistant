"""T042: build the offline targeted supplemental review pack (8 items).

Zones: T039 revisions (q08/q10/u03/u04) + T040 historical real answers for the
same four questions. Stable card IDs are domain-separated: `revision:q10` and
`answer:q10` never share opinion state.

Read-only inputs: real corpus pack v1.2 (fresh parse), frozen questions v2.0,
T039 review-supplement.md, T040 live-answers-full.json, T041 casebook link,
the user's original T036 record (identity SHA only; opinions are displayed
read-only from the supplement headings). Never writes back to any input.

Before writing anything it programmatically verifies every quote it will embed
(document SHA-256, block existence, span validity, quote == block slice
verbatim) against a fresh parse. Any failure exits non-zero WITHOUT producing
a pack. Output directory must not exist or be empty.

The generated review.html is self-contained (inline CSS/JS/data; no
fetch/localStorage/external resources). All 8 new opinions default to 未复核.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))
sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE_HTML = BACKEND / "scripts" / "targeted-review-pack.html"

CARD_IDS = ("revision:q08", "revision:q10", "revision:u03", "revision:u04",
            "answer:q08", "answer:q10", "answer:u03", "answer:u04")
QUESTION_IDS = ("q08", "q10", "u03", "u04")

# 固定关键点（工单口径；显示于对应卡片，不新增逐引用意见）
SPECIAL_NOTES = {
    "revision:q08": [
        "本卡展示的是 T039 修订的 gold 原文（事实 f1 两源）；T040 本次实发证据未检出该 gold——两者分区显示，**不能把 gold 补成模型实发 E**。",
    ],
    "revision:q10": [
        "普通 50/50 与开展学生互评 40/10/50 是**不同前提**，分别核对，不合并、不按年份宣布 2016 废止。",
    ],
    "revision:u03": [
        "v1.2 已核实 bed3ac 日期（2019-11-07）→ 严格口径可答；**日期已核实 ≠ 学校政策现行性认证**。",
    ],
    "revision:u04": [
        "严格不足与范围未知候选**分开**：83eb 候选仅标「未核实范围/非本次模型依据」，不替用户更改 scope、不推测办理部门。",
    ],
    "answer:q08": [
        "本卡为历史已存结果（非新生成）。实发 E 中**不含**修订 gold 原文（gold 缺口见 revision:q08 卡）；模型拒答忠于本次实发证据，合理不足≠答对 gold。",
    ],
    "answer:q10": [
        "P3「不纳入上述组成比例」是**推断**（「单独记载」有原文、比例排除无逐字规定）——**请单独核实**；两前提分开表述、未宣告 2016 废止。",
    ],
    "answer:u03": [
        "答案与已核实来源原文一致；**不代表学校政策现行有效**；日期未知来源未参与。",
    ],
    "answer:u04": [
        "范围未知候选（83eb）**未混入**本次实发 E；拒答未推测办理部门；不足≠学校无规定。",
    ],
}

ZONE_META = [
    {
        "zone_id": "t039_revision",
        "title": "分区一：T039 修订（q08 / q10 / u03 / u04）",
        "note": "原意见只读展示（不预填到下方新意见）；实际处置、新题面/条件/事实组或不足范围、gold 原文与待确认点。这里是修订核对，不是模型回答。",
    },
    {
        "zone_id": "t040_answer",
        "title": "分区二：T040 结果（q08 / q10 / u03 / u04）",
        "note": "历史已存真实结果（2026-10-10 一次四题限定运行）：原 query/条件、完整原答案或不足理由（逐字照录）、该次真正发出的 E、辅助核对与用户状态。不是新生成；live_verified 仅限该历史链路/存档核查。",
    },
]

DECLARATION = (
    "本包是 8 项补充意见记录工具：工具完成不等于人工复核完成；程序化逐字一致不代表语义正确或政策现行有效。"
    "新意见初值全部「未复核」；导出是新 JSON 记录，不是签署认证或学校政策确认；不写回 gold/模板/历史用户记录。"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _locator_display(locator: dict | None) -> str:
    if not locator:
        return "未知（解析未提供定位）"
    t = locator.get("type")
    if t == "pdf_page":
        s = f"PDF 第 {locator.get('page', '?')} 页"
        if locator.get("part", 1) != 1:
            s += f"（第 {locator['part']} 部分）"
        return s
    if t == "paragraph":
        return f"段落 #{locator.get('paragraph_index', '?')}"
    return f"未知定位类型：{json.dumps(locator, ensure_ascii=False)}"


def parse_supplement(text: str) -> dict[str, dict]:
    """Parse T039 review-supplement.md per-question sections (fixed format)."""
    out: dict[str, dict] = {}
    cur: dict | None = None
    cur_sec: dict | None = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^## (q08|q10|u03|u04)（用户：(.+?)）\s*$", line)
        if m:
            cur = {
                "question_id": m.group(1),
                "original_user_opinion": m.group(2),
                "disposition": "",
                "query_line_extra": "",
                "sections": [],
                "model_note": "",
                "pending_points": [],
            }
            out[m.group(1)] = cur
            cur_sec = None
            i += 1
            continue
        if cur is None:
            i += 1
            continue
        m = re.match(r"^- 处置：(.+)$", line)
        if m:
            cur["disposition"] = m.group(1).strip()
            i += 1
            continue
        m = re.match(r"^- query：「(.+?)」｜conditions：(\{.*?\})(?:｜(.+))?$", line)
        if m:
            cur["query_from_supp"] = m.group(1)
            cur["conditions_from_supp"] = json.loads(m.group(2))
            cur["query_line_extra"] = (m.group(3) or "").strip()
            i += 1
            continue
        m = re.match(r"^### (.+)$", line)
        if m:
            cur_sec = {"title": m.group(1), "is_candidate": "未核实候选" in m.group(1)}
            cur["sections"].append(cur_sec)
            i += 1
            continue
        if cur_sec is not None:
            m = re.match(r"^block_id `([0-9a-f]+)`｜定位 (\{.*?\})｜跨度 \[(\d+):(\d+)\]", line)
            if m:
                cur_sec["block_id"] = m.group(1)
                cur_sec["locator"] = ast.literal_eval(m.group(2))  # 补充文件为 Python 字面量（单引号）
                cur_sec["char_start"] = int(m.group(3))
                cur_sec["char_end"] = int(m.group(4))
                i += 1
                continue
            m = re.match(r"^来源：(.+?)｜document_id `([0-9a-f]+)`", line)
            if m:
                cur_sec["source_display"] = m.group(1)
                cur_sec["document_id"] = m.group(2)
                i += 1
                continue
        if line.startswith("逐字原文"):
            if i + 2 < len(lines) and lines[i + 1].strip() == "```text":
                j = i + 2
                buf = []
                while j < len(lines) and lines[j].strip() != "```":
                    buf.append(lines[j])
                    j += 1
                if cur_sec is not None:
                    cur_sec["quote"] = "\n".join(buf)
                i = j + 1
                continue
        m = re.match(r"^\*\*模型辅助示例释义（非产品实时生成[^*]*）\*\*：(.+)$", line)
        if m:
            body = m.group(1)
            cur["model_note"] = body
            pm = re.search(r"待确认：(.+)$", body)
            if pm:
                cur["pending_points"].append(pm.group(1).strip())
            i += 1
            continue
        i += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="构建 T042 八项定向补充复核包（只读输入；不加载模型）")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--corpus-root", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--supplement", required=True)
    ap.add_argument("--live-answers", required=True)
    ap.add_argument("--casebook", required=True)
    ap.add_argument("--user-record", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"FAIL: 输出目录非空，拒绝覆盖已有复核包: {out_dir}")
        return 1

    from campus_assistant.corpus.parse import parse_manifest

    manifest_path = Path(args.manifest)
    corpus_root = Path(args.corpus_root)
    questions_path = Path(args.questions)
    supplement_path = Path(args.supplement)
    live_path = Path(args.live_answers)
    casebook_path = Path(args.casebook)
    user_record_path = Path(args.user_record)

    parse_result = parse_manifest(manifest_path, corpus_root)
    if not parse_result.get("valid"):
        print("FAIL: 语料解析失败:", parse_result.get("errors"))
        return 1
    documents = parse_result["documents"]
    docs_by_id = {d["document_id"]: d for d in documents}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_by_id = {m["document_id"]: m for m in manifest.get("documents", [])}

    questions_doc = json.loads(questions_path.read_text(encoding="utf-8"))
    q_by_id = {q["question_id"]: q for q in questions_doc["questions"]}
    live_doc = json.loads(live_path.read_text(encoding="utf-8"))
    supp = parse_supplement(supplement_path.read_text(encoding="utf-8"))

    fails: list[str] = []
    checked = 0

    def verify_ref(ref: dict, ctx: str, quote: str | None = None) -> dict:
        """Verify one citation against the fresh parse; return display fields."""
        nonlocal checked
        checked += 1
        doc_id = ref["document_id"]
        doc = docs_by_id.get(doc_id)
        if doc is None:
            fails.append(f"{ctx}: 文档缺失 {doc_id}")
            return {}
        m = manifest_by_id.get(doc_id, {})
        if not (m.get("sha256") == ref.get("document_sha256", m.get("sha256")) == doc["metadata"].get("sha256")):
            fails.append(f"{ctx}: 文档 SHA 不符 {doc_id}")
        blocks = doc.get("blocks") or []
        blk = next((b for b in blocks if b["block_id"] == ref["block_id"]), None)
        if blk is None:
            fails.append(f"{ctx}: 块缺失 {doc_id}/{ref['block_id']}")
            return {}
        text = blk.get("text", "")
        s, e = ref["char_start"], ref["char_end"]
        if not (0 <= s < e <= len(text)):
            fails.append(f"{ctx}: 跨度非法 [{s},{e}) (块长 {len(text)})")
            return {}
        q = quote if quote is not None else ref.get("quote")
        if text[s:e] != q:
            fails.append(f"{ctx}: quote 与块切片不一致 {doc_id}/{ref['block_id']}[{s},{e})")
        idx = next(i for i, b in enumerate(blocks) if b["block_id"] == ref["block_id"])
        prev_b = blocks[idx - 1] if idx > 0 else None
        next_b = blocks[idx + 1] if idx + 1 < len(blocks) else None
        return {
            "document_id": doc_id,
            "document_sha256": m.get("sha256"),
            "block_id": ref["block_id"],
            "char_start": s,
            "char_end": e,
            "quote": q,
            "document_title": m.get("title"),
            "version_label": m.get("version_label"),
            "locator": blk.get("locator"),
            "locator_display": _locator_display(blk.get("locator")),
            "block_text": text,
            "block_len": len(text),
            "prev_block": ({"block_id": prev_b["block_id"], "text": prev_b.get("text", "")} if prev_b else None),
            "next_block": ({"block_id": next_b["block_id"], "text": next_b.get("text", "")} if next_b else None),
            "local_file": f"{corpus_root.as_posix()}/{m['local_path']}" if m.get("local_path") else None,
            "verify": "构建时程序化核对：文档 SHA、块存在、跨度合法、quote==块切片逐字一致",
        }

    # ---------- revision cards (zone 1) ----------
    cards: list[dict] = []
    for qid in QUESTION_IDS:
        q = q_by_id[qid]
        s = supp.get(qid)
        if s is None:
            fails.append(f"review-supplement 缺少 {qid} 小节")
            continue
        if s.get("query_from_supp") != q["query"] or s.get("conditions_from_supp") != q["conditions"]:
            fails.append(f"{qid}: supplement 的 query/conditions 与冻结题集不一致")
        gold_items = []
        fact_groups: dict[str, list[str]] = {}
        for ev in q.get("evidence", []):
            item = verify_ref(ev, f"revision:{qid}/{ev.get('evidence_id')}", quote=ev.get("quote"))
            item["evidence_id"] = ev.get("evidence_id")
            item["fact_id"] = ev.get("fact_id")
            gold_items.append(item)
            fact_groups.setdefault(ev.get("fact_id") or "?", []).append(ev.get("evidence_id"))
        candidates = []
        for sec in s.get("sections", []):
            if not sec.get("is_candidate"):
                continue
            ref = {
                "document_id": sec.get("document_id"),
                "block_id": sec.get("block_id"),
                "char_start": sec.get("char_start"),
                "char_end": sec.get("char_end"),
            }
            item = verify_ref(ref, f"revision:{qid}/candidate/{sec.get('block_id','')[:8]}", quote=sec.get("quote"))
            item["section_title"] = sec.get("title")
            item["candidate_label"] = "未核实范围/非本次模型依据（非严格 gold、非实发 E）"
            candidates.append(item)
        cards.append({
            "card_id": f"revision:{qid}",
            "object_type": "revision",
            "zone_id": "t039_revision",
            "question_id": qid,
            "query": q["query"],
            "conditions": q["conditions"],
            "original_user_opinion": s.get("original_user_opinion", ""),
            "disposition": s.get("disposition", ""),
            "query_line_extra": s.get("query_line_extra", ""),
            "answerable": q.get("answerable"),
            "question_type": q.get("question_type"),
            "rationale": q.get("rationale"),
            "missing": q.get("missing"),
            "revision_note": q.get("revision_note"),
            "fact_groups": [{"fact_id": k, "evidence_ids": v} for k, v in fact_groups.items()],
            "gold_evidence": gold_items,
            "candidates": candidates,
            "model_note": s.get("model_note", ""),
            "pending_points": s.get("pending_points", []),
            "special_notes": SPECIAL_NOTES.get(f"revision:{qid}", []),
        })

    # ---------- answer cards (zone 2) ----------
    for qid in QUESTION_IDS:
        a = live_doc["questions"].get(qid)
        if a is None:
            fails.append(f"live-answers-full 缺少 {qid}")
            continue
        s = supp.get(qid, {})
        if a.get("query") != q_by_id[qid]["query"] or a.get("conditions") != q_by_id[qid]["conditions"]:
            fails.append(f"answer:{qid}: T040 记录的 query/conditions 与冻结题集不一致")
        sent = []
        for ev in a.get("evidence_full", []):
            item = verify_ref(ev, f"answer:{qid}/{ev.get('evidence_id')}", quote=ev.get("text"))
            item["evidence_id"] = ev.get("evidence_id")
            item["preview_url"] = ev.get("preview_url")
            sent.append(item)
        cards.append({
            "card_id": f"answer:{qid}",
            "object_type": "answer",
            "zone_id": "t040_answer",
            "question_id": qid,
            "query": a["query"],
            "conditions": a["conditions"],
            "outcome": a.get("outcome"),
            "outcome_display": (
                "已存答案（历史真实结果）" if a.get("outcome") == "answered"
                else "模型判断材料不足（历史真实结果）"
            ),
            "answer_paragraphs": a.get("answer_paragraphs_full"),
            "insufficient_reason": a.get("insufficient_reason"),
            "sent_evidence": sent,
            "generation_meta": a.get("generation_meta"),
            "aux_checks_reference": "辅助核对（执行者判读，非用户结论）详见 submissions/T040/live-review-notes.md",
            "special_notes": SPECIAL_NOTES.get(f"answer:{qid}", []),
            "original_user_opinion_readonly": s.get("original_user_opinion", ""),
        })

    if [c["card_id"] for c in cards] != list(CARD_IDS):
        fails.append(f"卡片 ID 集合/顺序异常: {[c['card_id'] for c in cards]}")
    print(f"核对引用: {checked} 条（gold 证据 + 未核实候选 + T040 实发 E）")
    if fails:
        for f in fails:
            print("FAIL:", f)
        print(f"CHECK FAILED: {len(fails)} 项——未输出复核包（不改输入、不写半成品）")
        return 1

    pack = {
        "pack_meta": {
            "record_type": "targeted_review_pack",
            "tool": "scripts/build-targeted-review-pack.py (T042)",
            "human_review_status": "unreviewed",
            "declaration": DECLARATION,
            "review_scope": "T039 四项修订 + T040 同四题历史真实结果，共 8 项；不重审 T036 全部 114 项或模板 33 项",
            "inputs": {
                "questions": {"path": str(questions_path), "sha256": _sha(questions_path),
                              "dataset_version": questions_doc.get("dataset_version")},
                "manifest": {"path": str(manifest_path), "sha256": _sha(manifest_path)},
                "review_supplement": {"path": str(supplement_path), "sha256": _sha(supplement_path)},
                "live_answers_full": {"path": str(live_path), "sha256": _sha(live_path)},
                "casebook": {"path": str(casebook_path), "sha256": _sha(casebook_path)},
                "user_record": {"path": str(user_record_path), "sha256": _sha(user_record_path)},
            },
            "counts": {"cards": len(cards), "revision_cards": 4, "answer_cards": 4, "verified_refs": checked},
        },
        "zones": ZONE_META,
        "cards": cards,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pack.json").write_text(
        json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tpl = TEMPLATE_HTML.read_text(encoding="utf-8")
    html = tpl.replace("/*__PACK_DATA__*/null", json.dumps(pack, ensure_ascii=False))
    if "/*__PACK_DATA__*/" in html:
        print("FAIL: HTML 模板数据占位符替换失败")
        return 1
    (out_dir / "review.html").write_text(html, encoding="utf-8")

    readme = f"""# T042 八项定向补充复核包（T042-v1）

## 打开方式（本机离线，无网络/无密钥/无模型）

双击或用浏览器打开本目录 `review.html`（自包含 CSS/JS/数据；无 fetch/localStorage/外部资源）。

## 构建命令（Windows PowerShell；输出目录必须为空或不存在）

```powershell
& 'F:\\Collage Paper\\step2_code\\backend\\.venv\\Scripts\\python.exe' 'F:\\Collage Paper\\step2_code\\backend\\scripts\\build-targeted-review-pack.py' --manifest 'F:\\Collage Paper\\data\\corpora\\sicau-rag-pilot-v1.2\\manifest.json' --corpus-root 'F:\\Collage Paper\\data\\corpora\\sicau-rag-pilot-v1.2' --questions 'F:\\Collage Paper\\data\\evaluations\\sicau-rag-pilot-eval-v2\\questions.json' --supplement 'F:\\Collage Paper\\docs\\collaboration\\submissions\\T039\\review-supplement.md' --live-answers 'F:\\Collage Paper\\docs\\collaboration\\submissions\\T040\\live-answers-full.json' --casebook 'F:\\Collage Paper\\docs\\delivery\\generation-casebook.md' --user-record 'F:\\Collage Paper\\data\\reviews\\T036-user-review-20261008\\human-review-record.json' --out-dir 'F:\\Collage Paper\\step2_code\\backend\\.cache\\human-review\\T042-v1'
```

重跑请换新目录（如 T042-v2）——非空输出目录构建脚本拒绝执行。

## 内容（只含本次 8 项）

- 分区一 T039 修订：`revision:q08/q10/u03/u04`——原意见只读、处置、新题面/条件/事实组或不足范围、gold 原文（含未核实候选，单独标注）、待确认点。
- 分区二 T040 结果：`answer:q08/q10/u03/u04`——历史原 query/条件、完整原答案或不足理由（逐字）、该次实发 E、辅助核对与用户状态。
- 构建时对全部嵌入引用程序化核对：文档 SHA、块、跨度、quote 逐字一致；核对不通过则不出包。

## 使用说明

- **8 项新意见初值全部「未复核」**；四档=未复核/确认/需修订/未确认，每项可写说明；不提供「全选通过」。
- 原历史意见只读展示，不预填到新意见；统计只计本次 8 项，**不与历史 109/3/2 合并**。
- 「导出复核记录」下载**新的 JSON**（8 个稳定分域 ID/对象类型/题号/意见/说明 + 输入版本与 SHA + 导出时间）；复核人/日期字段留空由用户填，**不预填签名、导出时间≠签署日期**。
- 页面**不自动保存**（无 localStorage/fetch）：刷新/关闭会丢失未导出的意见；可随时导出阶段性记录。导出不是政策认证。
- 程序化核对不证明语义正确；工具完成不等于人工复核完成。
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    print("wrote", out_dir)
    print(f"CHECK OK: {checked} 条引用逐字/跨度/哈希核对通过；8 卡（4 修订 + 4 结果）齐备，新意见全部未复核")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
