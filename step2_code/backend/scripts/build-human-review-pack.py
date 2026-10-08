"""T036: build the offline human-review pack (review.html + pack.json + README).

Read-only inputs: real corpus pack (manifest + originals), T030 v1.3 questions,
the real transfer-major procedures template. Uses the existing real parser
only — no retrieval, ASR, generator or model loading. No network.

Before writing anything it programmatically verifies, for ALL 57 gold evidence
items and ALL 20 template citations: document existence, document SHA-256,
block existence, in-block span validity and quote == block slice verbatim.
Any failure exits non-zero WITHOUT producing a pack (never repairs input by
editing quotes/gold).

Output directory must not exist or must be empty — an existing pack is never
overwritten; rerun into a fresh directory.

The generated review.html is a self-contained local file (inline CSS/JS/data;
no CDN/fetch/external fonts). All human opinions default to 未复核; the tool
never writes back to gold/template/history files — clicking export downloads a
NEW JSON record of the human's own entries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))
sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE_HTML = BACKEND / "scripts" / "human-review-pack.html"

SEMANTICS_NOTES = [
    "同 fact_id（OR 组）的每条来源须**独立完整支持**该事实（判断类别与行为、前提与结论不拆散）；任一来源被命中即该事实满足。",
    "不同 fact_id 是不同必要事实（AND），禁止因主题相似判等价；不同精度/版本/主体/前提/程序不合并。",
    "不足题（无 gold 引用）≠「学校无规定」：展示已查范围/排除依据，属资料准入不足或未记载。",
    "模板跨页引用以全部原引并列展示（不截断页尾）；引用逐字/跨度/哈希已程序化核对，但**程序化一致不代表语义正确或政策现行有效**。",
    "本包为人工意见记录工具；MiMo/Astra 技术核对不代替人工审定，导出记录不是签署认证或学校政策确认。",
]


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


def build(manifest_path: Path, corpus_root: Path, questions_path: Path,
          procedures_path: Path, out_dir: Path) -> int:
    # ---- refuse to overwrite an existing pack ----
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"FAIL: 输出目录非空，拒绝覆盖已有复核包: {out_dir}")
        print("请换一个新的输出目录重跑（例如 T036-v2）。")
        return 1

    from campus_assistant.corpus.parse import parse_manifest

    parse_result = parse_manifest(manifest_path, corpus_root)
    if not parse_result.get("valid"):
        print("FAIL: 语料解析失败:", parse_result.get("errors"))
        return 1
    documents = parse_result["documents"]
    docs_by_id = {d["document_id"]: d for d in documents}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_by_id = {m["document_id"]: m for m in manifest.get("documents", [])}

    questions_doc = json.loads(questions_path.read_text(encoding="utf-8"))
    procedures_doc = json.loads(procedures_path.read_text(encoding="utf-8"))

    fails: list[str] = []
    checked = 0

    def verify_ref(ref: dict, ctx: str) -> dict:
        """Verify one citation against the fresh parse; return display fields."""
        nonlocal checked
        checked += 1
        doc_id = ref["document_id"]
        doc = docs_by_id.get(doc_id)
        if doc is None:
            fails.append(f"{ctx}: 文档缺失 {doc_id}")
            return {}
        m = manifest_by_id.get(doc_id, {})
        sha_ok = m.get("sha256") == ref.get("document_sha256") == doc["metadata"].get("sha256")
        if not sha_ok:
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
        if text[s:e] != ref.get("quote"):
            fails.append(f"{ctx}: quote 与块切片不一致 {doc_id}/{ref['block_id']}[{s},{e})")
        idx = next(i for i, b in enumerate(blocks) if b["block_id"] == ref["block_id"])
        prev_b = blocks[idx - 1] if idx > 0 else None
        next_b = blocks[idx + 1] if idx + 1 < len(blocks) else None
        local = m.get("local_path")
        return {
            "document_id": doc_id,
            "document_sha256": ref.get("document_sha256"),
            "block_id": ref["block_id"],
            "char_start": s,
            "char_end": e,
            "quote": ref.get("quote"),
            "document_title": m.get("title"),
            "version_label": m.get("version_label"),
            "published_at": m.get("published_at"),
            "effective_from": m.get("effective_from"),
            "effective_to": m.get("effective_to"),
            "scope": m.get("scope"),
            "is_synthetic": bool(m.get("is_synthetic", False)),
            "locator": blk.get("locator"),
            "locator_display": _locator_display(blk.get("locator")),
            "block_text": text,
            "block_len": len(text),
            "prev_block": ({"block_id": prev_b["block_id"], "text": prev_b.get("text", "")} if prev_b else None),
            "next_block": ({"block_id": next_b["block_id"], "text": next_b.get("text", "")} if next_b else None),
            "local_file": f"{corpus_root.as_posix()}/{local}" if local else None,
            "verify": "构建时程序化核对：文档 SHA、块存在、跨度合法、quote==块切片逐字一致",
        }

    # ---- questions ----
    q_items = []
    for q in questions_doc["questions"]:
        ev_items = []
        fact_groups: dict = {}
        for ev in q.get("evidence", []):
            item = verify_ref(ev, f"{q['question_id']}/{ev.get('evidence_id')}")
            item["evidence_id"] = ev.get("evidence_id")
            item["fact_id"] = ev.get("fact_id")
            item["required"] = True
            ev_items.append(item)
            fid = ev.get("fact_id") or f"(无fact_id) {ev.get('evidence_id')}"
            fact_groups.setdefault(fid, []).append(ev.get("evidence_id"))
        groups = [
            {
                "fact_id": (k if not k.startswith("(无fact_id)") else None),
                "label": k,
                "evidence_ids": v,
                "semantics": "OR：任一来源被完整覆盖即该事实满足；每源须独立完整支持",
            }
            for k, v in fact_groups.items()
        ]
        q_items.append({
            "question_id": q["question_id"],
            "query": q.get("query"),
            "conditions": q.get("conditions"),
            "answerable": q.get("answerable"),
            "question_type": q.get("question_type"),
            "group_id": q.get("group_id"),
            "rationale": q.get("rationale"),
            "missing": q.get("missing"),
            "revision_note": q.get("revision_note"),
            "fact_groups": groups,
            "fact_semantics": "不同 fact_id 之间为 AND（不同必要事实）",
            "evidence": ev_items,
        })

    # ---- template ----
    t_items = []
    for proc in procedures_doc.get("procedures", []):
        steps = []
        for st in proc.get("steps", []):
            cites = []
            for c in st.get("citations", []):
                item = verify_ref(c, f"{proc.get('procedure_id')}/{st.get('step_id')}/{c.get('block_id','')[:8]}")
                item["required"] = bool(c.get("required", True))
                cites.append(item)
            steps.append({
                "step_id": st.get("step_id"),
                "title": st.get("title"),
                "detail": st.get("detail"),
                "unspecified": st.get("unspecified") or [],
                "citations": cites,
            })
        t_items.append({
            "procedure_id": proc.get("procedure_id"),
            "title": proc.get("title"),
            "template_version": proc.get("template_version"),
            "summary": proc.get("summary"),
            "is_synthetic": bool(proc.get("is_synthetic", False)),
            "steps": steps,
        })

    total_ev = sum(len(q["evidence"]) for q in q_items)
    total_cit = sum(len(s["citations"]) for p in t_items for s in p["steps"])
    print(f"核对引用: {checked} 条（gold 证据 {total_ev} + 模板引用 {total_cit}）")
    if fails:
        for f in fails:
            print("FAIL:", f)
        print(f"CHECK FAILED: {len(fails)} 项——未输出复核包（不改输入、不写半成品）")
        return 1
    if total_ev != 57 or total_cit != 20:
        print(f"FAIL: 条目数与预期不符（gold 证据 {total_ev}≠57 或 模板引用 {total_cit}≠20）")
        return 1

    pack = {
        "pack_meta": {
            "record_type": "human_review_pack",
            "tool": "scripts/build-human-review-pack.py (T036)",
            "human_review_status": "unreviewed",
            "declaration": (
                "题目、事实组与模板由 MiMo（执行模型辅助）编制，人工复核状态：未复核。"
                "本包是人工意见记录工具；程序化逐字一致不代表语义正确或政策现行有效。"
                "导出记录不是签署认证、不是学校政策确认；不写回 gold/模板/历史文件。"
            ),
            "inputs": {
                "questions": {"path": str(questions_path), "sha256": _sha(questions_path),
                              "dataset_version": questions_doc.get("dataset_version")},
                "manifest": {"path": str(manifest_path), "sha256": _sha(manifest_path)},
                "procedures": {"path": str(procedures_path), "sha256": _sha(procedures_path),
                               "template_version": t_items[0]["template_version"] if t_items else None},
            },
            "counts": {
                "questions": len(q_items),
                "answerable": sum(1 for q in q_items if q["answerable"]),
                "unanswerable": sum(1 for q in q_items if not q["answerable"]),
                "evidence": total_ev,
                "template_steps": sum(len(p["steps"]) for p in t_items),
                "template_citations": total_cit,
                "verified_refs": checked,
            },
        },
        "semantics_notes": SEMANTICS_NOTES,
        "questions": q_items,
        "templates": t_items,
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

    readme = f"""# 离线人工复核包（T036-v1）

