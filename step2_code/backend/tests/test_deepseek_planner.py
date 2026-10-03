"""DeepSeek structured planner tests (T024) — focused, loopback mock only.

The REAL adapter (DeepSeekPlanner, real HTTP protocol code) is exercised
against a local loopback chat-completions mock (trust_env=False). The mock
is clearly labelled simulated and never enters the normal startup path;
tests can never reach api.deepseek.com. Zero external model calls.

Covers the task's focused acceptance:
- full chain 搜索→观察→草稿→finish via the adapter; round-2 input contains
  round-1 actual observations; results/citations match direct service;
- same app two runs independent, second run's conditions not crossed;
- model trying to relax filters or swap the user's procedure is rejected,
  original conditions kept;
- one successful tool then planning failure → partial, results kept;
  illegal JSON / truncation / one HTTP failure covered;
- startup/status/fixed workflow issue ZERO planning requests; attempts
  budget and zero retries verified by counts.
"""

from __future__ import annotations

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.agent.deepseek_planner import (
    DeepSeekPlanner,
    PlannerActionError,
    PlannerBadJSONError,
    PlannerHTTPError,
    PlannerTruncatedError,
    planner_from_env,
)
from campus_assistant.procedures.service import build_draft, load_procedures
from campus_assistant.qa.deepseek import chat_completions_url

BACKEND = Path(__file__).resolve().parents[1]
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES_PATH = BACKEND / "examples" / "procedures" / "procedures.json"

_spec = importlib.util.spec_from_file_location(
    "serve_corpus", BACKEND / "scripts" / "serve-corpus.py"
)
serve_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve_corpus)

FAKE_KEY = "sk-test-not-a-real-key"


# --------------------------------------------------------------- loopback mock

class MockChatServer:
    """Loopback chat-completions mock（模拟输出，非真实 DeepSeek）.

    script items: {"content": <action json str>, "finish_reason": "stop"|"length"}
                | {"http_status": 500}
    Captures every request payload for observation assertions.
    """

    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self._lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(n)
                with outer._lock:
                    outer.requests.append(json.loads(body.decode("utf-8")))
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
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def act_call(tool, args):
    return {"content": json.dumps({"type": "call", "tool": tool, "args": args}, ensure_ascii=False)}


def act_finish(summary="mock 脚本完成"):
    return {"content": json.dumps({"type": "finish", "summary": summary}, ensure_ascii=False)}


def act_awaiting(needs, message):
    return {"content": json.dumps({"type": "awaiting_input", "needs": needs, "message": message}, ensure_ascii=False)}


@pytest.fixture()
def mock_server():
    servers = []

    def make(script):
        s = MockChatServer(script)
        servers.append(s)
        return s

    yield make
    for s in servers:
        s.close()


# ------------------------------------------------------------------ fixtures

def _app(planner):
    app, _ = serve_corpus.build_app(
        manifest=PARSE_CORPUS / "manifest.json", corpus_root=PARSE_CORPUS,
        procedures=PROCEDURES_PATH, planner=planner,
    )
    return app


def _planner(mock, **kw):
    return DeepSeekPlanner(FAKE_KEY, base_url=mock.url(), model="mock-model",
                           trust_env=False, **kw)


def _defer_body(query="缓考申请的条件"):
    return {
        "procedure_id": "proc-apply-defer", "query": query,
        "filters": {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None},
    }


@pytest.fixture(scope="module")
def documents():
    from campus_assistant.corpus.parse import parse_manifest

    r = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
    assert r["valid"]
    return r["documents"]


@pytest.fixture(scope="module")
def procedures():
    return load_procedures(PROCEDURES_PATH)


# ------------------------------------------------ adapter parsing (no network)

