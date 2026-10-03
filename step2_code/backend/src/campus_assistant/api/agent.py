"""Restricted workflow API (T023).

GET  /api/v1/agent/status      — orchestration capability (always 200)
POST /api/v1/agent/workflow/run — fixed workflow 选事项→查找依据→整理草稿
POST /api/v1/agent/plan/run     — planner loop (explicitly injected planner only)

The fixed workflow is a deterministic pipeline and is never described as an
LLM agent. Planner mode is OFF in normal runs (planner=None); the simulated
planner is injected only by explicit demo/test entries and every run it
produces is labelled 模拟规划，非DeepSeek实时规划. A remote planning adapter
(DeepSeekPlanner, HTTP) exists behind the explicit config switch (T024) —
it is never contacted without explicit enable, is labelled by its actual
mode per response (fixed/simulated/deepseek), and is NOT live-verified
(planner_live_verified=false).

Both endpoints share the same two read-only tools (search_policy /
build_checklist_draft) which call existing services in-process. Nothing here
writes user todos or calls the answer provider. The run body carries the
user-submitted scope conditions; tools refuse to relax them.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from campus_assistant.agent.planner import SIMULATED_PLANNER_LABEL
from campus_assistant.agent.tools import (
    RunSnapshot,
    ToolContext,
    build_tool_registry,
    tool_catalog,
)
from campus_assistant.agent.workflow import (
    DEFAULT_DEADLINE_S,
    MAX_PLAN_ROUNDS,
    MAX_TOOL_CALLS,
    run_fixed_workflow,
    run_planner_loop,
)
from campus_assistant.api.search import SearchFilters

TINYAGENT_INTEGRATION_KIND = "reference"
TINYAGENT_NOTE = (
    "参考 TinyAgent（Datawhale tiny-universe/content/TinyAgent）的工具描述与动作循环思路，"
    "自研受限编排；未导入其代码、未接入真实 Agent，真实模型规划效果未验证。"
)


class RunRequest(BaseModel):
    model_config = {"extra": "forbid"}

    procedure_id: str | None = None
    query: str | None = None
    filters: SearchFilters | None = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str


def _snapshot(body: RunRequest) -> RunSnapshot:
    return RunSnapshot(
        procedure_id=body.procedure_id,
        query=body.query,
        filters=body.filters.normalized() if body.filters else None,
    )


def _ctx(request: Request, snapshot: RunSnapshot) -> ToolContext:
    state = request.app.state
    return ToolContext(
        procedures=getattr(state, "procedures", None),
        documents=state.corpus_data or [],
        bm25_index=state.search_index,
        dense_index=state.dense_index,
        embedding_service=state.embedding_service,
        available_modes=list(state.available_modes),
        snapshot=snapshot,
    )


def create_agent_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

    @router.get("/status")
    async def agent_status(request: Request):
        planner = getattr(request.app.state, "agent_planner", None)
        procedures = getattr(request.app.state, "procedures", None)
        if procedures is not None:
            fixed_available, reason = True, None
        else:
            fixed_available = False
            reason = "办事模板未配置——固定流程暂不可用（不代表学校事项无模板）；原文检索与摘录不受影响"
        kind = getattr(planner, "planner_kind", None) if planner is not None else None
        mode = {"simulated": "simulated", "deepseek": "deepseek"}.get(kind or "", "off")
        return {
            "agent_mode": mode,
            "planner": (
                {
                    "kind": kind,
                    "label": planner.label,
                    "uses_http": bool(getattr(planner, "uses_http", False)),
                    "model": getattr(planner, "model", None),
                }
                if planner is not None
                else None
            ),
            # 已配置 ≠ 已联调验证：本轮 planner_live_verified 恒为 false
            "planner_live_verified": False,
            "remote_planner": bool(getattr(planner, "uses_http", False)),
            "planner_note": "已配置/已注入不代表真实服务已联调验证；planner_live_verified=false",
            "tools": tool_catalog(),
            "budget": {
                "max_plan_rounds": MAX_PLAN_ROUNDS,
                "max_tool_calls": MAX_TOOL_CALLS,
                "planning_http_per_round": 1,
                "auto_retries": 0,
                "deadline_s": DEFAULT_DEADLINE_S,
            },
            "workflow": {"fixed_available": fixed_available, "reason": reason},
            "tinyagent_integration_kind": TINYAGENT_INTEGRATION_KIND,
            "tinyagent_note": TINYAGENT_NOTE,
            "request_id": request.state.request_id,
        }

    @router.post("/workflow/run", responses={503: {"model": ErrorResponse}})
    async def workflow_run(body: RunRequest, request: Request):
        procedures = getattr(request.app.state, "procedures", None)
        if procedures is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "PROCEDURES_NOT_CONFIGURED",
                    "message": "办事模板未配置，固定流程不可用（不代表学校事项无模板）。"
                    "请改用 /search 或 /ask 的原文摘录，或在启动入口显式配置办事模板。",
                    "request_id": request.state.request_id,
                },
            )
        snapshot = _snapshot(body)
        # 同步执行（工具/规划均为同步计算）放线程池，不阻塞事件循环（T024）
        result = await run_in_threadpool(
            run_fixed_workflow,
            snapshot=snapshot,
            ctx=_ctx(request, snapshot),
            registry=build_tool_registry(),
        )
        result["request_id"] = request.state.request_id
        return result

    @router.post("/plan/run", responses={503: {"model": ErrorResponse}})
    async def plan_run(body: RunRequest, request: Request):
        planner = getattr(request.app.state, "agent_planner", None)
        if planner is None:
            return JSONResponse(
                status_code=503,
                content={
                    "code": "AGENT_NOT_CONFIGURED",
                    "message": "Agent 模式默认关闭（普通服务不注入规划器）；"
                    f"模拟规划（{SIMULATED_PLANNER_LABEL}）仅在显式演示入口启用。"
                    "固定流程请改用 /api/v1/agent/workflow/run。",
                    "request_id": request.state.request_id,
                },
            )
        snapshot = _snapshot(body)
        # 规划 HTTP 为同步调用，放线程池（T024）；在途调用无法强制撤销（如实说明）
        result = await run_in_threadpool(
            run_planner_loop,
            planner=planner,
            snapshot=snapshot,
            ctx=_ctx(request, snapshot),
            registry=build_tool_registry(),
        )
        result["request_id"] = request.state.request_id
        return result

    return router
