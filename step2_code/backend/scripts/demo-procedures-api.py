"""Local API demo for procedure guides (T016).

Runs the real app (parse-corpus + explicitly-enabled synthetic procedures
template) through TestClient and records:
- GET /api/v1/procedures
- POST drafts for both items under different filters (including the refused
  2023 成绩复核 case)
- POST verify (unchanged / changed)
- the citation cross-check table (原文 → 清单步骤)

Zero external calls. Writes api-demo.json and citation-crosscheck.md.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-procedures-api.py --out-dir <submissions/T016>
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path


def _ensure_utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") == "utf8":
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="办事清单本地 API 演示（零外部请求）")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--corpus", default="examples/parse-corpus")
    parser.add_argument("--procedures", default="examples/procedures/procedures.json")
    args = parser.parse_args(argv)

    from campus_assistant.main import create_app
    from fastapi.testclient import TestClient

    corpus = Path(args.corpus)
    app = create_app(
        manifest_path=corpus / "manifest.json",
        corpus_root=corpus,
        procedures_path=Path(args.procedures),
    )
    client = TestClient(app)

    calls = []

    def rec(name, method, url, body, resp):
        calls.append({
            "name": name, "method": method, "url": url, "request": body,
            "status_code": resp.status_code, "response": resp.json(),
        })

    rec("list", "GET", "/api/v1/procedures", None, client.get("/api/v1/procedures"))

    drafts = {}
    for name, pid, filters in [
        ("draft-defer-2023", "proc-apply-defer", {"admission_year": 2023}),
        ("draft-defer-2024", "proc-apply-defer", {"admission_year": 2024}),
        ("draft-grade-2024", "proc-review-grade", {"admission_year": 2024}),
        ("draft-grade-2023", "proc-review-grade", {"admission_year": 2023}),
    ]:
        body = {"filters": filters}
        r = client.post(f"/api/v1/procedures/{pid}/draft", json=body)
        rec(name, "POST", f"/api/v1/procedures/{pid}/draft", body, r)
        drafts[name] = r.json()

    # verify: unchanged (exact snapshot) and changed (older template version)
    snap_source = drafts["draft-grade-2024"]
    snapshot = {
        "template_version": snap_source["template_version"],
        "filters": {"admission_year": 2024},
        "steps": [
            {"step_id": s["step_id"], "title": s["title"], "citations": s["citations"]}
            for s in snap_source["steps"]
        ],
    }
    rec("verify-unchanged", "POST", "/api/v1/procedures/proc-review-grade/verify",
        snapshot, client.post("/api/v1/procedures/proc-review-grade/verify", json=snapshot))
    old = dict(snapshot)
    old["template_version"] = "0.9"
    rec("verify-changed-version", "POST", "/api/v1/procedures/proc-review-grade/verify",
        old, client.post("/api/v1/procedures/proc-review-grade/verify", json=old))

    out = {
        "demo": "T016 procedures local API demo (synthetic template explicitly enabled)",
        "evidence_kind": "本地 API 演示（合成模板+合成语料），零外部模型调用；不代表学校现行办事指南",
        "external_model_calls": 0,
        "corpus": args.corpus,
        "procedures_template": args.procedures,
        "calls": calls,
        "notes": [
            "缓考申请：2023 与 2024 均可保存（2023 的材料信息回退“资料未说明”，不混入 2024 专属 DOCX 内容）。",
            "成绩复核：2024 可保存；2023 的必要来源（2024 专属 DOCX）被筛选排除 → saveable=false，明确“资料不足/依据需更新”。",
            "verify：同快照 unchanged；模板版本不同 → changed（提示复核，不覆盖用户进度）。",
        ],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "api-demo.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # citation cross-check table (原文 → 清单步骤)
    lines = [
        "# T016 引用核对表（原文 → 清单步骤）",
        "",
        "生成方式：`scripts/demo-procedures-api.py` 本地运行；跨度均经当前 parse-corpus 原块切片逐条核对。",
        "合成资料，不代表学校现行政策。",
        "",
        "| 事项 | 步骤 | 引用文档/块 | 字符区间 | 原文（模板 quote） | 与原块切片一致 | 必要引用 |",
        "|---|---|---|---|---|---|---|",
    ]
    for key, d in drafts.items():
        if d.get("status") is None:
            continue
        for s in d.get("steps", []):
            for c in s.get("citations", []):
                usable = c.get("usable", c.get("status") == "ok")
                if usable and c.get("quote"):
                    quote_cell = "“" + c["quote"].replace("\n", "\\n").replace("|", "\\|") + "”"
                    span_cell = "是（span_ok）"
                else:
                    quote_cell = "（未准入/失效：不作为可用依据，原文内容不输出）"
                    span_cell = c.get("status", "?")
                lines.append(
                    f"| {d['title']} | {s['step_id']} {s['title']} | "
                    f"{c['document_id']}/{c['block_id']} | [{c['char_start']},{c['char_end']}) | "
                    f"{quote_cell} | {span_cell} | "
                    f"{'是' if c['required'] else '否（可降级）'} |"
                )
    lines += [
        "",
        "注：未通过核对（被筛除/缺失/哈希变化/跨度不符）的引用不携带原文内容、不作为可用办理依据，",
        "仅保留状态与来源标识作诊断；可选引用被采用后同样进入 verify 跟踪。",
        "必要引用任一失败时草稿 saveable=false，不输出冒充完整的可保存清单。",
    ]
    (out_dir / "citation-crosscheck.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "api_demo": str(out_dir / "api-demo.json"),
        "citation_crosscheck": str(out_dir / "citation-crosscheck.md"),
        "calls_recorded": len(calls),
        "draft_saveable": {k: v.get("saveable") for k, v in drafts.items()},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