class TestAdapterParsing:
    def _one(self, content, finish_reason="stop"):
        class StubResp:
            status_code = 200

            @staticmethod
            def json():
                return {"id": "stub-1", "model": "stub", "choices": [
                    {"message": {"content": content}, "finish_reason": finish_reason}]}

        class StubClient:
            @staticmethod
            def post(url, json=None, headers=None, timeout=None):
                return StubResp()

        return DeepSeekPlanner(FAKE_KEY, base_url="http://127.0.0.1:9", trust_env=False, client=StubClient())

    def test_valid_call_action_with_null_audit_fields(self):
        p = self._one('{"type": "call", "tool": "search_policy", "args": {}}')
        a = p.next_action(round_no=1, snapshot=_snap(), observations=[])
        assert a["type"] == "call" and a["tool"] == "search_policy"
        assert a["audit"]["request_id"] == "stub-1"
        # 缺失的审计字段写 null，不捏造（stub 未提供 usage）
        assert a["audit"]["usage"] is None and a["audit"]["model"] == "stub"
        # 适配器不索取/不保存 Thought
        assert "thought" not in json.dumps(a, ensure_ascii=False).lower()

    def test_illegal_json_raises(self):
        p = self._one("这不是 JSON")
        with pytest.raises(PlannerBadJSONError):
            p.next_action(round_no=1, snapshot=_snap(), observations=[])

    def test_truncated_raises(self):
        p = self._one('{"type": "finish", "summary": "x', finish_reason="length")
        with pytest.raises(PlannerTruncatedError) as ei:
            p.next_action(round_no=1, snapshot=_snap(), observations=[])
        # T025-R1：失败轮已收到的信封审计字段保留（缺失写 null）
        audit = ei.value.audit
        assert audit is not None and audit["request_id"] == "stub-1"
        assert audit["finish_reason"] == "length" and audit["model"] == "stub"
        assert audit["max_tokens"] == 300

    def test_http_failure_raises_with_safe_message(self):
        class Resp:
            status_code = 500

        class Client:
            @staticmethod
            def post(url, json=None, headers=None, timeout=None):
                return Resp()

        p = DeepSeekPlanner(FAKE_KEY, base_url="http://127.0.0.1:9", trust_env=False, client=Client())
        with pytest.raises(PlannerHTTPError) as ei:
            p.next_action(round_no=1, snapshot=_snap(), observations=[])
        assert "HTTP 500" in ei.value.user_message
        assert FAKE_KEY not in ei.value.user_message

    def test_unknown_action_type_raises(self):
        p = self._one('{"type": "think", "content": "内部思考"}')
        with pytest.raises(PlannerActionError):
            p.next_action(round_no=1, snapshot=_snap(), observations=[])


