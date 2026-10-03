# T026 规划参数收敛与观察完整性 — 实施报告

身份：task_id=T026、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0、planner_live_verified=false、tinyagent_integration_kind=reference**。零外部模型调用、无下载、无安装；未执行 live（T025 B 一次授权已结束，不延续）；未修改 T025 原始 `live-run.json`。

## 概述

依据 T025 真实记录与 T025-R3 结论，做两件离线收敛：① 规划专用工具声明只暴露模型可写参数（固定筛选与已选事项由服务端快照注入），**保留越权参数明确拒绝**（不静默忽略后执行）；② 有界观察补总数/已列数/截断标记（4 项待核实只列 3 时不再误导为「总共 3」）。附 T025 事件顺序勘误。完成判定、HTTP 预算与业务契约均未改动。

## 功能交付（对照任务书）

1. **规划专用声明**（`agent/tools.py`）：`search_policy` 声明仅 `query/mode/top_k`（mode 限本次可用项、默认 bm25）；`build_checklist_draft` **无参数**（事项由用户已选快照固定）。执行层从快照注入 filters 与 procedure_id。**越权拒绝保留且前置**：模型传 `filters`/`procedure_id`（哪怕与快照一致）→ 明确拒绝（「不得放宽或改写」「不得擅自更换事项」措辞保留），绝不静默忽略后执行；handler 层范围/事项锁保留为直调防御。`tool_catalog()`（status 展示）与校验规则同源一致；**既有搜索/办理 API 契约未动**。最小实现，无工具框架。

2. **清晰工具说明**（`agent/deepseek_planner.py`）：系统提示提供**一组正确 JSON call 示例**（args 明确省略固定条件与事项，含 finish/awaiting_input 示例）；**模式可用性依据本次上下文**（`available_modes` 逐次传入、默认 BM25）；声明只列实际支持参数（草稿标注「无参数；范围条件与已选事项由服务端固定注入」）；缺用户输入依旧 awaiting_input、不猜事项（「禁止凭空猜测或自造 ID」保留）。

3. **观察完整性**（`agent/workflow.py`）：保留现有预算（命中 ≤3、issues ≤3、待核实 ≤3、逐字段截断），每个有界集合增加**总数/已列数/截断标记**（`*_total/*_listed/*_truncated`）：实测真实草稿待核实 4 项、观察列 3 → `pending_items_total=4 / listed=3 / truncated=true`，完整草稿仍 4 项不受摘要影响（证据/issue 同口径）。UI/报告不以模型 summary 覆盖工具完整结果（本轮未改 UI；页面本就分离展示）。

4. **事实说明**：`T025-evidence-errata.md` 勘误事件顺序（命中发生在第 2 轮、其观察供第 3 轮使用；第 2 轮只能接收第 1 轮拒绝信息），区分事件证据/代码推断的提示构造/实际捕获的出站请求（live-run **未保存出站 messages**，不声称日志已直接记录请求内容）。明确真实链路已通、完整冒烟含一次拒绝，**planner_live_verified 继续 false**，不擅自升级。

## 验证摘要（本地回放 + loopback mock + 聚焦回归，真实命令见 verification.md）

- **离线回放**（`scripts/t026-offline-replay.py` → `offline-replay.json`，loopback mock 明确标记）：出站声明（mock 捕获的真实 payload）无 filters/procedure_id 参数条目、草稿声明无参数、示例与模式行齐备；**T025 第 1 轮原样坏动作仍被拒**（业务前拒、快照 2023 未放宽、draft 与直接 service 全等、finish 不伪装成功 → partial/failed_actions）；**同一服务下一次独立运行 completed**；观察截断 4/3/true 与完整草稿 4 项一致。
- **聚焦回归 62 passed**（agent + planner + smoke）：含新增声明/越权拒绝/回放/观察透明用例；T024 既有短语断言（「不得放宽或改写」「不得擅自更换事项」）零回归。未改 UI 不跑页面、未跑全量。
- **口径**：mock 正常结果**不证明真实模型改进**，不宣称错误率降低或真实效果改善。

## 修改与新增文件

- 新增：`scripts/t026-offline-replay.py`
- 修改：`agent/{tools,deepseek_planner,workflow,planner}.py`、`tests/{test_agent_workflow,test_deepseek_planner}.py`
- 提交另附：`offline-replay.json`、`T025-evidence-errata.md`；清单见 `changed-files.json`
- 未修改：UI、语料/gold/模板、完成判定（`_finish_verdict` 未动）、HTTP 预算、T025 原始记录、Astra 文档

## 简明后续计划

1. **是否再做一次真实冒烟由用户/Astra 另行决定**——T025 B 授权已耗尽，本任务不自动请求、不执行任何付费调用。若再跑，核对重点：新声明下模型是否不再自造 filters、完整链是否可免拒绝完成；预算与判定口径不变。
2. 人工核对遗留（T025 live-review-notes）仍待用户：草稿 4 步骤语义、4 项未明确事项确认。
3. 若后续接入真实学校语料，先走 T021 登记/preview 核对流程，不以合成结果外推。
4. 无 UI 变更需求挂起；下一处如涉页面，再补 stub 层级检查与浏览器复验。

完成后停止，等待 Astra 验收。T027 未发布。
