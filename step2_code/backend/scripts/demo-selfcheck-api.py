"""Local API demo for the limited self-check (T019).

Runs the real app (parse-corpus + explicitly injected synthetic rule)
through the four documented scenarios and records request/response
examples, plus the rule-vs-original-text cross-check table. Zero external
calls; user answers live only inside each request.

Scenarios:
1. 全满足        — 四项自报“是”
2. 缺考核信息    — 第四项“不确定/未填写”（含未参加考核）→ 待核实
3. 一个不满足    — 第二项“否”
4. 依据被筛除    — 年级 1900（不放宽筛选）→ 依据不足

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-selfcheck-api.py --out-dir <submissions/T019>
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
    parser = argparse.ArgumentParser(description="自查本地 API 演示（零外部请求）")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--corpus", default="examples/parse-corpus")
    parser.add_argument("--rule", default="examples/self-check/rule.json")
    args = parser.parse_args(argv)

    from campus_assistant.main import create_app
    from fastapi.testclient import TestClient

    corpus = Path(args.corpus)
    app = create_app(
        manifest_path=corpus / "manifest.json",
        corpus_root=corpus,
        self_check_path=Path(args.rule),
    )
    client = TestClient(app)

    calls = []

    def rec(name, method, url, body, resp):
        calls.append({
            "name": name, "method": method, "url": url, "request": body,
            "status_code": resp.status_code, "response": resp.json(),
        })

    rec("rule-info", "GET", "/api/v1/self-check/rule", None,
        client.get("/api/v1/self-check/rule"))

    YES = "yes"
    SCENARIOS = [
        ("scenario1-all-satisfied",
         {"answers": {"apply_at_first_year_end": YES, "no_discipline_record": YES,
                      "rank_top_30": YES, "passed_assessment": YES}}),
        ("scenario2-assessment-unknown",
         {"answers": {"apply_at_first_year_end": YES, "no_discipline_record": YES,
                      "rank_top_30": YES, "passed_assessment": "unknown"}}),
        ("scenario3-one-unsatisfied",
         {"answers": {"apply_at_first_year_end": YES, "no_discipline_record": "no",
                      "rank_top_30": YES, "passed_assessment": YES}}),
        ("scenario4-basis-excluded",
         {"filters": {"admission_year": 1900},
          "answers": {"apply_at_first_year_end": YES, "no_discipline_record": YES,
                       "rank_top_30": YES, "passed_assessment": YES}}),
    ]
    for name, body in SCENARIOS:
        rec(name, "POST", "/api/v1/self-check", body,
            client.post("/api/v1/self-check", json=body))

    out = {
        "demo": "T019 self-check local API demo (synthetic rule + parse-corpus)",
        "evidence_kind": "本地 API 示例（合成规则、确定性判断）；不代表学校审核结果，零外部调用",
        "external_model_calls": 0,
        "corpus": args.corpus,
        "rule": args.rule,
        "calls": calls,
        "notes": [
            "四项条件逐项 返回填报/状态/解释/原文引用；未知不计为满足。",
            "依据被筛除（场景 4）总结为“依据不足，无法完成自查”，不利用失效原文算通过。",
            "用户填报仅在请求内处理，不写报告/日志/localStorage。",
        ],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "selfcheck-api-demo.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 规则原文对照
    rule_resp = next(c["response"] for c in calls if c["name"] == "rule-info")
    lines = [
        "# T019 规则原文对照（转专业条件自查 · 合成演示）",
        "",
        "规则配置 `examples/self-check/rule.json`（rule_version 1.0）显式绑定 parse-corpus 第五条各句；",
        "跨度均经当前解析块切片逐条核对。合成资料，不代表学校现行政策。",
        "",
        "| 项 | 自查问题（三态） | 原文引用（模板 quote） | 块/区间 | 满足判定 |",
        "|---|---|---|---|---|",
    ]
    for it in rule_resp["items"]:
        c = it["citation"]
        quote = c["quote"].replace("\n", "\\n").replace("|", "\\|")
        lines.append(
            f"| {it['item_id']} {it['title']} | {it['question']} | “{quote}” | "
            f"{c['block_id']} [{c['char_start']},{c['char_end']}) | 自报“是”=满足；“否”=不满足；"
            f"“不确定/未填写”=待核实（未知不计满足） |"
        )
    lines += [
        "",
        "注：排名项按用户自报“是否前 30%”三态判定，不换算并列/取整；未参加考核记为待核实，",
        "与明确未通过（否）区分。依据未通过准入/缺失/哈希变化时整体为“依据不足，无法完成自查”。",
    ]
    (out_dir / "rule-text-crosscheck.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    verdicts = {
        c["name"]: c["response"].get("summary_status")
        for c in calls if c["method"] == "POST"
    }
    print(json.dumps({
        "selfcheck_api_demo": str(out_dir / "selfcheck-api-demo.json"),
        "rule_text_crosscheck": str(out_dir / "rule-text-crosscheck.md"),
        "calls_recorded": len(calls),
        "verdicts": verdicts,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
