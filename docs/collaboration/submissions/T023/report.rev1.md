# T023 受限任务编排与 TinyAgent 适配验证 — 实施报告

身份：task_id=T023、task_revision=v1、submission_revision=1、status=ready_for_review、**tinyagent_integration_kind=reference、planner_live_verified=false、external_model_calls=0**（零外部模型调用；无模型下载；密钥零暴露）。

## 概述

把既有「查政策 + 办理草稿」接成受限工具流程，落实 docs/04 的 Agent 可替换层：定义可替换 Planner 契约与工具注册表，本轮只开放 `search_policy` / `build_checklist_draft` 两个只读工具；固定工作流（选事项→检索→草稿）与显式注入的模拟规划器共用同一套工具；首页/工作流页如实展示实际步骤与引用。核对了 Datawhale TinyAgent 的源码、许可与适配范围，结论为**仅参考、自研受限编排**（无运行时代码复用）。顺手完成 T022-R1 非阻断整理。

## 功能交付（对照任务书）

1. **TinyAgent 核查与适配结论**（`tinyagent-assessment.md` + `tinyagent-snapshot/`）：只读拉取官方 Agent.py/LLM.py/tool.py/readme/requirements，记录 commit（main HEAD `a5ae08d…`）、文件 SHA-256 与上游 blob SHA、来源与许可（**GitHub license=null、无 LICENSE 文件 → 无明确可复用许可**）。适配结论：无可直接复用的运行时代码，仅可参考「工具声明式注册 + 动作→工具→观察循环 + 结构化动作解析」的接口形状；模型层（InternLM2Chat + transformers + `.cuda()`）与工具层（硬编码 `google_search` + serper.dev 付费搜索）必须替换。**只有参考其思路，故写「参考 TinyAgent，自研受限编排」；不写「已集成」**；未运行其示例、未下载 InternLM、未开启默认工具；不据其声称 Windows CPU+DeepSeek 已兼容。

2. **可替换编排接口**（`agent/planner.py`）：定义 `Planner` 协议（`planner_kind`/`label`/`next_action`）作为未来 DeepSeek 适配器的连接契约（仅设计，未实现）。本轮唯一实现是显式注入的 `ScriptedPlanner`（脚本化动作，无模型、无隐藏推理），全程标注「模拟规划，非DeepSeek实时规划」。

3. **只读工具注册表**（`agent/tools.py`）：仅 `search_policy`（复用 retrieval.service 的 mode/filters）、`build_checklist_draft`（复用 procedures.service 的引用核查与 saveable 门）。直接调既有 service——不 HTTP 自调、不复制业务、不触碰 generated 问答。**范围条件只来自用户提交的快照，规划器省略 filters 即用快照，传不同 filters 在调用业务前被拒**；事项 ID 必须来自当前已配置列表。**不向规划器暴露保存/删除待办、Shell、eval、任意 URL、文件读取、学校登录**。未知工具/不合法参数在调用业务前拒绝（`result is None`）。

4. **固定流程与模拟规划器共用工具**（`agent/workflow.py`）：固定流程明确「选事项→查找依据→整理草稿」，`workflow_label` 含「非大模型 Agent」，不被伪称 LLM Agent；模拟规划器走同一循环。普通服务默认 `planner=None`（Agent 模式关）；模拟规划仅由 `demo-campus.py` 显式注入。**不新写真实 DeepSeek 规划接口**，只留连接契约。

5. **预算与停止**：沿用上限 ≤4 轮规划 / ≤6 次工具执行；无进展重复动作停止（`no_progress`）；未知/非法参数先拒绝。事件记录实际工具名/状态/次数，**不输出模型 Thought/隐藏推理**。总时限用**单调时钟**在步骤间检查，`cancellable_note` 如实说明「同步本地工具不支持中途取消，停止只终止后续调度，正在执行的工具会运行完毕」——不谎称线程超时即取消底层计算。部分成功保留已完成结果；缺必要事项/条件返回 `awaiting_input` + `input_needed` 表单提示，不瞎猜、不挂起。

6. **工作流页/API**（`static/workflow.html` + `/api/v1/agent/*`）：轻量页展示「查找依据→整理草稿」的实际步骤状态与结果引用（不造假进度——步骤状态取自真实执行事件）。草稿仍需用户进入既有办理页核对后**手动保存**；页内**不写 localStorage**；「进入办理页」链接携带本次条件快照。模拟规划仅在注入时显示独立按钮并标注。缺模板时给清楚回退入口（503 + 改用 /search、/ask 摘录的说明）。

7. **T022-R1 非阻断整理**：① ask 页相关事项仅推荐当前已配置事项，否则明确「本次运行未配置对应指南」，不给死入口（`loadProceduresConfigured` + 渲染门控）；② 未配置生成器文案改为「需显式 `--generator deepseek` 开启并配密钥，仅配密钥不自动启用」，与显式开关要求一致；③ 首页「关键词恒可用」改为「语料索引就绪后可用」；④ 状态接口非预期失败显示「读取失败/未知（HTTP x）」而非当作未配置。

## 验证摘要（真实命令见 verification.md）

- `tests/test_agent_workflow.py` **18 passed**：正常检索→缓考草稿对照直接 service 结果与引用、未知工具/非法参数/重复停止/预算、条件未放宽、缺模板/缺输入回退、不自动保存/不调真实模型、Agent 默认关。
- 必要回归 `test_run_entry + test_procedures + test_agent_workflow` = **41 passed**。
- JS 语法 9 页通过（workflow.html 新增）；ask 行为 26 场景通过（含 T022-R1 双分支）。
- 本地调用轨迹 4 类运行真实产出（`call-trace.json`），零外部调用。

## 修改与新增文件

- 新增：`src/campus_assistant/agent/{__init__,tools,planner,workflow}.py`、`src/campus_assistant/api/agent.py`、`src/campus_assistant/static/workflow.html`、`tests/test_agent_workflow.py`、`scripts/trace-agent-run.py`
- 修改：`src/campus_assistant/main.py`（planner 开关 + agent 路由 + /workflow 页）、`scripts/serve-corpus.py`（planner 透传）、`scripts/demo-campus.py`（演示注入模拟规划器）、`src/campus_assistant/static/home.html`（T022-R1×3 + 流程入口卡）、`src/campus_assistant/static/ask.html`（T022-R1×2）、`scripts/check-ask-behavior.cjs`（双分支覆盖）
- 提交另附：`tinyagent-assessment.md`、`tinyagent-snapshot/`（5 文件留档）、`call-trace.json`
- 清单见 `changed-files.json`（sha256+size）；未修改：Astra 文档、旧语料/gold、既有 service 判断算法、用户本机存储。

## 已知限制

- **真实 Agent 未接入**：`planner_live_verified=false`。只有固定流程与模拟规划器；不宣称自然语言规划效果已验证、不称真实 Agent 已接入。
- **TinyAgent 无明确许可**：源码快照仅留档评估，未进入 `src/`；不复制、不引其依赖。
- **无浏览器工具**：浏览器主路径留待 Astra（demo-notes 检查表）。
- 测试资料为合成性质，不代表真实校园效果。

完成后停止，等待 Astra 验收。T024 未发布。
