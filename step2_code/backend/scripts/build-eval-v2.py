"""Build the independent evaluation-v2 corpus (T027).

Assembles ``examples/evaluation-v2/corpus/`` from byte-identical copies of
existing synthetic fixtures (parse/filter-demo/comparison/pdf-text) plus two
CLEARLY-MARKED new distractor documents. Never modifies the old
``examples/evaluation`` questions, original fixture corpora, templates or
historical gold.

Subcommands:
  assemble      build corpus/ + manifest.json (deterministic; re-run safe)
  dump-blocks   parse the corpus and write document_id/block_id/parser_version/
                sha256/text dump (for annotation against原文)
  fill-spans    fill evidence char_start/char_end/document_sha256/parser_version
                in a questions draft by EXACT substring location in block text
                (annotation aid — the gold quote is authored from原文 first,
                spans are derived mechanically; never from retrieval results)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
V2 = BACKEND / "examples" / "evaluation-v2"
CORPUS = V2 / "corpus"

# (document_id, source manifest dir, source local_path)
COPIES = [
    ("syn-parse-txt-001", "parse-corpus", "sample.txt"),
    ("syn-parse-docx-001", "parse-corpus", "sample.docx"),
    ("fd-2024", "filter-demo", "filter-2024.txt"),
    ("fd-2025", "filter-demo", "filter-2025.txt"),
    ("fd-yjy", "filter-demo", "filter-yjy.txt"),
    ("fd-unknown", "filter-demo", "filter-unknown.txt"),
    ("fd-future", "filter-demo", "filter-future.txt"),
    ("cmp-defer-v1", "comparison-corpus", "cmp-defer-v1.txt"),
    ("cmp-defer-v2", "comparison-corpus", "cmp-defer-v2.txt"),
    ("cmp-grades-1", "comparison-corpus", "cmp-grades.txt"),
    ("syn-pdf-text-001", "pdf-corpus", "sample-text.pdf"),
]

# 新增干扰资料（明显标注的合成示例）
DISTRACTORS = {
    "dis-graduate-defer": {
        "text": (
            "【合成测试文件 — 干扰资料，明显标注的合成示例，不代表任何真实学校规定】\n\n"
            "研究生缓考与创新基金管理办法（合成干扰示例）\n\n"
            "第一条 本办法适用于全日制研究生，不适用于本科生。\n\n"
            "第二条 研究生因科研任务不能参加期末考试的，应在考试前 7 个工作日内向研究生院提交缓考申请，"
            "并附导师签字的科研任务说明。\n\n"
            "第三条 研究生创新基金每年 4 月受理申请，申请人须提交研究计划书一式两份。\n"
        ),
        "entry": {
            "document_id": "dis-graduate-defer",
            "policy_group_id": "dis-group",
            "title": "研究生缓考与创新基金管理办法（合成干扰示例）",
            "source_url": "https://example.org/distractor/graduate-defer",
            "source_site": "合成评测示例网站",
            "version_label": "合成干扰 v1",
            "published_at": "2025-01-01",
            "effective_from": "2025-01-01",
            "effective_to": None,
            "scope": {"campus": [], "student_type": ["研究生"], "admission_years": []},
            "is_synthetic": True,
        },
    },
    "dis-scholarship": {
        "text": (
            "【合成测试文件 — 干扰资料，明显标注的合成示例，不代表任何真实学校规定】\n\n"
            "学校奖学金评定细则（合成干扰示例）\n\n"
            "第一条 学校奖学金用于奖励品学兼优的本科生。\n\n"
            "第二条 学校奖学金评定的学分绩点要求为加权平均成绩 85 分以上，且当学年无课程不合格。\n\n"
            "第三条 学校奖学金每学年评定一次，于每年 10 月公布名单。\n"
        ),
        "entry": {
            "document_id": "dis-scholarship",
            "policy_group_id": "dis-group",
            "title": "学校奖学金评定细则（合成干扰示例）",
            "source_url": "https://example.org/distractor/scholarship",
            "source_site": "合成评测示例网站",
            "version_label": "合成干扰 v1",
            "published_at": "2025-01-01",
            "effective_from": "2025-01-01",
            "effective_to": None,
            "scope": {"campus": [], "student_type": ["全日制本科"], "admission_years": []},
            "is_synthetic": True,
        },
    },
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assemble() -> int:
    CORPUS.mkdir(parents=True, exist_ok=True)
    entries = []
    for doc_id, src_dir, src_name in COPIES:
        src_manifest = json.loads(
            (BACKEND / "examples" / src_dir / "manifest.json").read_text(encoding="utf-8"))
        src_entry = next(e for e in src_manifest["documents"] if e["document_id"] == doc_id)
        src_file = BACKEND / "examples" / src_dir / src_name
        dst_name = f"{doc_id}{Path(src_name).suffix}"
        dst_file = CORPUS / dst_name
        shutil.copyfile(src_file, dst_file)
        digest = _sha256(dst_file)
        assert digest == src_entry["sha256"], f"拷贝后哈希不一致: {doc_id}"
        entry = dict(src_entry)
        entry["local_path"] = dst_name
        entry["sha256"] = digest
        entries.append(entry)
    for doc_id, spec in DISTRACTORS.items():
        dst_file = CORPUS / f"{doc_id}.txt"
        dst_file.write_text(spec["text"], encoding="utf-8")
        entry = dict(spec["entry"])
        entry["local_path"] = dst_file.name
        entry["sha256"] = _sha256(dst_file)
        entries.append(entry)
    manifest = {"schema_version": "1.0", "documents": entries}
    (CORPUS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"assembled {len(entries)} docs -> {CORPUS}")
    print("manifest_sha256:", _sha256(CORPUS / "manifest.json"))
    return 0


def dump_blocks(out_path: Path) -> int:
    sys.path.insert(0, str(BACKEND / "src"))
    from campus_assistant.corpus.parse import parse_manifest

    result = parse_manifest(CORPUS / "manifest.json", CORPUS)
    if not result["valid"]:
        print("corpus INVALID:", json.dumps(result["errors"], ensure_ascii=False))
        return 1
    rows = []
    for d in result["documents"]:
        for b in d.get("blocks", []):
            rows.append({
                "document_id": d["document_id"],
                "sha256": d.get("metadata", {}).get("sha256"),
                "parser_version": d.get("parser_version"),
                "block_id": b["block_id"],
                "locator": b.get("locator"),
                "text": b.get("text", ""),
            })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"valid corpus, {len(rows)} blocks -> {out_path}")
    return 0


def fill_spans(draft_path: Path, blocks_path: Path, out_path: Path) -> int:
    """Fill evidence spans from EXACT quote substring in block text.

    The draft carries question_id/evidence_id/block_id/quote (quote authored
    from原文). This only derives char_start/char_end/sha/parser_version.
    Fails loudly when a quote is absent or ambiguous — never guesses.
    """
    blocks = json.loads(blocks_path.read_text(encoding="utf-8"))
    by_block = {(b["document_id"], b["block_id"]): b for b in blocks}
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    filled = 0
    for q in draft.get("questions", []):
        for ev in q.get("evidence", []):
            key = (ev["document_id"], ev["block_id"])
            block = by_block.get(key)
            if block is None:
                print(f"ERROR {q['question_id']}/{ev['evidence_id']}: 块不存在 {key}")
                return 1
            quote = ev["quote"]
            text = block["text"]
            first = text.find(quote)
            if first < 0:
                print(f"ERROR {q['question_id']}/{ev['evidence_id']}: quote 不在原文块中")
                return 1
            if text.find(quote, first + 1) >= 0:
                print(f"ERROR {q['question_id']}/{ev['evidence_id']}: quote 在块内不唯一")
                return 1
            ev["char_start"] = first
            ev["char_end"] = first + len(quote)
            ev["document_sha256"] = block["sha256"]
            ev["parser_version"] = block["parser_version"]
            filled += 1
    out_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"filled {filled} evidence spans -> {out_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="evaluation-v2 语料构建/标注辅助")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("assemble")
    p_dump = sub.add_parser("dump-blocks")
    p_dump.add_argument("--out", required=True)
    p_fill = sub.add_parser("fill-spans")
    p_fill.add_argument("--draft", required=True)
    p_fill.add_argument("--blocks", required=True)
    p_fill.add_argument("--out", required=True)
    args = parser.parse_args()
    if args.cmd == "assemble":
        return assemble()
    if args.cmd == "dump-blocks":
        return dump_blocks(Path(args.out))
    return fill_spans(Path(args.draft), Path(args.blocks), Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
