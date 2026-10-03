"""Restricted execution loop shared by the fixed workflow and planners (T023/T024).

- ``run_fixed_workflow``: deterministic 选事项→查找依据→整理草稿. This is a
  fixed pipeline over the same tools — explicitly NOT an LLM agent.
- ``run_planner_loop``: drives any injected ``Planner`` through the same
  tools under the budgets below. Planners: scripted simulated (demo) or
  the DeepSeek structured adapter (T024, explicit config; live never
  verified this round).

Budgets (from the approved plan): ≤4 planning rounds, ≤6 tool executions,
≤1 planning HTTP per round, zero automatic retries. No-progress repeated
actions stop the run. Unknown tools / invalid params are rejected before
any business call. The total time limit is enforced by monotonic-clock
checks BETWEEN steps: in-flight synchronous local tools and in-flight
planning HTTP calls are not cancelled (no cancellation mechanism) — the
honest contract is "stop scheduling further work", never "the computation
was aborted".

Observations carry bounded, real result summaries (hit counts + a few
evidence/source identifiers; draft saveable / pending items / actual
procedure_id) with explicit char budgets and truncation markers — enough
for the next decision, never the full corpus / history / keys. Corpus text
in observations is data, not instructions.

Completion semantics (T024-R1): completion is decided SERVER-SIDE by the
required artifacts of this entry point — 查找依据 (search result) and 整理草稿
(draft) — never by the planner's summary. Missing artifacts → ``partial``
(some results kept) or ``stopped`` (none), with the missing steps listed and
no hidden extra calls/retries. A produced draft with saveable=false is an
artifact but is always labelled 依据不足/暂不可保存; "completed" only means
generating checkable results — never school approval, finished business or
saved todos. ``awaiting_input`` names what is missing. Planning/tool
exceptions become explainable failures that keep completed results. Events
record actual tool names, statuses, counts and model audit fields (missing →
null) — no model Thought / hidden reasoning is stored or emitted.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from campus_assistant.agent.planner import Planner
from campus_assistant.agent.tools import ToolContext, ToolSpec, run_tool

MAX_PLAN_ROUNDS = 4
MAX_TOOL_CALLS = 6
DEFAULT_DEADLINE_S = 30.0

OBS_EXCERPT_CHARS = 80
OBS_FIELD_CHARS = 160
OBS_ERROR_CHARS = 200
OBS_TOP_EVIDENCE = 3
OBS_TOP_ISSUES = 3
OBS_TOP_UNSPECIFIED = 3

CANCEL_NOTE = (
    "工具为本地同步计算，规划调用可能是远程 HTTP；均不支持中途取消。"
    "停止/超时只终止后续调度，正在执行的调用会运行完毕（不谎称已取消底层计算）。"
)

FIXED_WORKFLOW_LABEL = "固定流程（选事项→查找依据→整理草稿），非大模型 Agent"

# 必要产物（T024-R1）：本入口的任务是按用户选定事项查依据、整理办理草稿。
# 完成与否由服务端按产物判定，模型 summary 不决定成功；完成仅指生成可核对结果，
# 不代表学校审批、办事已办妥或待办已保存。
ARTIFACT_LABELS = {"search": "查找依据", "draft": "整理草稿"}
COMPLETION_NOTE = "完成仅指生成可核对结果，不代表学校审批、办事已办妥或待办已保存。"


def _missing_artifacts(out: dict[str, Any]) -> list[str]:
    return [k for k in ("search", "draft") if not out["results"].get(k)]


def _finish_verdict(out: dict[str, Any], *, had_failures: bool) -> tuple[str, str, str]:
    """Server-side completion verdict. Returns (status, stop_reason, message).

    不让模型 summary 决定成功；缺产物 → partial（有结果）/ stopped（无结果），
    列出缺失步骤并保留已完成结果；不补调用、不重试。
    """
    missing = _missing_artifacts(out)
    labels = "、".join(ARTIFACT_LABELS[k] for k in missing)
    kept = "、".join(ARTIFACT_LABELS[k] for k in ("search", "draft") if out["results"].get(k))
    draft = out["results"].get("draft")
    saveable_note = ""
    if draft is not None and draft.get("saveable") is False:
        saveable_note = "草稿 saveable=false（依据不足或需更新，暂不可保存）；"

    if missing and kept:
        return (
            "partial", "incomplete_artifacts",
            f"任务未完成：缺少{labels}。已保留{kept}结果；未补调用、未重试。{saveable_note}{COMPLETION_NOTE}",
        )
    if missing:
        return (
            "stopped", "incomplete_artifacts",
            f"任务未完成：缺少{labels}，本次无任何结果。未补调用、未重试。{COMPLETION_NOTE}",
        )
    if had_failures:
        return (
            "partial", "failed_actions",
            f"必要产物已生成，但期间有失败/被拒动作，未全部完成。{saveable_note}{COMPLETION_NOTE}",
        )
    return (
        "completed", "finished",
        f"查找依据与办理草稿均已生成。{saveable_note}{COMPLETION_NOTE}",
    )


def _clip(text: Any, limit: int) -> str:
    s = str(text if text is not None else "")
    return s if len(s) <= limit else s[:limit] + "…[已截断]"


def _base_result(
    *,
    workflow_kind: str,
    workflow_label: str,
    snapshot: Any,
    budget: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": uuid.uuid4().hex[:12],
        "workflow_kind": workflow_kind,
        "workflow_label": workflow_label,
        "status": "completed",
        "stop_reason": None,
        "message": None,
        "input_needed": [],
        "snapshot": {
            "procedure_id": snapshot.procedure_id,
            "query": snapshot.query,
            "filters": snapshot.filters,
        },
        "steps": [],
        "events": [],
        "results": {"search": None, "draft": None},
        "plan_rounds_used": 0,
        "tool_calls_used": 0,
        "planner_http_attempts": 0,
        "budget": budget,
        "cancellable_note": CANCEL_NOTE,
    }


def _missing_inputs(snapshot: Any) -> list[str]:
    needed = []
    if not snapshot.procedure_id:
        needed.append("procedure_id")
    if not snapshot.query or not str(snapshot.query).strip():
        needed.append("query")
    return needed


def _awaiting(needed: list[str], ctx: ToolContext) -> dict[str, Any]:
    labels = {"procedure_id": "请选择办事事项", "query": "请输入要查找的政策问题"}
    return {
        "status": "awaiting_input",
        "stop_reason": "missing_input",
        "message": "；".join(labels.get(n, n) for n in needed) + "。已在表单中标注待补充项，不会自动猜测。",
        "input_needed": needed,
        "available_procedures": list(ctx.procedure_ids),
    }


def _sanitize_needs(raw: Any) -> list[str]:
    out = []
    if isinstance(raw, list):
        for n in raw[:6]:
            if isinstance(n, str) and n.strip():
                out.append(_clip(n.strip(), 40))
    return out


def _tool_observation(round_no: int, tool_out: dict[str, Any]) -> dict[str, Any]:
    """Bounded real-result summary for the next planner decision (T024).

    Hit counts + a few evidence/source identifiers; draft saveable /
    pending items / actual procedure_id. Explicit truncation markers.
    """
    obs: dict[str, Any] = {
        "round": round_no,
        "tool": tool_out["tool"],
        "status": tool_out["status"],
    }
    if tool_out["status"] != "ok":
        obs["error"] = _clip(tool_out.get("error"), OBS_ERROR_CHARS)
        return obs
    res = tool_out.get("result") or {}
    if "hit_count" in res:
        total = res.get("hit_count", 0)
        obs["hit_count"] = total
        evs = []
        for h in (res.get("hits") or [])[:OBS_TOP_EVIDENCE]:
            c = h.get("chunk") or {}
            evs.append({
                "document_id": _clip(c.get("document_id"), 60),
                "block_id": _clip(c.get("block_id"), 40),
                "excerpt": _clip(c.get("text"), OBS_EXCERPT_CHARS),
            })
        obs["top_evidence"] = evs
        # 截断透明（T026）：总数/已列数/截断标记——“列了 N 条”≠“总共 N 条”
        obs["evidence_total"] = total
        obs["evidence_listed"] = len(evs)
        obs["evidence_truncated"] = total > len(evs)
    elif "saveable" in res:
        obs["procedure_id"] = res.get("procedure_id")
        obs["saveable"] = res.get("saveable")
        obs["status_text"] = res.get("status")
        issues_all = res.get("issues") or []
        issues_shown = [_clip(i, OBS_FIELD_CHARS) for i in issues_all[:OBS_TOP_ISSUES]]
        obs["issues"] = issues_shown
        obs["issues_total"] = len(issues_all)
        obs["issues_listed"] = len(issues_shown)
        obs["issues_truncated"] = len(issues_all) > len(issues_shown)
        pending_all: list[str] = []
        for st in res.get("steps") or []:
            for u in st.get("unspecified") or []:
                pending_all.append(f"{st.get('title')}：{u}")
        pending_shown = [_clip(p, OBS_FIELD_CHARS) for p in pending_all[:OBS_TOP_UNSPECIFIED]]
        obs["pending_items"] = pending_shown
        obs["pending_items_total"] = len(pending_all)
        obs["pending_items_listed"] = len(pending_shown)
        obs["pending_items_truncated"] = len(pending_all) > len(pending_shown)
    return obs


def _procedure_options(ctx: ToolContext) -> list[dict[str, Any]]:
    opts = []
    for p in (ctx.procedures or {}).get("procedures", []):
        opts.append({"procedure_id": p["procedure_id"], "title": p.get("title")})
    return opts


def _event(round_no: int, tool_out: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    """Event record: tool name, status, bounded observation summary —
    never model Thoughts / hidden reasoning."""
    summary = None
    res = tool_out.get("result")
    if res is not None:
        if "hit_count" in res:
            summary = f"命中 {res['hit_count']} 条"
        elif "saveable" in res:
            summary = f"草稿 saveable={res['saveable']}，步骤 {len(res.get('steps', []))} 个"
    return {
        "round": round_no,
        "kind": "tool_call" if tool_out["status"] == "ok" else "tool_rejected",
        "tool": tool_out["tool"],
        "status": tool_out["status"],
        "error": tool_out.get("error"),
        "summary": summary,
        "observation": observation,
        "audit": None,
    }


def _safe_tool_call(
    registry: dict[str, ToolSpec], tool: str, args: Any, ctx: ToolContext, round_no: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Run one tool once; convert unexpected handler exceptions to an
    explainable failure (T024) instead of a 500.

    Returns (event, observation, tool_out). tool_out["result"] holds the
    full business result for the run's result slots (events stay bounded).
    """
    try:
        tool_out = run_tool(registry, tool, args, ctx)
    except Exception as e:  # noqa: BLE001 — mapped to an explainable failure
        tool_out = {
            "tool": tool,
            "status": "rejected",
            "error": f"工具执行异常（{type(e).__name__}），本次未完成",
            "result": None,
        }
    obs = _tool_observation(round_no, tool_out)
    return _event(round_no, tool_out, obs), obs, tool_out


