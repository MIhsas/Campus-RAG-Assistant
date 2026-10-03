"""Emit a local call trace for T023 submissions (zero external calls).

Runs the fixed workflow and the explicitly-injected simulated planner over
the synthetic example corpus and dumps their real tool events/counts to JSON.
No model calls, no downloads, no network.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES_PATH = BACKEND / "examples" / "procedures" / "procedures.json"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    sys.path.insert(0, str(BACKEND / "src"))
    from campus_assistant.agent.planner import ScriptedPlanner
    from campus_assistant.agent.tools import RunSnapshot, ToolContext, build_tool_registry
    from campus_assistant.agent.workflow import run_fixed_workflow, run_planner_loop
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.procedures.service import load_procedures

    result = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
    documents = result["documents"]
    procedures = load_procedures(PROCEDURES_PATH)
    filters = {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}
    registry = build_tool_registry()

    def ctx(**kw):
        snap = RunSnapshot(
            procedure_id=kw.get("procedure_id", "proc-apply-defer"),
            query=kw.get("query", "缓考申请的条件"),
            filters=kw.get("filters", filters),
        )
        return ToolContext(
            procedures=procedures, documents=documents,
            bm25_index=None, dense_index=None, embedding_service=None,
            available_modes=["bm25"], snapshot=snap,
        )

    trace = {
        "note": "本地调用轨迹：合成示例语料 + 显式注入的脚本化模拟规划器。零外部模型调用，无下载。"
                "工具调用次数与事件为真实运行结果；不代表真实 Agent/DeepSeek 规划质量。",
        "corpus": "examples/parse-corpus（合成）",
        "runs": [],
    }

    # Run 1: normal fixed workflow 检索→缓考草稿
    c1 = ctx()
    out1 = run_fixed_workflow(snapshot=c1.snapshot, ctx=c1, registry=registry)
    trace["runs"].append({"name": "normal_fixed_defer_draft", "kind": "fixed", "result": out1})

    # Run 2: simulated planner happy path
    c2 = ctx()
    p2 = ScriptedPlanner([
        {"tool": "search_policy", "args": {}},
        {"tool": "build_checklist_draft", "args": {}},
        {"type": "finish", "summary": "模拟脚本完成：检索并整理草稿"},
    ])
    out2 = run_planner_loop(planner=p2, snapshot=c2.snapshot, ctx=c2, registry=registry)
    trace["runs"].append({"name": "simulated_planner_happy", "kind": "simulated_planner", "result": out2})

    # Run 3: unknown tool + invalid args (rejected before business)
    c3 = ctx()
    p3 = ScriptedPlanner([
        {"tool": "not_a_tool", "args": {}},
        {"tool": "search_policy", "args": {"top_k": 99}},
        {"type": "finish"},
    ])
    out3 = run_planner_loop(planner=p3, snapshot=c3.snapshot, ctx=c3, registry=registry)
    trace["runs"].append({"name": "simulated_unknown_tool_and_bad_args", "kind": "simulated_planner", "result": out3})

    # Run 4: scope relaxation attempt (rejected) + no-progress stop
    c4 = ctx()
    p4 = ScriptedPlanner([
        {"tool": "search_policy", "args": {"query": "缓考", "filters": {
            "campus": None, "student_type": None, "admission_year": None, "as_of_date": None}}},
        {"tool": "search_policy", "args": {"query": "缓考"}},
        {"tool": "search_policy", "args": {"query": "缓考"}},
        {"type": "finish"},
    ])
    out4 = run_planner_loop(planner=p4, snapshot=c4.snapshot, ctx=c4, registry=registry)
    trace["runs"].append({"name": "simulated_relax_rejected_then_no_progress", "kind": "simulated_planner", "result": out4})

    # Run 5/6 (T023-R1): 同一模拟规划器实例连续两次运行，各自独立执行
    shared = ScriptedPlanner([
        {"tool": "search_policy", "args": {}},
        {"tool": "build_checklist_draft", "args": {}},
        {"type": "finish", "summary": "模拟脚本完成"},
    ])
    c5 = ctx(procedure_id="proc-apply-defer", query="缓考申请的条件", filters=filters)
    out5 = run_planner_loop(planner=shared, snapshot=c5.snapshot, ctx=c5, registry=registry)
    trace["runs"].append({"name": "shared_planner_run_1_defer", "kind": "simulated_planner", "result": out5})
    c6 = ctx(procedure_id="proc-review-grade", query="成绩复核的流程", filters=None)
    out6 = run_planner_loop(planner=shared, snapshot=c6.snapshot, ctx=c6, registry=registry)
    trace["runs"].append({"name": "shared_planner_run_2_grade_review", "kind": "simulated_planner", "result": out6})

    out_path = BACKEND.parents[1] / "docs" / "collaboration" / "submissions" / "T023" / "call-trace.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Console summary
    for r in trace["runs"]:
        res = r["result"]
        print(f"[{r['name']}] status={res['status']} stop={res.get('stop_reason')} "
              f"tool_calls={res['tool_calls_used']} rounds={res['plan_rounds_used']}")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
