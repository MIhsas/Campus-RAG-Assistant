"""PDF intake demo: extraction cross-check + candidate package example (T021).

Parses the synthetic PDF fixture, records 原文 → 提取块/页码 → 命中引用
for manual checking, then runs the registration CLI on a local copy to
produce a candidate corpus package example. Local only; no network.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-pdf-intake.py --out-dir <submissions/T021>
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower().replace("-", "") == "utf8":
                continue
            wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", line_buffering=True)
            if stream is sys.stdout:
                sys.stdout = wrapped
            else:
                sys.stderr = wrapped
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(description="PDF 提取对照与候选语料包示例（零网络）")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)

    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.main import create_app
    from fastapi.testclient import TestClient

    corpus = BACKEND / "examples" / "pdf-corpus"
    parsed = parse_manifest(corpus / "manifest.json", corpus)

    app = create_app(manifest_path=corpus / "manifest.json", corpus_root=corpus)
    client = TestClient(app)
    search = client.post("/api/v1/search", json={"query": "复核 分数", "top_k": 5, "mode": "bm25"}).json()
    ask = client.post("/api/v1/ask", json={
        "query": "复核 分数", "top_k": 5, "mode": "bm25", "answer_mode": "extractive",
    }).json()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- 对照表 ----
    lines = [
        "# T021 PDF 原文 → 提取块/页码 → 命中引用 对照",
        "",
        "夹具：`examples/pdf-corpus/sample-text.pdf`（scripts/make-pdf-fixtures.py 生成：fpdf2 + 本机 SimHei，本地合成，无网络）。",
        "提取规则：逐页 pypdf 提取 → 行尾空白去除/换行统一/连续空行折叠（不改写非空白字符）→ 空行分段；",
        "块定位 `pdf_page`（页码 1 基 + 页内段序）；引用跨度相对提取块逐字一致（不宣称与视觉排版等价）。合成资料，不代表真实学校规定。",
        "",
        "| 页 | 提取块（block_id / part） | 提取文本 |",
        "|---|---|---|",
    ]
    doc = next(d for d in parsed["documents"] if d["document_id"] == "syn-pdf-text-001")
    for b in doc["blocks"]:
        loc = b["locator"]
        text = b["text"].replace("\n", "\\n").replace("|", "\\|")
        lines.append(f"| {loc['page']} | {b['block_id']} / part {loc['part']} | {text} |")

    lines += ["", "## 检索命中 → 引用核对（query=\"复核 分数\"）", ""]
    for h in search.get("hits", []):
        c = h["chunk"]
        lines.append(
            f"- 命中 #{h['rank']}：块 {c['block_id']}（PDF 第 {c['locator']['page']} 页）"
            f"→ preview_url `{h['preview_url']}`"
        )
    if not search.get("hits"):
        lines.append("- （无命中）")

    lines += ["", "## ask extractive 证据引用", ""]
    for ev in ask.get("evidence", []):
        lines.append(
            f"- {ev['evidence_id']}：块 {ev['block_id']}（PDF 第 {ev['locator']['page']} 页 · [{ev['char_start']},{ev['char_end']})）"
            f"，quote 与提取块逐字一致，preview_url `{ev['preview_url']}`"
        )

    no_text_err = [e for e in parsed.get("errors", []) if e.get("document_id") == "syn-pdf-notext-001"]
    if no_text_err:
        lines += ["", "## 无文本 PDF 的明确不可用状态", "",
                  f"- syn-pdf-notext-001：`{no_text_err[0]['message']}`（不进索引、不算解析成功）"]

    (out_dir / "pdf-extraction-crosscheck.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- 候选语料包示例（登记 CLI 真实跑一次）----
    import hashlib
    import shutil

    src_pdf = corpus / "sample-text.pdf"
    input_copy = out_dir / "_register-input"
    input_copy.mkdir(exist_ok=True)
    shutil.copyfile(src_pdf, input_copy / "sample-text.pdf")
    meta = {
        "document_id": "candidate-pdf-001",
        "policy_group_id": "candidate-group",
        "title": "候选登记示例（合成 PDF）",
        "source_url": "https://example.org/candidate",
        "source_site": "合成测试示例站",
        "version_label": "候选 v1",
        "published_at": None,
        "effective_from": None,
        "effective_to": None,
        "scope": {"campus": [], "student_type": [], "admission_years": []},
        "is_synthetic": True,
    }
    meta_path = input_copy / "meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    pkg = out_dir / "candidate-package"
    proc = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / "register-corpus.py"),
         "--input", str(input_copy / "sample-text.pdf"), "--meta", str(meta_path),
         "--out-dir", str(pkg)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(BACKEND),
    )
    (out_dir / "candidate-package-report.txt").write_text(proc.stdout, encoding="utf-8")

    print(json.dumps({
        "crosscheck": str(out_dir / "pdf-extraction-crosscheck.md"),
        "candidate_package": str(pkg),
        "register_exit": proc.returncode,
        "register_output_head": proc.stdout.splitlines()[:4],
    }, ensure_ascii=False, indent=2))
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
