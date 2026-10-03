"""Restricted orchestration tests (T023).

Focused set matching the task's verification list:
- one normal 检索→缓考草稿 run compared against the direct service results;
- simulated unknown-tool / loop-stop behaviour;
- scope conditions never relaxed;
- missing template / missing required input → clear fallback;
- load and run never auto-save todos, never call a real model.

Uses a local explicitly-injected scripted planner only. Tool call counts and
events are asserted — NOT model quality. No external calls, no downloads.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.agent.planner import SIMULATED_PLANNER_LABEL, ScriptedPlanner
from campus_assistant.agent.tools import RunSnapshot, ToolContext, build_tool_registry, run_tool
from campus_assistant.agent.workflow import run_fixed_workflow, run_planner_loop
from campus_assistant.procedures.service import build_draft, load_procedures
from campus_assistant.retrieval.service import execute_search

BACKEND = Path(__file__).resolve().parents[1]
PARSE_CORPUS = BACKEND / "examples" / "parse-corpus"
PROCEDURES_PATH = BACKEND / "examples" / "procedures" / "procedures.json"

_spec = importlib.util.spec_from_file_location(
    "serve_corpus", BACKEND / "scripts" / "serve-corpus.py"
)
serve_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serve_corpus)


@pytest.fixture(scope="module")
def documents():
    from campus_assistant.corpus.parse import parse_manifest

    r = parse_manifest(PARSE_CORPUS / "manifest.json", PARSE_CORPUS)
    assert r["valid"]
    return r["documents"]


@pytest.fixture(scope="module")
def procedures():
    return load_procedures(PROCEDURES_PATH)


def _ctx(documents, procedures, *, procedure_id="proc-apply-defer", query="缓考申请的条件",
         filters=None, modes=("bm25",)):
    return ToolContext(
        procedures=procedures,
        documents=documents,
        bm25_index=None,
        dense_index=None,
        embedding_service=None,
        available_modes=list(modes),
        snapshot=RunSnapshot(procedure_id=procedure_id, query=query, filters=filters),
    )


def _defer_filters():
    return {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}


class TestNormalRunMatchesService:
    def test_defer_draft_matches_direct_service(self, documents, procedures):
        f = _defer_filters()
        ctx = _ctx(documents, procedures, filters=f)
        reg = build_tool_registry()
        out = run_fixed_workflow(snapshot=ctx.snapshot, ctx=ctx, registry=reg)

        assert out["workflow_kind"] == "fixed"
        assert "非大模型 Agent" in out["workflow_label"]
        assert out["status"] == "completed"
        assert out["tool_calls_used"] == 2

        # 对照直接 service 结果与引用
        direct = build_draft(procedures, "proc-apply-defer", f, documents)
        got = out["results"]["draft"]
        assert got["saveable"] == direct["saveable"] is True
        assert [s["step_id"] for s in got["steps"]] == [s["step_id"] for s in direct["steps"]]
        for gs, ds in zip(got["steps"], direct["steps"]):
            assert [c["block_id"] for c in gs["citations"]] == [c["block_id"] for c in ds["citations"]]
            assert [c["quote"] for c in gs["citations"]] == [c["quote"] for c in ds["citations"]]

    def test_search_tool_matches_direct_execute_search(self, documents, procedures):
        f = _defer_filters()
        ctx = _ctx(documents, procedures, query="缓考", filters=f)
        reg = build_tool_registry()
        res = run_tool(reg, "search_policy", {"query": "缓考", "top_k": 5}, ctx)
        assert res["status"] == "ok"
        direct = execute_search(
            query="缓考", mode="bm25", top_k=5, filters_norm=f,
            documents=documents, bm25_index=None, dense_index=None, embedding_service=None,
        )
        assert [h["chunk"].get("chunk_id") for h in res["result"]["hits"]] == \
               [h["chunk"].get("chunk_id") for h in direct["hits"]]

    def test_events_record_tool_names_no_thought(self, documents, procedures):
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        out = run_fixed_workflow(snapshot=ctx.snapshot, ctx=ctx, registry=build_tool_registry())
        tools = [e["tool"] for e in out["events"] if e["tool"]]
        assert tools == ["search_policy", "build_checklist_draft"]
        for e in out["events"]:
            assert "thought" not in e and "reasoning" not in e


class TestUnknownToolAndLoopStop:
    def test_unknown_tool_rejected_before_business(self, documents, procedures):
        ctx = _ctx(documents, procedures)
        res = run_tool(build_tool_registry(), "not_a_tool", {}, ctx)
        assert res["status"] == "rejected"
        assert "未知工具" in res["error"]
        assert res["result"] is None

    def test_invalid_args_rejected_before_business(self, documents, procedures):
        ctx = _ctx(documents, procedures)
        res = run_tool(build_tool_registry(), "search_policy", {"top_k": 99}, ctx)
        assert res["status"] == "rejected"
        assert res["result"] is None

    def test_repeated_action_stops_loop(self, documents, procedures):
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        planner = ScriptedPlanner([
            {"tool": "search_policy", "args": {"query": "缓考"}},
            {"tool": "search_policy", "args": {"query": "缓考"}},  # 重复 → 停止
            {"type": "finish"},
        ])
        out = run_planner_loop(planner=planner, snapshot=ctx.snapshot, ctx=ctx,
                               registry=build_tool_registry())
        assert out["stop_reason"] == "no_progress"
        assert out["tool_calls_used"] == 1
        assert out["plan_rounds_used"] <= 4

    def test_tool_call_budget_capped(self, documents, procedures):
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        planner = ScriptedPlanner([
            {"tool": "search_policy", "args": {"query": "缓考"}},
            {"tool": "build_checklist_draft", "args": {}},
            {"tool": "search_policy", "args": {"query": "复核"}},
            {"tool": "build_checklist_draft", "args": {}},
            {"tool": "search_policy", "args": {"query": "考试"}},
            {"tool": "build_checklist_draft", "args": {}},
            {"tool": "search_policy", "args": {"query": "学籍"}},  # 第7次 → 预算停止
            {"type": "finish"},
        ])
        out = run_planner_loop(planner=planner, snapshot=ctx.snapshot, ctx=ctx,
                               registry=build_tool_registry())
        assert out["tool_calls_used"] <= 6
        assert out["plan_rounds_used"] <= 4
        assert out["stop_reason"] in ("budget_exhausted", "no_progress", "finished")


class TestScopeNeverRelaxed:
    def test_planner_cannot_widen_filters(self, documents, procedures):
        f = _defer_filters()
        ctx = _ctx(documents, procedures, filters=f)
        reg = build_tool_registry()
        # 试图放宽（去掉年级限制）→ 调用前拒绝（T026：filters 为越权参数，一律拒）
        res = run_tool(reg, "search_policy", {"query": "缓考", "filters": {"campus": None, "student_type": None, "admission_year": None, "as_of_date": None}}, ctx)
        assert res["status"] == "rejected"
        assert "不得放宽或改写" in res["error"]
        assert res["result"] is None

    def test_matching_filters_also_rejected_no_silent_execute(self, documents, procedures):
        # T026：即使与快照一致也不得由模型传入（不能静默忽略后执行）
        f = _defer_filters()
        ctx = _ctx(documents, procedures, filters=f)
        res = run_tool(build_tool_registry(), "search_policy", {"query": "缓考", "filters": f}, ctx)
        assert res["status"] == "rejected" and res["result"] is None

    def test_omitted_filters_uses_snapshot_scope(self, documents, procedures):
        f = _defer_filters()
        ctx = _ctx(documents, procedures, filters=f)
        res = run_tool(build_tool_registry(), "search_policy", {"query": "缓考"}, ctx)
        assert res["status"] == "ok"
        # 执行层从快照注入固定条件；年级条件确已生效（未被放宽）
        assert res["result"]["filter_summary"]["active"] is True


class TestFallbacks:
    def test_missing_template_gives_clear_fallback(self, documents):
        ctx = _ctx(documents, None)
        res = run_tool(build_tool_registry(), "build_checklist_draft", {}, ctx)
        assert res["status"] == "rejected"
        assert "模板未配置" in res["error"]

    def test_missing_input_returns_awaiting(self, documents, procedures):
        ctx = _ctx(documents, procedures, query="")
        out = run_fixed_workflow(snapshot=ctx.snapshot, ctx=ctx, registry=build_tool_registry())
        assert out["status"] == "awaiting_input"
        assert "query" in out["input_needed"]

    def test_unknown_procedure_awaiting(self, documents, procedures):
        ctx = _ctx(documents, procedures, procedure_id="proc-not-here")
        out = run_fixed_workflow(snapshot=ctx.snapshot, ctx=ctx, registry=build_tool_registry())
        assert out["status"] == "awaiting_input"
        assert "procedure_id" in out["input_needed"]
        assert out["tool_calls_used"] == 0


class TestNoAutoSaveNoRealModel:
    def test_workflow_page_has_no_localStorage_write(self):
        html = (BACKEND / "src" / "campus_assistant" / "static" / "workflow.html").read_text(encoding="utf-8")
        # 断言实际写入调用缺失，而非说明文字（说明里会提到 localStorage）
        assert "localStorage.setItem" not in html
        assert "localStorage.getItem" not in html
        assert ".setItem(" not in html
        assert "window.localStorage" not in html

    def test_demo_planner_label_and_counts(self, documents, procedures):
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        planner = ScriptedPlanner([
            {"tool": "search_policy", "args": {}},
            {"tool": "build_checklist_draft", "args": {}},
            {"type": "finish", "summary": "模拟脚本完成"},
        ])
        assert planner.label == SIMULATED_PLANNER_LABEL
        out = run_planner_loop(planner=planner, snapshot=ctx.snapshot, ctx=ctx,
                               registry=build_tool_registry())
        assert out["workflow_label"] == SIMULATED_PLANNER_LABEL
        assert out["tool_calls_used"] == 2
        assert out["results"]["draft"] is not None


class TestFixedWorkflowVerdict:
    """T024-R1：固定流程同一产物判定原则——搜索失败+草稿成功不得无提示 completed。"""

    def test_search_fail_draft_ok_is_partial_with_missing_listed(self, documents, procedures):
        from campus_assistant.agent.tools import ToolSpec

        reg = build_tool_registry()

        def boom(args, ctx):
            raise RuntimeError("search down")

        reg["search_policy"] = ToolSpec(
            name="search_policy", description="", parameters=[], handler=boom,
        )
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        out = run_fixed_workflow(snapshot=ctx.snapshot, ctx=ctx, registry=reg)
        assert out["status"] == "partial"
        assert out["results"]["draft"] is not None
        assert out["results"]["search"] is None
        assert "缺少查找依据" in out["message"] and "未补调用" in out["message"]
        assert out["steps"][1]["status"] == "failed"

    def test_clean_fixed_run_completed_with_server_note(self, documents, procedures):
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        out = run_fixed_workflow(snapshot=ctx.snapshot, ctx=ctx, registry=build_tool_registry())
        assert out["status"] == "completed"
        assert "均已生成" in out["message"]
        assert "不代表学校审批、办事已办妥或待办已保存" in out["message"]


class TestObservationTruncationTransparency:
    """T026：有界观察补总数/已列数/截断标记——“列了 3 项”≠“总共 3 项”。"""

    def test_pending_items_total_listed_truncated(self, documents, procedures):
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        planner = ScriptedPlanner([
            {"tool": "build_checklist_draft", "args": {}},
            {"type": "finish", "summary": "done"},
        ])
        out = run_planner_loop(planner=planner, snapshot=ctx.snapshot, ctx=ctx,
                               registry=build_tool_registry())
        obs = next(e["observation"] for e in out["events"]
                   if e["kind"] == "tool_call" and e["tool"] == "build_checklist_draft")
        # 完整草稿 4 项待核实；观察只列 3 —— 总数/已列/截断如实
        full_pending = sum(len(s.get("unspecified") or []) for s in out["results"]["draft"]["steps"])
        assert full_pending == 4
        assert obs["pending_items_total"] == 4
        assert obs["pending_items_listed"] == 3
        assert obs["pending_items_truncated"] is True
        assert len(obs["pending_items"]) == 3
        # 完整草稿未被摘要截断影响
        assert out["results"]["draft"]["steps"] is not None
        # issues 同口径
        assert obs["issues_total"] == len(out["results"]["draft"]["issues"]) >= 0
        assert obs["issues_listed"] <= obs["issues_total"]

    def test_evidence_truncation_flags(self, documents, procedures):
        ctx = _ctx(documents, procedures, filters=_defer_filters())
        planner = ScriptedPlanner([
            {"tool": "search_policy", "args": {"query": "缓考", "top_k": 10}},
            {"type": "finish", "summary": "done"},
        ])
        out = run_planner_loop(planner=planner, snapshot=ctx.snapshot, ctx=ctx,
                               registry=build_tool_registry())
        obs = next(e["observation"] for e in out["events"]
                   if e["kind"] == "tool_call" and e["tool"] == "search_policy")
        assert obs["evidence_total"] == obs["hit_count"]
        assert obs["evidence_listed"] == len(obs["top_evidence"])
        assert obs["evidence_truncated"] == (obs["evidence_total"] > obs["evidence_listed"])


class TestPlannerRunIsolation:
    """T023-R1：同一规划器实例跨请求共享导致第二次运行空完成——已改为无状态按 round_no 取动作。"""

    SCRIPT = [
        {"tool": "search_policy", "args": {}},
        {"tool": "build_checklist_draft", "args": {}},
        {"type": "finish", "summary": "done"},
    ]

    def test_same_instance_two_runs_both_execute(self, documents, procedures):
        planner = ScriptedPlanner(self.SCRIPT)
        reg = build_tool_registry()
        c1 = _ctx(documents, procedures, procedure_id="proc-apply-defer", query="缓考", filters=_defer_filters())
        o1 = run_planner_loop(planner=planner, snapshot=c1.snapshot, ctx=c1, registry=reg)
        c2 = _ctx(documents, procedures, procedure_id="proc-review-grade", query="成绩复核", filters=None)
        o2 = run_planner_loop(planner=planner, snapshot=c2.snapshot, ctx=c2, registry=reg)

        assert o1["tool_calls_used"] == 2 and o1["results"]["draft"] is not None
        assert o2["tool_calls_used"] == 2, "同一实例第二次运行必须照常执行，不得空完成"
        assert o2["results"]["draft"]["procedure_id"] == "proc-review-grade"
        assert o2["results"]["search"]["query"] == "成绩复核"
        assert o2["snapshot"]["filters"] is None

    def test_same_client_two_consecutive_api_runs(self):
        planner = ScriptedPlanner(self.SCRIPT)
        c = TestClient(TestPlannerRunIsolation._app(planner=planner), raise_server_exceptions=False)
        r1 = c.post("/api/v1/agent/plan/run", json={
            "procedure_id": "proc-apply-defer", "query": "缓考申请的条件",
            "filters": {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None},
        })
        # 第二次换事项与条件（同一 app/client，不重启、不刷新）
        r2 = c.post("/api/v1/agent/plan/run", json={
            "procedure_id": "proc-review-grade", "query": "成绩复核的流程", "filters": None,
        })
        assert r1.status_code == 200 and r2.status_code == 200
        d1, d2 = r1.json(), r2.json()
        assert d1["tool_calls_used"] == 2
        assert d2["tool_calls_used"] == 2, "第二次运行必须照常执行工具"
        # 结果属于第二次快照
        assert d2["results"]["draft"]["procedure_id"] == "proc-review-grade"
        assert d2["results"]["search"]["query"] == "成绩复核的流程"
        assert d2["snapshot"]["filters"] is None
        assert d1["results"]["draft"]["procedure_id"] == "proc-apply-defer"
        assert d1["snapshot"]["filters"]["admission_year"] == 2023

    @staticmethod
    def _app(**kw):
        app, _ = serve_corpus.build_app(
            manifest=PARSE_CORPUS / "manifest.json", corpus_root=PARSE_CORPUS,
            procedures=PROCEDURES_PATH, **kw,
        )
        return app


class TestAgentRouteDefaultsOff:
    def _app(self, **kw):
        app, _ = serve_corpus.build_app(
            manifest=PARSE_CORPUS / "manifest.json", corpus_root=PARSE_CORPUS,
            procedures=PROCEDURES_PATH, **kw,
        )
        return app

    def test_agent_off_by_default(self):
        c = TestClient(self._app(), raise_server_exceptions=False)
        s = c.get("/api/v1/agent/status").json()
        assert s["agent_mode"] == "off"
        assert s["planner"] is None
        assert s["remote_planner"] is False
        assert s["tinyagent_integration_kind"] == "reference"
        assert {t["name"] for t in s["tools"]} == {"search_policy", "build_checklist_draft"}
        r = c.post("/api/v1/agent/plan/run", json={"procedure_id": "proc-apply-defer", "query": "缓考"})
        assert r.status_code == 503
        assert r.json()["code"] == "AGENT_NOT_CONFIGURED"

    def test_fixed_workflow_route_runs_and_copies_condition(self):
        c = TestClient(self._app(), raise_server_exceptions=False)
        body = {"procedure_id": "proc-apply-defer", "query": "缓考申请的条件",
                "filters": {"campus": None, "student_type": None, "admission_year": 2023, "as_of_date": None}}
        r = c.post("/api/v1/agent/workflow/run", json=body)
        assert r.status_code == 200
        d = r.json()
        assert d["workflow_kind"] == "fixed" and d["status"] == "completed"
        assert d["snapshot"]["filters"]["admission_year"] == 2023
        assert d["results"]["draft"]["saveable"] is True

    def test_explicit_planner_injection_enables_plan_run(self):
        planner = ScriptedPlanner([
            {"tool": "search_policy", "args": {}},
            {"type": "finish", "summary": "done"},
        ])
        c = TestClient(self._app(planner=planner), raise_server_exceptions=False)
        s = c.get("/api/v1/agent/status").json()
        assert s["agent_mode"] == "simulated"
        assert s["planner"]["label"] == SIMULATED_PLANNER_LABEL
        r = c.post("/api/v1/agent/plan/run", json={"procedure_id": "proc-apply-defer", "query": "缓考"})
        assert r.status_code == 200
        assert r.json()["tool_calls_used"] == 1

    def test_workflow_page_reachable(self):
        c = TestClient(self._app(), raise_server_exceptions=False)
        r = c.get("/workflow")
        assert r.status_code == 200
        assert "非大模型 Agent" in r.text
        assert "localStorage.setItem" not in r.text