def run_fixed_workflow(
    *,
    snapshot: Any,
    ctx: ToolContext,
    registry: dict[str, ToolSpec],
) -> dict[str, Any]:
    """Fixed pipeline. Requires the user to have selected the procedure and
    posed the query — no inference, no guessing. Zero planner calls."""
    budget = {
        "max_plan_rounds": 1,
        "max_tool_calls": 2,
        "deadline_s": None,
        "note": "固定流程为确定性步骤，不经过规划器",
    }
    out = _base_result(
        workflow_kind="fixed", workflow_label=FIXED_WORKFLOW_LABEL, snapshot=snapshot, budget=budget
    )
    needed = _missing_inputs(snapshot)
    if needed:
        out.update(_awaiting(needed, ctx))
        out["steps"] = [
            {"step_id": "select_procedure", "title": "选事项", "status": "awaiting", "detail": None},
            {"step_id": "search_policy", "title": "查找依据", "status": "skipped", "detail": None},
            {"step_id": "build_checklist_draft", "title": "整理草稿", "status": "skipped", "detail": None},
        ]
        return out

    if snapshot.procedure_id not in ctx.procedure_ids:
        out.update(_awaiting(["procedure_id"], ctx))
        out["message"] = (
            f"未找到事项「{snapshot.procedure_id}」，请从当前已配置事项中选择（不代表学校无此事项）。"
        )
        out["steps"] = [
            {"step_id": "select_procedure", "title": "选事项", "status": "awaiting", "detail": out["message"]},
            {"step_id": "search_policy", "title": "查找依据", "status": "skipped", "detail": None},
            {"step_id": "build_checklist_draft", "title": "整理草稿", "status": "skipped", "detail": None},
        ]
        return out

    proc_title = next(
        (p.get("title") for p in (ctx.procedures or {}).get("procedures", [])
         if p["procedure_id"] == snapshot.procedure_id),
        snapshot.procedure_id,
    )
    out["steps"].append({
        "step_id": "select_procedure", "title": "选事项",
        "status": "ok", "detail": f"已选定：{proc_title}",
    })

    # Step 2 查找依据（异常转换为可解释失败，不 500）
    ev1, _obs1, t1 = _safe_tool_call(registry, "search_policy", {}, ctx, 2)
    out["tool_calls_used"] += 1
    out["events"].append(ev1)
    if t1["status"] == "ok":
        out["results"]["search"] = t1["result"]
        out["steps"].append({
            "step_id": "search_policy", "title": "查找依据", "status": "ok",
            "detail": f"命中 {t1['result'].get('hit_count', 0)} 条原文依据",
        })
    else:
        out["steps"].append({
            "step_id": "search_policy", "title": "查找依据", "status": "failed",
            "detail": t1["error"],
        })

    # Step 3 整理草稿
    ev2, _obs2, t2 = _safe_tool_call(registry, "build_checklist_draft", {}, ctx, 3)
    out["tool_calls_used"] += 1
    out["events"].append(ev2)
    if t2["status"] == "ok":
        out["results"]["draft"] = t2["result"]
        draft = t2["result"]
        out["steps"].append({
            "step_id": "build_checklist_draft", "title": "整理草稿", "status": "ok",
            "detail": "草稿已生成（" + ("可保存" if draft.get("saveable") else "依据不足，暂不可保存") + "）",
        })
    else:
        out["steps"].append({
            "step_id": "build_checklist_draft", "title": "整理草稿", "status": "failed",
            "detail": t2["error"],
        })

    # T024-R1：与规划路径同一产物判定原则（搜索失败+草稿成功不得无提示 completed）
    had_failures = any(e["status"] != "ok" for e in out["events"])
    status, stop_reason, message = _finish_verdict(out, had_failures=had_failures)
    out["status"] = status
    out["stop_reason"] = stop_reason
    out["message"] = message
    out["plan_rounds_used"] = 1
    return out


