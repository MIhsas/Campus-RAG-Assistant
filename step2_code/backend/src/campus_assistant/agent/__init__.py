"""Restricted task orchestration layer (T023).

A replaceable planner/agent-adapter boundary with a constrained tool
registry. This round ships:

- a fixed workflow (选事项→查找依据→整理草稿) that is explicitly NOT an
  LLM agent — it is a deterministic pipeline over the same tools;
- an optional planner loop driven by an explicitly injected planner
  (this round: a scripted simulated planner only, labelled
  "模拟规划，非DeepSeek实时规划"). Normal runs never enable planner mode.

Reference note: the planner/tool boundary is informed by Datawhale
tiny-universe/content/TinyAgent (see submissions/T023/tinyagent-assessment.md).
No code of that repository is imported; integration kind is "reference".
"""

from campus_assistant.agent.planner import (
    SIMULATED_PLANNER_LABEL,
    Planner,
    ScriptedPlanner,
)
from campus_assistant.agent.deepseek_planner import DeepSeekPlanner, planner_from_env
from campus_assistant.agent.tools import (
    RunSnapshot,
    ToolContext,
    build_tool_registry,
    run_tool,
    tool_catalog,
)
from campus_assistant.agent.workflow import (
    DEFAULT_DEADLINE_S,
    MAX_PLAN_ROUNDS,
    MAX_TOOL_CALLS,
    run_fixed_workflow,
    run_planner_loop,
)

__all__ = [
    "DEFAULT_DEADLINE_S",
    "MAX_PLAN_ROUNDS",
    "MAX_TOOL_CALLS",
    "SIMULATED_PLANNER_LABEL",
    "DeepSeekPlanner",
    "Planner",
    "RunSnapshot",
    "ScriptedPlanner",
    "ToolContext",
    "build_tool_registry",
    "planner_from_env",
    "run_fixed_workflow",
    "run_planner_loop",
    "run_tool",
    "tool_catalog",
]