## 打开方式（本机离线，无网络/无密钥/无模型）

双击或用浏览器打开本目录 `review.html` 即可（本地 file:// 直接打开；页面自包含 CSS/JS/数据，不加载任何外部资源）。

## 构建命令（Windows PowerShell，含空格路径已用引号；输出目录必须为空或不存在）

```powershell
& 'F:\\Collage Paper\\step2_code\\backend\\.venv\\Scripts\\python.exe' 'F:\\Collage Paper\\step2_code\\backend\\scripts\\build-human-review-pack.py' --manifest 'F:\\Collage Paper\\data\\corpora\\sicau-rag-pilot-v1.1\\manifest.json' --corpus-root 'F:\\Collage Paper\\data\\corpora\\sicau-rag-pilot-v1.1' --questions 'F:\\Collage Paper\\data\\evaluations\\sicau-rag-pilot-eval-v1\\questions.json' --procedures 'F:\\Collage Paper\\data\\procedures\\sicau-transfer-2026-v1\\procedures.json' --out-dir 'F:\\Collage Paper\\step2_code\\backend\\.cache\\human-review\\T036-v1'
```

重跑请换新目录（如 T036-v2）——输出目录非空时构建脚本**拒绝执行**，不覆盖已有包。

## 内容

- `pack.json`：结构化对照数据（输入 SHA/版本、24 题×事实组×57 证据、13 步×20 引用；每条含逐字 quote、原解析块全文、前后相邻块、页码定位、本地原件路径）。
- `review.html`：离线浏览与人工记录页面（意见初值全部「未复核」；可导出复核记录 JSON）。
- 构建时已对 77 条引用（57+20）逐条程序化核对：文档 SHA、块存在、跨度、quote 逐字一致。

## 使用说明

- 人工意见四档：未复核/确认/需修订/未确认；允许保留「需修订/未确认」，不要求全选通过。
- 「导出复核记录」下载**新的 JSON**（含输入身份 SHA 与各条意见），**不会**写回 gold/模板/历史文件。
- 页面**不自动保存**：刷新/关闭会丢失未导出的意见；可随时导出阶段性记录。
- 导出记录不是人工签署认证，更不是学校政策确认。
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    print("wrote", out_dir)
    print("CHECK OK: 77 条引用逐字/跨度/哈希核对通过；24 题(20+4)/57 证据/13 步/20 引用齐备")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="构建离线人工复核包（只读输入；不加载模型）")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--corpus-root", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--procedures", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    return build(Path(args.manifest), Path(args.corpus_root), Path(args.questions),
                 Path(args.procedures), Path(args.out_dir))


if __name__ == "__main__":
    raise SystemExit(main())
