"""Emit the T024 mock planner call trace (zero external calls).

Runs the REAL DeepSeekPlanner adapter against a local loopback
chat-completions mock (simulated outputs, trust_env=False) and contrasts it
with the T023 scripted planner. Records rounds, actual actions, result
statuses, attempts and model audit fields (missing → null). Never touches
api.deepseek.com; mock outputs are marked simulated.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES_PATH = BACKEND / "examples" / "procedures" / "procedures.json"

FAKE_KEY = "sk-trace-not-a-real-key"


class MockChatServer:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self._lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                with outer._lock:
                    outer.requests.append(json.loads(self.rfile.read(n).decode("utf-8")))
                    item = outer.script.pop(0) if outer.script else {"content": '{"type":"finish","summary":"mock脚本用尽"}'}
                if "http_status" in item:
                    self.send_response(item["http_status"])
                    self.end_headers()
                    return
                payload = {
                    "id": f"mock-{len(outer.requests)}",
                    "model": "mock-planner（模拟，非真实 DeepSeek）",
                    "choices": [{"message": {"content": item.get("content", "")},
                                 "finish_reason": item.get("finish_reason", "stop")}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                }
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def act_call(tool, args):
    return {"content": json.dumps({"type": "call", "tool": tool, "args": args}, ensure_ascii=False)}


def act_finish(summary):
    return {"content": json.dumps({"type": "finish", "summary": summary}, ensure_ascii=False)}


def main() -> int:
    sys.path.insert(0, str(BACKEND / "src"))
    from campus_assistant.agent.deepseek_planner import DeepSeekPlanner
    from campus_assistant.agent.planner import ScriptedPlanner
    from campus_assistant.agent.tools import RunSnapshot, ToolContext, build_tool_registry
    from campus_assistant.agent.workflow import run_planner_loop
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.procedures.service import load_procedures

    documents = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)["documents"]
    procedures = load_procedures(PROCEDURES_PATH)
    registry = build_tool_registry()
    defer_filters = {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}

    def ctx(procedure_id="proc-apply-defer", query="缓考申请的条件", filters=defer_filters):
        return ToolContext(
            procedures=procedures, documents=documents,
            bm25_index=None, dense_index=None, embedding_service=None,
            available_modes=["bm25"],
            snapshot=RunSnapshot(procedure_id=procedure_id, query=query, filters=filters),
        )

    def record(name, transport, result, mock=None, planner_kind=None):
        events = []
        for e in result["events"]:
            item = {
                "round": e["round"], "kind": e["kind"], "tool": e.get("tool"),
                "status": e["status"], "summary": e.get("summary"), "error": e.get("error"),
                "audit": e.get("audit"),  # 缺失/脚本规划器 = null
            }
            if e.get("action"):
                item["action"] = e["action"]
            events.append(item)
        rec = {
            "name": name,
            "transport": transport,
            "planner_kind": planner_kind or (result.get("planner") or {}).get("kind"),
            "workflow_label": result["workflow_label"],
            "status": result["status"],
            "stop_reason": result.get("stop_reason"),
            "message": result.get("message"),
            "plan_rounds_used": result["plan_rounds_used"],
            "planner_http_attempts": result.get("planner_http_attempts", 0),
            "tool_calls_used": result["tool_calls_used"],
            "snapshot": result["snapshot"],
            "results_summary": {
                "search_hit_count": (result["results"]["search"] or {}).get("hit_count"),
                "draft_procedure_id": (result["results"]["draft"] or {}).get("procedure_id"),
                "draft_saveable": (result["results"]["draft"] or {}).get("saveable"),
            },
            "events": events,
        }
        if mock is not None:
            rec["mock_http_requests"] = len(mock.requests)
        return rec

    trace = {
        "note": "T024 mock 调用轨迹：真实 DeepSeekPlanner 适配器 × 本地 loopback chat-completions mock"
                "（模拟输出，非真实 DeepSeek；trust_env=False；零外部调用）。对照组为 T023 脚本化模拟规划器"
                "（无 HTTP）。attempts=规划 HTTP 尝试次数（零自动重试）；audit 缺失写 null。",
        "runs": [],
    }

    # 1. 适配器完整链：搜索→观察→草稿→finish
    m1 = MockChatServer([
        act_call("search_policy", {"query": "缓考"}),
        act_call("build_checklist_draft", {}),
        act_finish("mock 完成：已检索并整理草稿"),
    ])
    p1 = DeepSeekPlanner(FAKE_KEY, base_url=m1.url(), model="mock-model", trust_env=False)
    c1 = ctx()
    r1 = run_planner_loop(planner=p1, snapshot=c1.snapshot, ctx=c1, registry=registry)
    trace["runs"].append(record(
        "adapter_loopback_full_chain", "DeepSeek 适配器 × loopback mock HTTP", r1, m1))
    trace["runs"][-1]["round2_input_contains_round1_observation"] = (
        "hit_count" in json.dumps(m1.requests[1], ensure_ascii=False)
        and "syn-parse-txt" in json.dumps(m1.requests[1], ensure_ascii=False)
    )
    m1.close()

    # 2. 同一实例两次运行隔离
    m2 = MockChatServer([
        act_call("search_policy", {}), act_call("build_checklist_draft", {}), act_finish("run1"),
        act_call("search_policy", {}), act_call("build_checklist_draft", {}), act_finish("run2"),
    ])
    p2 = DeepSeekPlanner(FAKE_KEY, base_url=m2.url(), model="mock-model", trust_env=False)
    ca = ctx()
    ra = run_planner_loop(planner=p2, snapshot=ca.snapshot, ctx=ca, registry=registry)
    cb = ctx(procedure_id="proc-review-grade", query="成绩复核的流程", filters=None)
    rb = run_planner_loop(planner=p2, snapshot=cb.snapshot, ctx=cb, registry=registry)
    trace["runs"].append(record("adapter_isolation_run_1_defer", "DeepSeek 适配器 × loopback mock HTTP", ra, m2))
    trace["runs"].append(record("adapter_isolation_run_2_grade_review", "DeepSeek 适配器 × loopback mock HTTP", rb, m2))
    m2.close()

    # 3. 放宽条件/换事项被拒 → finish 不伪装成功
    m3 = MockChatServer([
        act_call("search_policy", {"query": "缓考", "filters": {
            "campus": None, "student_type": None, "admission_year": None, "as_of_date": None}}),
        act_call("build_checklist_draft", {"procedure_id": "proc-review-grade"}),
        act_finish("试图改条件与事项"),
    ])
    p3 = DeepSeekPlanner(FAKE_KEY, base_url=m3.url(), model="mock-model", trust_env=False)
    c3 = ctx()
    r3 = run_planner_loop(planner=p3, snapshot=c3.snapshot, ctx=c3, registry=registry)
    trace["runs"].append(record("adapter_reject_relax_and_swap", "DeepSeek 适配器 × loopback mock HTTP", r3, m3))
    m3.close()

    # 4. 成功工具后规划 HTTP 失败 → partial 保留结果
    m4 = MockChatServer([act_call("search_policy", {"query": "缓考"}), {"http_status": 500}])
    p4 = DeepSeekPlanner(FAKE_KEY, base_url=m4.url(), model="mock-model", trust_env=False)
    c4 = ctx()
    r4 = run_planner_loop(planner=p4, snapshot=c4.snapshot, ctx=c4, registry=registry)
    trace["runs"].append(record("adapter_success_then_http_500", "DeepSeek 适配器 × loopback mock HTTP", r4, m4))
    m4.close()

    # 5. 非法 JSON → 可解释失败、零重试
    m5 = MockChatServer([{"content": "垃圾内容不是 JSON"}])
    p5 = DeepSeekPlanner(FAKE_KEY, base_url=m5.url(), model="mock-model", trust_env=False)
    c5 = ctx()
    r5 = run_planner_loop(planner=p5, snapshot=c5.snapshot, ctx=c5, registry=registry)
    trace["runs"].append(record("adapter_illegal_json", "DeepSeek 适配器 × loopback mock HTTP", r5, m5))
    m5.close()

    # 6. T024-R1：直接 finish 无产物 → stopped/明确未完成（模型结束语不作主结论）
    m6 = MockChatServer([act_finish("【模拟】全部办理工作已完成")])
    p6a = DeepSeekPlanner(FAKE_KEY, base_url=m6.url(), model="mock-model", trust_env=False)
    c6a = ctx()
    r6a = run_planner_loop(planner=p6a, snapshot=c6a.snapshot, ctx=c6a, registry=registry)
    trace["runs"].append(record("adapter_direct_finish_no_artifacts", "DeepSeek 适配器 × loopback mock HTTP", r6a, m6))
    trace["runs"][-1]["planner_summary_recorded_only"] = r6a.get("planner_summary")
    m6.close()

    # 7. 对照组：T023 脚本化模拟规划器（无 HTTP，audit 恒 null）
    p6 = ScriptedPlanner([
        {"tool": "search_policy", "args": {}},
        {"tool": "build_checklist_draft", "args": {}},
        {"type": "finish", "summary": "脚本完成（对照组）"},
    ])
    c6 = ctx()
    r6 = run_planner_loop(planner=p6, snapshot=c6.snapshot, ctx=c6, registry=registry)
    trace["runs"].append(record("scripted_planner_contrast", "脚本化模拟规划器（无 HTTP）", r6))

    out = BACKEND.parents[1] / "docs" / "collaboration" / "submissions" / "T024" / "mock-planner-trace.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for r in trace["runs"]:
        print(f"[{r['name']}] {r['status']} stop={r['stop_reason']} "
              f"http_attempts={r['planner_http_attempts']} tools={r['tool_calls_used']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
