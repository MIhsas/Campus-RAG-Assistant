"""Constrained tool registry for the restricted workflow (T023).

Exactly two read-only tools are registered:

- ``search_policy``        → existing retrieval pipeline (T011/T012 modes +
  applicability filters, in-process, no HTTP self-calls);
- ``build_checklist_draft`` → existing procedures service (T016 citation
  checks + saveable gate).

Never exposed to any planner: 保存/删除待办、Shell、eval、任意 URL、文件读取、
学校登录、生成式问答。Tool handlers never call the answer provider.

Scope conditions (campus/student_type/admission_year/as_of_date) and the
selected procedure come ONLY from the user-submitted run snapshot and are
injected by the execution layer (T026). They are NOT model-writable: the
tool declarations expose only query/mode/top_k (search) and no parameters
(draft). Any attempt to pass ``filters`` / ``procedure_id`` is rejected as
an over-reach BEFORE any business call — never silently dropped and then
executed. The handler-level scope/identity locks remain as defence for
direct calls.

Unknown tools and invalid arguments are rejected before business execution:
a rejection produces no service call and is reported as status "rejected".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class RunSnapshot:
    """User-submitted conditions for one run. Immutable during the run."""

    procedure_id: str | None = None
    query: str | None = None
    filters: dict[str, Any] | None = None


@dataclass
class ToolContext:
    """Everything a tool may read. Built from app state once per run."""

    procedures: dict[str, Any] | None
    documents: list[dict[str, Any]]
    bm25_index: Any
    dense_index: Any
    embedding_service: Any
    available_modes: list[str]
    snapshot: RunSnapshot
    procedure_ids: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        ids = ()
        if self.procedures is not None:
            ids = tuple(p["procedure_id"] for p in self.procedures["procedures"])
        object.__setattr__(self, "procedure_ids", ids)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: list[dict[str, Any]]
    handler: Callable[[dict[str, Any], ToolContext], dict[str, Any]]


# ---------------------------------------------------------------- validation

def _reject(reason: str) -> dict[str, Any]:
    return {"status": "rejected", "error": reason, "result": None}


def _check_args(
    spec: ToolSpec, args: dict[str, Any], ctx: ToolContext
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate arguments strictly. Returns (clean_args, None) or (None, reason)."""
    if not isinstance(args, dict):
        return None, "args 必须是对象"
    # 越权参数（T026）：范围条件与已选事项由服务端用户快照固定，模型不得构造；
    # 传入即明确拒绝（不静默忽略后执行）。声明中也不出现这些参数。
    forbidden = {
        "filters": "范围条件由服务端用户快照固定（不得放宽或改写），规划器不得传入 filters",
        "procedure_id": "不得擅自更换事项——已选事项由服务端用户快照固定，规划器不得传入 procedure_id",
    }
    for name in sorted(args):
        if name in forbidden:
            return None, forbidden[name]
    declared = {p["name"] for p in spec.parameters}
    unknown = set(args) - declared
    if unknown:
        return None, f"未知参数：{'、'.join(sorted(unknown))}"

    clean: dict[str, Any] = {}
    for p in spec.parameters:
        name = p["name"]
        if name not in args:
            if p.get("required"):
                return None, f"缺少必需参数：{name}"
            continue
        v = args[name]
        t = p.get("type")
        if t == "string":
            if not isinstance(v, str):
                return None, f"{name} 必须是字符串"
            if name == "query":
                if not (1 <= len(v) <= 500) or not v.strip():
                    return None, "query 长度须在 1—500 且非全空白"
            elif not v:
                return None, f"{name} 不能为空"
        elif t == "integer":
            if isinstance(v, bool) or not isinstance(v, int):
                return None, f"{name} 必须是整数"
            lo, hi = p.get("min"), p.get("max")
            if lo is not None and v < lo:
                return None, f"{name} 不能小于 {lo}"
            if hi is not None and v > hi:
                return None, f"{name} 不能大于 {hi}"
        elif t == "enum":
            if v not in p.get("enum", []):
                return None, f"{name} 取值无效：{v!r}"
            if name == "mode" and v not in ctx.available_modes:
                return None, f"检索模式 {v} 本次运行不可用（当前：{'、'.join(ctx.available_modes)}）"
        elif t == "object":
            if v is not None and not isinstance(v, dict):
                return None, f"{name} 必须是对象或 null"
        clean[name] = v

    return clean, None


# -------------------------------------------------------------------- tools