def _snap():
    from campus_assistant.agent.tools import RunSnapshot

    return RunSnapshot(procedure_id="proc-apply-defer", query="缓考申请的条件",
                       filters={"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None})


# ------------------------------------------------------ loopback full chain

class TestLoopbackFullChain:
    def test_search_observe_draft_finish_and_round2_observation(self, mock_server, documents, procedures):
        mock = mock_server([
            act_call("search_policy", {"query": "缓考"}),
            act_call("build_checklist_draft", {}),
            act_finish("mock 完成：已检索并整理草稿"),
        ])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        r = c.post("/api/v1/agent/plan/run", json=_defer_body())
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "completed"
        assert d["tool_calls_used"] == 2
        assert d["planner_http_attempts"] == 3
        assert d["workflow_kind"] == "deepseek_planner"
        assert "未联调验证" in d["workflow_label"]

        # 结果/引用对照直接 service
        direct = build_draft(procedures, "proc-apply-defer", _snap().filters, documents)
        got = d["results"]["draft"]
        assert got["saveable"] == direct["saveable"] is True
        assert [c2["quote"] for s in got["steps"] for c2 in s["citations"]] == \
               [c2["quote"] for s in direct["steps"] for c2 in s["citations"]]

        # 第二轮输入确含第一轮实际观察（真实检索结果摘要，非虚构）
        assert len(mock.requests) == 3
        r2_user = mock.requests[1]["messages"][1]["content"]
        assert "第 2 轮" in r2_user
        assert "hit_count" in r2_user
        assert "syn-parse-txt" in r2_user, "第二轮须含第一轮真实命中来源标识"
        # 观察是数据不是指令
        assert "资料数据" in mock.requests[1]["messages"][1]["content"]
        # 提示词含工具声明与配置事项列表，禁止猜 ID
        sys_prompt = mock.requests[0]["messages"][0]["content"]
        assert "search_policy" in sys_prompt and "build_checklist_draft" in sys_prompt
        assert "proc-apply-defer" in sys_prompt and "禁止凭空猜测" in sys_prompt
        # 审计字段来自 mock（模拟），缺失写 null 的口径由模型字段透传保证
        assert d["events"][0]["audit"]["model"] == "mock-planner（模拟，非真实 DeepSeek）"

    def test_two_runs_same_app_independent(self, mock_server):
        script = [
            act_call("search_policy", {}), act_call("build_checklist_draft", {}), act_finish("run1"),
            act_call("search_policy", {}), act_call("build_checklist_draft", {}), act_finish("run2"),
        ]
        mock = mock_server(script)
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        r1 = c.post("/api/v1/agent/plan/run", json=_defer_body("缓考申请的条件"))
        body2 = {"procedure_id": "proc-review-grade", "query": "成绩复核的流程", "filters": None}
        r2 = c.post("/api/v1/agent/plan/run", json=body2)
        d1, d2 = r1.json(), r2.json()
        assert d1["tool_calls_used"] == 2 and d2["tool_calls_used"] == 2
        assert d1["results"]["draft"]["procedure_id"] == "proc-apply-defer"
        assert d2["results"]["draft"]["procedure_id"] == "proc-review-grade"
        assert d2["results"]["search"]["query"] == "成绩复核的流程"
        assert d2["snapshot"]["filters"] is None
        # 第二次请求输入属第二次快照，不含第一次条件
        req2 = json.dumps(mock.requests[3], ensure_ascii=False)
        assert "成绩复核" in req2 and "proc-review-grade" in req2
        assert "admission_year\": 2023" not in req2 and "年级=2023" not in req2


class TestGuardsAndPartial:
    def test_relax_and_swap_rejected_original_conditions_kept(self, mock_server):
        mock = mock_server([
            act_call("search_policy", {"query": "缓考", "filters": {
                "campus": None, "student_type": None, "admission_year": None, "as_of_date": None}}),
            act_call("build_checklist_draft", {"procedure_id": "proc-review-grade"}),
            act_finish("试图改条件与事项"),
        ])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        r = c.post("/api/v1/agent/plan/run", json=_defer_body())
        d = r.json()
        # 两次都在业务调用前被拒；原条件快照不丢
        kinds = [(e["kind"], e["status"]) for e in d["events"] if e["kind"].startswith("tool")]
        assert kinds == [("tool_rejected", "rejected"), ("tool_rejected", "rejected")]
        assert d["tool_calls_used"] == 0
        assert d["snapshot"]["filters"]["admission_year"] == 2023
        # T024-R1：无任何产物 → stopped/明确未完成，模型结束语不作主结论
        assert d["status"] == "stopped", "finish 不得把被拒动作伪装成全部成功"
        assert "任务未完成" in (d["message"] or "") and "未补调用" in (d["message"] or "")
        assert "试图改条件与事项" not in (d["message"] or ""), "模型结束语不作主结论"
        errs = " ".join(e["error"] or "" for e in d["events"])
        assert "不得放宽或改写" in errs and "不得擅自更换事项" in errs

    def test_success_then_planner_http_failure_keeps_partial(self, mock_server):
        mock = mock_server([
            act_call("search_policy", {"query": "缓考"}),
            {"http_status": 500},
        ])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        r = c.post("/api/v1/agent/plan/run", json=_defer_body())
        d = r.json()
        assert d["status"] == "partial"
        assert d["stop_reason"] == "planner_error"
        assert d["results"]["search"] is not None, "已完成结果保留"
        assert d["results"]["draft"] is None
        assert "HTTP 500" in (d["message"] or "")
        assert d["planner_http_attempts"] == 2 and d["tool_calls_used"] == 1

    def test_illegal_json_stops_with_explainable_failure(self, mock_server):
        mock = mock_server([{"content": "垃圾内容不是 JSON"}, act_finish()])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        d = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        assert d["status"] == "stopped"
        assert d["stop_reason"] == "planner_error"
        assert "JSON" in (d["message"] or "")
        assert len(mock.requests) == 1, "失败不重试（零自动重试）"

    def test_awaiting_input_from_planner(self, mock_server):
        mock = mock_server([act_awaiting(["procedure_confirm"], "更换事项需用户确认")])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        d = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        assert d["status"] == "awaiting_input"
        assert d["input_needed"] == ["procedure_confirm"]
        assert "更换事项需用户确认" in d["message"]


class TestCompletionVerdict:
    """T024-R1：服务端按必要产物判定完成；缺草稿不得 completed。"""

    def test_direct_finish_without_artifacts_not_completed(self, mock_server):
        mock = mock_server([act_finish("【模拟】全部办理工作已完成")])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        d = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        assert d["status"] == "stopped"
        assert d["results"]["draft"] is None and d["results"]["search"] is None
        assert "任务未完成" in d["message"] and "查找依据、整理草稿" in d["message"]
        assert "全部办理工作已完成" not in d["message"], "模型结束语不作主结论"
        assert d.get("planner_summary") == "【模拟】全部办理工作已完成", "结束语仅记录"
        assert len(mock.requests) == 1, "不偷偷补调用"

    def test_search_then_finish_missing_draft_not_completed(self, mock_server):
        mock = mock_server([act_call("search_policy", {"query": "缓考"}), act_finish("【模拟】全部办理工作已完成")])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        d = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        assert d["status"] == "partial"
        assert d["results"]["search"] is not None, "保留已有检索结果"
        assert d["results"]["draft"] is None
        assert "缺少整理草稿" in d["message"] and "已保留查找依据" in d["message"]
        assert "未补调用、未重试" in d["message"]
        assert "全部办理工作已完成" not in d["message"]
        assert len(mock.requests) == 2, "不偷偷补调用、不重试"

    def test_full_chain_completed_with_server_verdict(self, mock_server):
        mock = mock_server([
            act_call("search_policy", {"query": "缓考"}),
            act_call("build_checklist_draft", {}),
            act_finish("【模拟】全部办理工作已完成"),
        ])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        d = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        assert d["status"] == "completed"
        assert d["results"]["search"] is not None and d["results"]["draft"] is not None
        # 服务端文案为主结论：完成=生成可核对结果，不是办妥/审批/已保存
        assert "均已生成" in d["message"]
        assert "不代表学校审批、办事已办妥或待办已保存" in d["message"]
        assert "全部办理工作已完成" not in d["message"]

    def test_insufficient_draft_saveable_false_explicit(self, mock_server):
        mock = mock_server([
            act_call("search_policy", {"query": "缓考"}),
            act_call("build_checklist_draft", {}),
            act_finish("完成"),
        ])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        body = _defer_body()
        # 未知校区 → 依据被筛除 → saveable=false（资料不足草稿）
        body["filters"] = {"campus": "火星校区", "student_type": None, "admission_year": None, "as_of_date": None}
        d = c.post("/api/v1/agent/plan/run", json=body).json()
        assert d["results"]["draft"] is not None and d["results"]["draft"]["saveable"] is False
        assert d["status"] == "completed", "产物齐=可核对结果（草稿本身如实标注不足）"
        assert "saveable=false" in d["message"] and "暂不可保存" in d["message"]
        assert "不代表学校审批、办事已办妥" in d["message"]


class TestZeroPlannerCallsAndAttempts:
    def test_startup_status_fixed_workflow_zero_planning_requests(self, mock_server):
        mock = mock_server([act_finish()])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        c.get("/api/v1/agent/status")
        c.get("/")
        c.post("/api/v1/agent/workflow/run", json=_defer_body())
        assert mock.requests == [], "启动/status/固定流程零规划请求"
        c.post("/api/v1/agent/plan/run", json=_defer_body())
        assert len(mock.requests) == 1, "仅显式规划请求触发"

    def test_attempts_budget_and_no_retry(self, mock_server):
        mock = mock_server([{"http_status": 500}])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        d = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        assert d["planner_http_attempts"] == 1
        assert len(mock.requests) == 1, "HTTP 失败零重试"
        assert d["budget"]["auto_retries"] == 0

    def test_status_distinguishes_modes_and_unverified(self, mock_server):
        mock = mock_server([act_finish()])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        s = c.get("/api/v1/agent/status").json()
        assert s["agent_mode"] == "deepseek"
        assert s["planner_live_verified"] is False
        assert s["remote_planner"] is True
        assert s["planner"]["model"] == "mock-model"
        off = TestClient(_app(None), raise_server_exceptions=False).get("/api/v1/agent/status").json()
        assert off["agent_mode"] == "off" and off["planner_live_verified"] is False


class TestT026ParamConvergence:
    """T026：声明只含模型可写参数；越权参数明确拒绝不静默执行。"""

    def test_outbound_declaration_excludes_fixed_params(self, mock_server):
        mock = mock_server([act_finish("done")])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        c.post("/api/v1/agent/plan/run", json=_defer_body())
        sys_msg = mock.requests[0]["messages"][0]["content"]
        # 参数条目不含 filters/procedure_id；草稿声明无参数；示例省略固定条件
        assert "    - filters" not in sys_msg
        assert "    - procedure_id" not in sys_msg
        assert "（无参数；范围条件与已选事项由服务端固定注入）" in sys_msg
        assert '"tool": "build_checklist_draft", "args": {}}' in sys_msg
        assert "本次可用检索模式" in sys_msg
        assert "不要**在 args 中传入 filters 或 procedure_id" in sys_msg

    def test_overreach_filters_and_procedure_rejected(self, documents, procedures):
        from campus_assistant.agent.tools import (
            RunSnapshot,
            ToolContext,
            build_tool_registry,
            run_tool,
        )

        reg = build_tool_registry()
        snap = _snap()
        ctx = ToolContext(
            procedures=procedures, documents=documents,
            bm25_index=None, dense_index=None, embedding_service=None,
            available_modes=["bm25"], snapshot=snap,
        )
        r1 = run_tool(reg, "search_policy", {"query": "缓考", "filters": {"年级": "2023"}}, ctx)
        assert r1["status"] == "rejected" and "不得放宽或改写" in r1["error"] and r1["result"] is None
        r2 = run_tool(reg, "build_checklist_draft", {"procedure_id": "proc-review-grade"}, ctx)
        assert r2["status"] == "rejected" and "不得擅自更换事项" in r2["error"] and r2["result"] is None

    def test_replay_bad_action_still_rejected_then_clean_run_completes(self, mock_server):
        bad = {"type": "call", "tool": "search_policy",
               "args": {"query": "缓考", "filters": {"年级": "2023"}}}
        mock = mock_server([
            {"content": json.dumps(bad, ensure_ascii=False)},
            act_call("build_checklist_draft", {}),
            act_finish("run1"),
            act_call("search_policy", {"query": "缓考"}),
            act_call("build_checklist_draft", {}),
            act_finish("run2"),
        ])
        c = TestClient(_app(_planner(mock)), raise_server_exceptions=False)
        d1 = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        # 坏动作仍被拒，快照未放宽，finish 不伪装成功
        assert d1["events"][1]["kind"] == "tool_rejected"
        assert "不得放宽或改写" in (d1["events"][1]["error"] or "")
        assert d1["snapshot"]["filters"]["admission_year"] == 2023
        assert d1["status"] == "partial"
        # 同一服务下一次独立运行正常完成
        d2 = c.post("/api/v1/agent/plan/run", json=_defer_body()).json()
        assert d2["status"] == "completed" and d2["tool_calls_used"] == 2
        assert d2["results"]["draft"]["procedure_id"] == "proc-apply-defer"


class TestEntryAssembly:
    def test_planner_default_off_and_degrades(self, monkeypatch):
        monkeypatch.setenv("CAMPUS_PLANNER", "deepseek")
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        app, report = serve_corpus.build_app(
            manifest=PARSE_CORPUS / "manifest.json", corpus_root=PARSE_CORPUS,
            planner_mode="deepseek",
        )
        text = "\n".join(line for line, _ in report)
        assert "请求启用但配置不完整" in text and "已降级" in text
        assert TestClient(app, raise_server_exceptions=False).get("/api/v1/agent/status").json()["agent_mode"] == "off"

    def test_planner_configured_report_no_key_leak(self, monkeypatch):
        monkeypatch.setenv("CAMPUS_PLANNER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)

        def factory():
            return planner_from_env({"CAMPUS_PLANNER": "deepseek", "DEEPSEEK_API_KEY": FAKE_KEY,
                                     "DEEPSEEK_MODEL": "deepseek-flash"})

        app, report = serve_corpus.build_app(
            manifest=PARSE_CORPUS / "manifest.json", corpus_root=PARSE_CORPUS,
            planner_mode="deepseek", planner_factory=factory,
        )
        text = "\n".join(line for line, _ in report)
        assert "规划器：已配置" in text and "未联调验证" in text
        assert FAKE_KEY not in text
        s = TestClient(app, raise_server_exceptions=False).get("/api/v1/agent/status").json()
        assert s["agent_mode"] == "deepseek" and s["planner_live_verified"] is False

    def test_generator_independent_of_planner(self):
        app, report = serve_corpus.build_app(
            manifest=PARSE_CORPUS / "manifest.json", corpus_root=PARSE_CORPUS,
            generator="deepseek", provider_factory=lambda: None,
        )
        text = "\n".join(line for line, _ in report)
        assert "生成器：请求启用但配置不完整" in text
        assert "规划器：未启用" in text

    def test_demo_campus_stays_simulated(self, monkeypatch):
        monkeypatch.setenv("CAMPUS_PLANNER", "deepseek")
        monkeypatch.setenv("DEEPSEEK_API_KEY", FAKE_KEY)
        demo_spec = importlib.util.spec_from_file_location(
            "demo_campus_t024", BACKEND / "scripts" / "demo-campus.py")
        demo = importlib.util.module_from_spec(demo_spec)
        demo_spec.loader.exec_module(demo)
        planner = demo._demo_planner()
        assert planner.planner_kind == "simulated", "demo 始终显式模拟，不因环境切到真实服务"

    def test_chat_url_rule_shared(self):
        # 复用 T013/T014 的连接参数惯例（单一路径规则），对应回归
        assert chat_completions_url("https://api.deepseek.com") == "https://api.deepseek.com/chat/completions"
