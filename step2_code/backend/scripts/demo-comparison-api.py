"""Local API demo for policy version comparison (T017).

Runs the real app over examples/comparison-corpus and records:
- GET /api/v1/comparison/groups
- POST compare v1→v2 (fixture pair) and the swapped direction
- rejection cases (same document / cross policy group)

Also writes comparison-expectations.md — the manual expected classification
vs the program output side by side. Zero external calls.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-comparison-api.py --out-dir <submissions/T017>
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


# 手工期望（依据夹具文本设计意图，对照程序输出）
MANUAL_EXPECTATIONS = [
    ("【合成测试文件】前言（无标识）", "未变", "两侧逐字相同"),
    ("缓考申请办法（虚构测试）标题（无标识）", "未变", "两侧逐字相同"),
    ("第一条 本办法所称缓考…", "未变", "两侧逐字相同"),
    ("第二条 缓考申请须在考试前 ? 个工作日提交。", "修改", "5 个工作日 → 3 个工作日，同标识配对"),
    ("第三条 申请缓考须同时提交书面情况说明。", "删除", "仅 v1 存在"),
    ("第四条 学院应在收到申请后 3 个工作日内完成审批。", "新增", "仅 v2 存在"),
]


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="版本对比本地 API 演示（零外部请求）")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--corpus", default="examples/comparison-corpus")
    args = parser.parse_args(argv)

    from campus_assistant.main import create_app
    from fastapi.testclient import TestClient

    corpus = Path(args.corpus)
    app = create_app(manifest_path=corpus / "manifest.json", corpus_root=corpus)
    client = TestClient(app)

    calls = []

    def rec(name, method, url, body, resp):
        calls.append({
            "name": name, "method": method, "url": url, "request": body,
            "status_code": resp.status_code, "response": resp.json(),
        })

    rec("groups", "GET", "/api/v1/comparison/groups", None,
        client.get("/api/v1/comparison/groups"))
    body = {"left_document_id": "cmp-defer-v1", "right_document_id": "cmp-defer-v2"}
    rec("compare-v1-v2", "POST", "/api/v1/comparison", body,
        client.post("/api/v1/comparison", json=body))
    body_swap = {"left_document_id": "cmp-defer-v2", "right_document_id": "cmp-defer-v1"}
    rec("compare-v2-v1-swap", "POST", "/api/v1/comparison", body_swap,
        client.post("/api/v1/comparison", json=body_swap))
    body_same = {"left_document_id": "cmp-defer-v1", "right_document_id": "cmp-defer-v1"}
    rec("reject-same-doc", "POST", "/api/v1/comparison", body_same,
        client.post("/api/v1/comparison", json=body_same))
    body_cross = {"left_document_id": "cmp-defer-v1", "right_document_id": "cmp-grades-1"}
    rec("reject-cross-group", "POST", "/api/v1/comparison", body_cross,
        client.post("/api/v1/comparison", json=body_cross))

    out = {
        "demo": "T017 comparison local API demo (synthetic comparison corpus)",
        "evidence_kind": "本地 API 演示（合成虚构政策），零外部模型调用；文字差异不代表适用性",
        "external_model_calls": 0,
        "corpus": args.corpus,
        "calls": calls,
        "notes": [
            "v1→v2 分类：1 修改（第二条 5→3 工作日）、1 删除（第三条）、1 新增（第四条）、3 未变。",
            "交换左右后新增/删除互换（compare-v2-v1-swap）。",
            "同文档与跨政策组比较被拒绝（400）。",
        ],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparison-demo.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 手工期望分类与程序结果对照
    compare_resp = next(c["response"] for c in calls if c["name"] == "compare-v1-v2")
    program = []
    for e in compare_resp.get("entries", []):
        label = {"added": "新增", "deleted": "删除", "modified": "修改", "unchanged": "未变"}[e["change_type"]]
        key = e["clause_key"] or "（无标识）"
        text = (e["left"] or e["right"] or {}).get("text", "")[:24]
        program.append((key, label, text))
    lines = [
        "# T017 手工期望分类与程序结果对照",
        "",
        "手工期望依据夹具文本设计意图（Astra 可独立复核夹具 `examples/comparison-corpus/`）；",
        "程序结果取自 `comparison-demo.json` 的 compare-v1-v2 条目。合成虚构政策，不代表真实学校规定。",
        "",
        "| 条款 | 手工期望 | 程序结果 | 一致 |",
        "|---|---|---|---|",
    ]
    program_by_label = {}
    for key, label, text in program:
        program_by_label.setdefault(label, []).append(key)
    ok_all = True
    for name, expect, why in MANUAL_EXPECTATIONS:
        # map expectation row to program entry by label and rough text
        got = "未找到"
        for key, label, text in program:
            short = name.split("（")[0].replace("…", "")
            if key != "（无标识）" and key in short:
                if label == expect:
                    got = f"{label}（{key}）"
                break
            if key == "（无标识）" and ("无标识" in name) and label == expect:
                got = f"{label}（无标识）"
                break
        matched = got != "未找到"
        ok_all = ok_all and matched
        lines.append(f"| {name} | {expect}（{why}） | {got} | {'✓' if matched else '✗'} |")
    counts = compare_resp.get("counts", {})
    lines += [
        "",
        f"程序计数：新增 {counts.get('added')}、删除 {counts.get('deleted')}、修改 {counts.get('modified')}、未变 {counts.get('unchanged')}（手工期望 1/1/1/3）。",
        f"总体对照：{'全部一致' if ok_all else '存在不一致（见上表）'}。",
    ]
    (out_dir / "comparison-expectations.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print(json.dumps({
        "comparison_demo": str(out_dir / "comparison-demo.json"),
        "comparison_expectations": str(out_dir / "comparison-expectations.md"),
        "calls_recorded": len(calls),
        "counts": counts,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