def _search_policy(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from campus_assistant.retrieval.service import execute_search

    query = args.get("query") or ctx.snapshot.query
    if not query:
        return _reject("缺少查询问题（快照未提供 query）")
    mode = args.get("mode", "bm25")
    top_k = args.get("top_k", 5)
    out = execute_search(
        query=query,
        mode=mode,
        top_k=top_k,
        filters_norm=ctx.snapshot.filters,
        documents=ctx.documents,
        bm25_index=ctx.bm25_index,
        dense_index=ctx.dense_index,
        embedding_service=ctx.embedding_service,
    )
    return {
        "status": "ok",
        "error": None,
        "result": {
            "query": query,
            "mode": mode,
            "top_k": top_k,
            "hit_count": len(out["hits"]),
            "hits": out["hits"],
            "filter_summary": out["filter_summary"],
        },
    }


def _build_checklist_draft(args: dict[str, Any], ctx: ToolContext) -> dict[str, Any]:
    from campus_assistant.procedures.service import build_draft

    requested = args.get("procedure_id")
    # 事项身份锁（T024）：当前用户已选事项不得被规划器悄悄换成另一个。
    if (
        requested is not None
        and ctx.snapshot.procedure_id is not None
        and requested != ctx.snapshot.procedure_id
    ):
        return _reject(
            f"不得擅自更换事项：用户已选「{ctx.snapshot.procedure_id}」，请求的是「{requested}」。"
            "确需更换请返回 awaiting_input 请求用户确认，不要直接换。"
        )
    procedure_id = requested or ctx.snapshot.procedure_id
    if not procedure_id:
        return _reject("缺少办事事项（快照未提供 procedure_id）")
    if ctx.procedures is None:
        return _reject("办事模板未配置（本次运行无可用模板，可改用原文检索摘录）")
    if procedure_id not in ctx.procedure_ids:
        return _reject(
            f"事项 ID 不在当前已配置列表：{procedure_id}（当前：{'、'.join(ctx.procedure_ids) or '无'}）"
        )
    draft = build_draft(ctx.procedures, procedure_id, ctx.snapshot.filters, ctx.documents)
    return {"status": "ok", "error": None, "result": draft}


# T026：声明只含模型实际可写参数——固定筛选与已选事项由服务端快照注入，
# 不向模型暴露 filters/procedure_id（传入即按越权参数拒绝，见 _check_args）。
SEARCH_POLICY_PARAMS: list[dict[str, Any]] = [
    {"name": "query", "description": "要查找的政策问题；省略则使用用户提交快照中的问题",
     "required": False, "type": "string"},
    {"name": "mode", "description": "检索模式（仅限本次运行可用项，默认 bm25）",
     "required": False, "type": "enum", "enum": ["bm25", "dense", "hybrid"]},
    {"name": "top_k", "description": "返回条数 1—20，默认 5",
     "required": False, "type": "integer", "min": 1, "max": 20},
]

# build_checklist_draft 无模型可写参数：事项由用户已选快照固定。
DRAFT_PARAMS: list[dict[str, Any]] = []


def build_tool_registry() -> dict[str, ToolSpec]:
    """The full tool set. Nothing beyond these two read-only tools exists."""
    return {
        "search_policy": ToolSpec(
            name="search_policy",
            description="按用户提交的范围条件检索政策原文依据（只读；复用检索服务的模式与条件筛选）",
            parameters=SEARCH_POLICY_PARAMS,
            handler=_search_policy,
        ),
        "build_checklist_draft": ToolSpec(
            name="build_checklist_draft",
            description="按当前模板与语料生成带引用核对的办理草稿（只读；不保存任何待办）",
            parameters=DRAFT_PARAMS,
            handler=_build_checklist_draft,
        ),
    }


def tool_catalog() -> list[dict[str, Any]]:
    """Public description of the tool set (status endpoint)."""
    reg = build_tool_registry()
    return [
        {"name": s.name, "description": s.description, "parameters": s.parameters}
        for s in reg.values()
    ]


def run_tool(
    registry: dict[str, ToolSpec], tool_name: str, args: Any, ctx: ToolContext
) -> dict[str, Any]:
    """Dispatch one tool call. Unknown tools / invalid args are rejected
    BEFORE any business code runs."""
    spec = registry.get(tool_name)
    if spec is None:
        return {"tool": tool_name, **_reject(f"未知工具：{tool_name}（本运行仅开放 search_policy、build_checklist_draft）")}
    clean, reason = _check_args(spec, args, ctx)
    if reason is not None:
        return {"tool": tool_name, **_reject(f"参数不合法：{reason}")}
    out = spec.handler(clean, ctx)
    return {"tool": tool_name, **out}
