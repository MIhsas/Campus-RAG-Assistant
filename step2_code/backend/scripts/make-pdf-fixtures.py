"""Generate the synthetic PDF demo fixtures (T021).

Creates examples/pdf-corpus/ with:
- sample-text.pdf   — 2-page Chinese text PDF (numbers, negations, page marks)
- sample-no-text.pdf — drawing-only PDF (no extractable text)
- manifest.json     — synthetic corpus manifest (is_synthetic=true)
- README.txt        — generation method record

Generation: fpdf2 with the local Windows SimHei font (system font, used
only to synthesize this fixture; nothing is fetched from the network).
This is synthetic test material — not school policy, not real corpus.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\make-pdf-fixtures.py [--out-dir examples/pdf-corpus]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/c/Windows/Fonts/simhei.ttf"),
]


def _find_font() -> Path:
    for p in FONT_CANDIDATES:
        if p.is_file():
            return p
    raise SystemExit("未找到本机 SimHei 字体（C:/Windows/Fonts/simhei.ttf），无法生成夹具")


def build_text_pdf(out: Path) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pdf.add_font("simhei", fname=str(_find_font()))
    pdf.add_page()
    pdf.set_font("simhei", size=12)
    pdf.multi_cell(w=0, h=8, new_x="LMARGIN", new_y="NEXT", text="【合成测试 PDF — 仅供解析演示，不代表真实学校规定】")
    pdf.ln(2)
    pdf.multi_cell(w=0, h=8, new_x="LMARGIN", new_y="NEXT", text="第一章 总则")
    pdf.multi_cell(w=0, h=8, new_x="LMARGIN", new_y="NEXT", text="第一条 成绩复核申请须在成绩公布后 10 个工作日内提出。")
    pdf.multi_cell(w=0, h=8, new_x="LMARGIN", new_y="NEXT", text="第二条 复核仅核对分数，不重新评阅试卷。")
    pdf.add_page()
    pdf.set_font("simhei", size=12)
    pdf.multi_cell(w=0, h=8, new_x="LMARGIN", new_y="NEXT", text="第二章 补充")
    pdf.multi_cell(w=0, h=8, new_x="LMARGIN", new_y="NEXT", text="第三条 缓考申请不得由他人代办。")
    pdf.multi_cell(w=0, h=8, new_x="LMARGIN", new_y="NEXT", text="第四条 2024 级学生适用本示例，2025 级另行通知。")
    pdf.output(str(out))


def build_no_text_pdf(out: Path) -> None:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.7)
    pdf.line(20, 20, 190, 20)
    pdf.line(20, 40, 190, 60)
    pdf.rect(30, 80, 120, 60)
    pdf.output(str(out))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成合成 PDF 演示夹具（本地生成，无网络）")
    parser.add_argument("--out-dir", default="examples/pdf-corpus")
    args = parser.parse_args(argv)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    text_pdf = out / "sample-text.pdf"
    no_text_pdf = out / "sample-no-text.pdf"
    build_text_pdf(text_pdf)
    build_no_text_pdf(no_text_pdf)

    docs = []
    for fname, did, title in [
        ("sample-text.pdf", "syn-pdf-text-001", "合成测试 PDF（两页文本示例）"),
        ("sample-no-text.pdf", "syn-pdf-notext-001", "合成测试 PDF（无文本示例）"),
    ]:
        sha = hashlib.sha256((out / fname).read_bytes()).hexdigest()
        docs.append({
            "document_id": did,
            "policy_group_id": "syn-pdf-group",
            "title": title,
            "source_url": f"https://example.org/pdf/{did}",
            "source_site": "合成测试示例站",
            "local_path": fname,
            "sha256": sha,
            "version_label": "合成演示 v1",
            "published_at": "2025-01-01",
            "effective_from": "2025-03-01",
            "effective_to": None,
            "scope": {"campus": ["成都校区"], "student_type": ["全日制本科"], "admission_years": [2023, 2024]},
            "is_synthetic": True,
        })
    (out / "manifest.json").write_text(
        json.dumps({"schema_version": "1.0", "documents": docs}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "README.txt").write_text(
        "合成 PDF 演示夹具（T021）\n"
        "生成方式：scripts/make-pdf-fixtures.py，fpdf2 + 本机 Windows SimHei 字体本地生成，无网络获取。\n"
        "sample-text.pdf：两页中文文本（含数字 10/2024、否定词 不/不得、页内章节标记），用于逐页提取与引用核对。\n"
        "sample-no-text.pdf：仅线条/矩形，无任何文本，用于验证“未提取到文本”不可用状态。\n"
        "合成资料，不代表真实学校规定；不改旧 parse/comparison 语料与 gold。\n",
        encoding="utf-8",
    )
    for p in (text_pdf, no_text_pdf):
        print(f"{p.name}: {p.stat().st_size} bytes, sha256={hashlib.sha256(p.read_bytes()).hexdigest()[:16]}…")
    print("fixtures written to", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
