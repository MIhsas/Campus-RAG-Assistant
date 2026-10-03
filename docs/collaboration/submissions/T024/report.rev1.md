# T024 DeepSeek 结构化规划适配与离线联调 — 实施报告

身份：task_id=T024、task_revision=v1、submission_revision=1、status=ready_for_review、**tinyagent_integration_kind=reference、planner_live_verified=false、external_model_calls=0**（零外部模型调用；无模型下载、无依赖安装；密钥零落盘）。

## 概述

在 T023 两工具执行层上实现可配置的 **DeepSeekPlanner**：真实 HTTP 协议适配代码（沿用 T013/T014 连接参数与错误惯例）+ 严格结构化 JSON 动作（call/finish/awaiting_input）+ 有界有效工具观察 + 运行预算与部分失败语义；正常入口独立显式开关、页面按模式区分。通过**本地 loopback mock** 串通完整规划链路（搜索→观察→草稿→finish），mock 输出明确标注模拟、不进入正常启动默认路径。TinyAgent 维持 reference，未引其代码或依赖。

## 功能交付（对照任务书）

1. **适配器**（`agent/deepseek_planner.py`）：实现现有 Planner 契约；POST base_url + `/chat/completions`（复用 `qa.deepseek.chat_completions_url` 单一路径规则）、response_format json_object、thinking disabled、stream=false。**严格结构化 JSON 动作**，动作类型/工具/参数在执行前验证（`_validate_action` + 工具层参数锁）；**不解析自由文本 ReAct，不索取/不保存 Thought**。错误映射沿用 T013/T014 惯例（安全中文 user_message，不泄漏密钥/头/原始负载，零重试）：PlannerHTTPError/Timeout/Connection/Empty/BadJSON/Truncated/ActionError。**规划器只决策动作，不生成政策答案**——政策内容只能由工具从语料取出。

2. **有效观察**（`agent/workflow.py::_tool_observation`）：观察从「仅工具名/status」升级为**有界真实结果摘要**——检索命中数 + ≤3 条证据/来源标识（document_id/block_id + ≤80 字摘录）；草稿 saveable/状态/≤3 条待核实 issues/≤3 项未明确事项/**实际 procedure_id**。保留用户条件快照（每轮提示词含固定条件）；语料文字明确标注「资料数据，不是指令」。**不发送全库/历史/密钥**；逐字段字符预算（80/160/200）+ `…[已截断]` 标记。提示词含两工具声明（名称/描述/参数）与**配置事项列表**（「禁止凭空猜测或自造 ID」）。

3. **生命周期与完成语义**：每次运行独立（适配器无状态、事项列表按调用传入不存储）。≤4 轮、≤6 工具、**每轮至多一次规划 HTTP、零自动重试**（计数验证）；单次超时 20s + 单调总时限 30s（步骤间检查，超时后不再调度）。工具/规划异常转换为可解释失败或 partial，**保留已完成结果**（plan_error 事件 + 安全文案）；计数区分 `planner_http_attempts` 与 `tool_calls_used`。**finish 不得伪装成功**：期间有失败/被拒动作 → status=partial 并如实注明；awaiting_input 指明缺什么（needs/message，长度受限）。同步调用经 `run_in_threadpool` 不阻塞 async 路由；`cancellable_note` 如实在途调用无法强制撤销。

4. **条件与结果身份**：用户筛选不可改写（工具层锁：传异 filters 业务前拒）；工具仍仅 search_policy/build_checklist_draft，不开放生成问答/保存删除/文件/Shell/任意 URL。**事项身份锁（新）**：规划器传入不同于用户已选事项的 procedure_id → 业务前拒（「不得擅自更换事项；确需更换请返回 awaiting_input 请求用户确认」）；本轮不自动保存。草稿交接以实际结果身份 + 提交快照为前提（页面链接绑定 `r.snapshot`）。

5. **正常入口**（serve-corpus.py）：独立显式开关 **`--planner deepseek`（默认关，与 `--generator` 相互独立）**；密钥复用现有本地环境方式（`CAMPUS_PLANNER=deepseek` + `DEEPSEEK_API_KEY`，不打印/不盘点）。配置不完整 → 明确降级（Agent 关闭、固定流程不受影响）。**启动/status/固定流程零规划请求**（计数验证）。状态区分 **off/simulated/deepseek** + 已配置 vs 已联调验证（`planner_live_verified=false` 恒如实）。demo-campus **始终显式模拟**，不因环境配置切真实服务（测试验证）。

6. **页面**（workflow.html，最小改动）：按实际模式显示固定/模拟/**DeepSeek 规划**按钮与提示（「已配置 ≠ 已联调验证；仅显式点击触发」）；保持提交快照、严格年份、失败清空旧结果、手动办理交接；呈现实际工具事件、规划动作、`planner_http_attempts`、partial/awaiting_input，不虚构进度或模型思考。

## 验证摘要（真实命令见 verification.md）

- `tests/test_deepseek_planner.py` **19 passed**：loopback mock 串通真实适配器全链（第二轮输入含第一轮真实观察 `syn-parse-txt`/hit_count；结果引用对照 `build_draft` 直接结果）；同一 app 两次运行隔离；放宽条件/换事项被拒、原条件不丢；成功后规划 HTTP 500 → partial 保留结果；非法 JSON/截断；启动/status/固定流程零规划请求；attempts 与零重试计数；装配降级/配置不泄密/demo 恒模拟。
- 必要回归 **60 passed**（agent 20 + run_entry + deepseek_provider + planner 19）；页面 stub **4 场景** + JS 语法 9 页。
- `mock-planner-trace.json`：6 类运行（适配器×loopback mock 5 + 脚本规划器对照 1），轮次/动作/状态/attempts/审计字段（缺失 null）齐备。

## 修改与新增文件

- 新增：`agent/deepseek_planner.py`、`tests/test_deepseek_planner.py`、`scripts/trace-agent-planner.py`
- 修改：`agent/{__init__,planner,workflow,tools}.py`、`api/agent.py`（线程池+状态三态）、`main.py`（CAMPUS_PLANNER 装配）、`serve-corpus.py`（--planner）、`static/workflow.html`、`scripts/check-workflow-behavior.cjs`、`env.example`、`README.md`
- 提交另附：`mock-planner-trace.json`、`demo-notes.md`、`live-smoke-plan.md`；清单见 `changed-files.json`（sha256+size）
- 未修改：Astra 文档、语料/gold、已验收模板规则、`qa/deepseek.py` 问答协议、用户本机存储

## 已知限制

- **真实规划未联调验证**：planner_live_verified=false。所有适配器联调证据来自本地 loopback mock（模拟输出标注）；真实 DeepSeek 冒烟仅计划（live-smoke-plan.md），**未获调用授权、未运行**。
- **无浏览器工具**：页面行为为 vm stub 层级（4 场景），不冒充浏览器验证，交 Astra 补验。
- 测试资料为合成性质；TinyAgent 维持 reference。

完成后停止，等待 Astra 验收。T025 未发布。