def _action_signature(action: dict[str, Any]) -> str:
    return json.dumps(
        {"type": action.get("type"), "tool": action.get("tool"), "args": action.get("args")},
        sort_keys=True, ensure_ascii=False, default=str,
    )


def run_planner_loop(
    *,
    planner: Planner,
    snapshot: Any,
    ctx: ToolContext,
    registry: dict[str, ToolSpec],
    deadline_s: float = DEFAULT_DEADLINE_S,
) -> dict[str, Any]:
    """Drive one planner through the tools under budget/deadline limits."""
    budget = {
        "max_plan_rounds": MAX_PLAN_ROUNDS,
        "max_tool_calls": MAX_TOOL_CALLS,
        "planning_http_per_round": 1,
        "auto_retries": 0,
        "deadline_s": deadline_s,
    }
    out = _base_result(
        workflow_kind="deepseek_planner" if planner.planner_kind == "deepseek" else "simulated_planner",
        workflow_label=planner.label,
        snapshot=snapshot,
        budget=budget,
    )
    out["planner"] = {"kind": planner.planner_kind, "label": planner.label}

    needed = _missing_inputs(snapshot)
    if needed:
        out.update(_awaiting(needed, ctx))
        return out

    deadline = time.monotonic() + deadline_s
    seen_signatures: set[str] = set()
    observations: list[dict[str, Any]] = []
    options = _procedure_options(ctx)
    uses_http = bool(getattr(planner, "uses_http", False))
    had_failures = False
    stop_reason = None
    message = None

    for round_no in range(1, MAX_PLAN_ROUNDS + 1):
        if time.monotonic() >= deadline:
            stop_reason = "deadline_exceeded"
            message = "总时限已到（单调时钟检查），停止后续调度。" + CANCEL_NOTE
            break

        # --- one planning attempt per round, zero retries ---
        out["plan_rounds_used"] = round_no
        if uses_http:
            out["planner_http_attempts"] += 1
        try:
            action = planner.next_action(
                round_no=round_no, snapshot=snapshot, observations=observations,
                procedure_options=options,
                available_modes=list(ctx.available_modes),
            )
        except Exception as e:  # noqa: BLE001 — mapped, never a raw 500
            user_message = getattr(e, "user_message", None) or "规划器调用失败（未知错误）"
            # T025-R1：失败轮已收到的安全审计字段保留进运行记录（未收到仍为 null）
            out["events"].append({
                "round": round_no, "kind": "plan_error", "tool": None,
                "status": "failed", "error": user_message,
                "summary": None, "observation": None,
                "audit": getattr(e, "audit", None),
            })
            had_failures = True
            stop_reason = "planner_error"
            message = user_message
            break

        audit = action.get("audit") if isinstance(action, dict) else None
        out["events"].append({
            "round": round_no,
            "kind": "plan_decision",
            "tool": action.get("tool"),
            "status": "ok",
            "error": None,
            "summary": f"动作 {action.get('type')}",
            "observation": None,
            "audit": audit,          # 缺失写 null（脚本规划器恒为 null）
            "action": {
                "type": action.get("type"),
                "tool": action.get("tool"),
                "args": action.get("args") if action.get("type") == "call" else None,
            },
        })

        if action.get("type") == "finish":
            # T024-R1：服务端按必要产物判定完成，模型 summary 不决定成功
            status, stop_reason, message = _finish_verdict(out, had_failures=had_failures)
            out["status"] = status
            summary = action.get("summary")
            if summary:
                # 结束语仅记录进轨迹（模型输出，不作结论）
                out["planner_summary"] = summary
                out["events"].append({
                    "round": round_no, "kind": "finish", "tool": None,
                    "status": "ok", "error": None,
                    "summary": f"规划器结束语（仅记录，不作结论）：{_clip(summary, 120)}",
                    "observation": None, "audit": None,
                })
            break

        if action.get("type") == "awaiting_input":
            out["status"] = "awaiting_input"
            out["stop_reason"] = "planner_awaiting_input"
            out["input_needed"] = _sanitize_needs(action.get("needs"))
            out["message"] = action.get("message") or "规划器请求补充输入"
            return out

        if action.get("type") != "call":
            # 调用前拒绝：未知动作类型（适配器已挡，此处兜底）
            had_failures = True
            out["events"].append({
                "round": round_no, "kind": "tool_rejected", "tool": action.get("tool"),
                "status": "rejected", "error": f"未知动作类型：{action.get('type')!r}",
                "summary": None, "observation": None, "audit": None,
            })
            continue

        sig = _action_signature(action)
        if sig in seen_signatures:
            stop_reason = "no_progress"
            message = "重复相同动作（无新信息），按预算规则停止。"
            out["events"].append({
                "round": round_no, "kind": "stopped", "tool": action.get("tool"),
                "status": "skipped", "error": message, "summary": None,
                "observation": None, "audit": None,
            })
            break
        seen_signatures.add(sig)

        if out["tool_calls_used"] >= MAX_TOOL_CALLS:
            stop_reason = "budget_exhausted"
            message = f"工具执行次数已达上限（{MAX_TOOL_CALLS}），停止。"
            break

        if time.monotonic() >= deadline:
            stop_reason = "deadline_exceeded"
            message = "总时限已到（单调时钟检查），停止后续调度。" + CANCEL_NOTE
            break

        ev, obs, t = _safe_tool_call(registry, action.get("tool", ""), action.get("args"), ctx, round_no)
        out["events"].append(ev)
        if t["status"] == "ok":
            out["tool_calls_used"] += 1
            if t["tool"] == "search_policy":
                out["results"]["search"] = t["result"]
            elif t["tool"] == "build_checklist_draft":
                out["results"]["draft"] = t["result"]
        else:
            had_failures = True
        observations.append(obs)
    else:
        stop_reason = "budget_exhausted"
        message = f"规划轮次已达上限（{MAX_PLAN_ROUNDS}），停止。"

    if stop_reason in ("no_progress", "budget_exhausted", "deadline_exceeded", "planner_error"):
        if out["results"]["search"] or out["results"]["draft"]:
            out["status"] = "partial"
            message = (message or "") + " 已保留已完成部分的结果。"
        else:
            out["status"] = "stopped"
    out["stop_reason"] = stop_reason
    out["message"] = message
    return out
