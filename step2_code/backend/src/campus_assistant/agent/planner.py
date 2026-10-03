"""Replaceable planner boundary (T023).

``Planner`` is the contract a future agent adapter would implement (the
"Agent 可替换层" of docs/04). This round ships ONLY the scripted simulated
planner below; there is no remote/LLM planning implementation and none is
called anywhere.

Future connection contract (designed, not implemented this round):
an adapter would receive the tool catalog (``tool_catalog()``), the
user-submitted snapshot and prior observations, request one action from the
remote model as strict JSON (tool name + args), and return exactly the
``next_action`` shape below. The execution loop, budgets, parameter
validation and scope lock stay in ``workflow.py``/``tools.py`` and are not
delegated to the model. Until such an adapter actually runs against a real
model, nothing here may be described as "真实 Agent 已接入".

Reference: the tool-description / action-observation loop shape was informed
by Datawhale tiny-universe/content/TinyAgent (Agent.py ReAct prompt +
parse_latest_plugin_call). Its model layer (LLM.InternLM2Chat, transformers,
``.cuda()``) and its only tool (google_search via serper.dev) are NOT reused;
no code of that repository is imported. See
submissions/T023/tinyagent-assessment.md.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

SIMULATED_PLANNER_LABEL = "模拟规划，非DeepSeek实时规划"


@runtime_checkable
class Planner(Protocol):
    """One planning decision per call. The loop never accepts free-form
    reasoning text from a planner — only structured actions.

    Action shapes (T024):
      {"type": "call", "tool": str, "args": dict}
      {"type": "finish", "summary": str}
      {"type": "awaiting_input", "needs": [str], "message": str}
    An optional "audit" key (model request id / usage / latency / finish
    reason; missing fields null) may accompany any action for trace records.
    """

    planner_kind: str
    label: str

    def next_action(
        self,
        *,
        round_no: int,
        snapshot: Any,
        observations: list[dict[str, Any]],
        procedure_options: list[dict[str, Any]] | None = None,
        available_modes: list[str] | None = None,
    ) -> dict[str, Any]:
        """``procedure_options`` / ``available_modes`` is run context passed
        per call for prompts, never stored."""
        ...


class ScriptedPlanner:
    """Explicitly-injected simulated planner (demo/tests only).

    Actions are a fixed script — there is no model, no inference and no
    hidden reasoning. Always labelled 模拟规划，非DeepSeek实时规划.

    The planner is STATELESS across runs: the action for each decision is
    selected purely by ``round_no`` (the n-th decision of THIS run). The same
    injected instance can therefore serve any number of consecutive runs —
    each run starts again at round 1 — without shared cursors, resets or
    per-run copies (T023-R1).
    """

    planner_kind = "simulated"
    label = SIMULATED_PLANNER_LABEL
    uses_http = False  # 脚本规划不发任何 HTTP；attempts 与 HTTP 计数分离

    def __init__(self, script: list[dict[str, Any]]) -> None:
        self._script = tuple(dict(a) for a in script)

    def next_action(
        self,
        *,
        round_no: int,
        snapshot: Any,
        observations: list[dict[str, Any]],
        procedure_options: list[dict[str, Any]] | None = None,
        available_modes: list[str] | None = None,
    ) -> dict[str, Any]:
        idx = round_no - 1
        if idx < 0 or idx >= len(self._script):
            return {"type": "finish", "summary": "脚本动作已全部执行完毕"}
        action = self._script[idx]
        if action.get("type") == "finish":
            return {"type": "finish", "summary": str(action.get("summary", "脚本结束"))}
        return {"type": "call", "tool": action.get("tool", ""), "args": dict(action.get("args", {}))}
