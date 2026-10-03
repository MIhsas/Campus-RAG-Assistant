# T023 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦受限编排与状态真实性；未重测底层检索/解析/ASR/embedding 质量；**零外部模型调用、无模型下载、无网络（TinyAgent 快照为只读拉取，见 tinyagent-assessment.md）**；未读取/打印密钥。

## 1. 受限编排测试（18 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_agent_workflow.py -q -p no:cacheprovider --basetemp .cache/t023 --tb=short -rs
# 18 passed, 2 warnings in 1.07s
# 退出码：0
```

对照任务「验证」清单：

- **一次正常 检索→缓考草稿，对照直接 service 结果及引用**：`test_defer_draft_matches_direct_service` 将 `/agent/workflow/run` 产出的草稿与 `procedures.service.build_draft` 直接结果逐引用对比（block_id + quote 全等）；`test_search_tool_matches_direct_execute_search` 将 `search_policy` 工具命中与 `retrieval.service.execute_search` 直接结果对比（chunk_id 序列全等）。
- **模拟未知工具/循环停止**：`test_unknown_tool_rejected_before_business`、`test_invalid_args_rejected_before_business`（不合法参数在调用业务前拒绝，`result is None`）；`test_repeated_action_stops_loop`（重复动作 → `stop_reason=no_progress`，`tool_calls_used=1`）；`test_tool_call_budget_capped`（≤6 工具、≤4 轮）。
- **条件未被放宽**：`test_planner_cannot_widen_filters`（试图去掉年级限制被拒，`不得放宽或改写`）；`test_matching_filters_accepted_and_summary_reflects_scope`（一致条件通过，`filter_summary.active=true`）。
- **缺模板/缺必要输入明确回退**：`test_missing_template_gives_clear_fallback`（模板未配置拒绝）、`test_missing_input_returns_awaiting`（缺 query → `awaiting_input`）、`test_unknown_procedure_awaiting`（未知事项 → `awaiting_input`，`tool_calls_used=0`）。
- **加载与运行均不自动保存待办、不调用真实模型**：`test_workflow_page_has_no_localStorage_write`（workflow.html 无任何 `localStorage.setItem`/`getItem`/`window.localStorage` 调用）；`test_agent_off_by_default`（Agent 默认关、`plan/run` 503）；`test_demo_planner_label_and_counts`（模拟规划器全程标注、工具计数正确）。
- **工具调用次数与事件，不当作真实模型质量**：`test_events_record_tool_names_no_thought`（事件只含工具名/状态，无 thought/reasoning）。

## 2. 受影响旧页面/API 必要回归（41 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_run_entry.py tests/test_procedures.py tests/test_agent_workflow.py -q -p no:cacheprovider --basetemp .cache/t023b --tb=short -rs
# 41 passed, 2 warnings in 3.19s
# 退出码：0
```

覆盖：T022 统一入口装配/状态、T016 办事草稿/核对、T023 编排。未跑 ASR/embedding/大矩阵。

## 3. 页面 JS 行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 9 HTML files passed syntax check.（退出码 0，workflow.html 新增）

"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 26 scenarios passed（退出码 0）
```

ask.html 行为新增 T022-R1 覆盖：配置了模板 → 相关事项给出入口（带结果快照链接）；未配置 → 明确「本次运行未配置对应指南」且无死入口。

## 4. 本地调用轨迹（真实运行，零外部调用）

```bash
./.venv/Scripts/python.exe scripts/trace-agent-run.py
# [normal_fixed_defer_draft] status=completed stop=None tool_calls=2 rounds=1
# [simulated_planner_happy] status=completed stop=finished tool_calls=2 rounds=3
# [simulated_unknown_tool_and_bad_args] status=completed stop=finished tool_calls=0 rounds=3
# [simulated_relax_rejected_then_no_progress] status=partial stop=no_progress tool_calls=1 rounds=3
# 退出码：0 → call-trace.json
```

四类运行的工具名/状态/次数为真实执行结果，均为脚本化模拟规划器驱动，**不代表真实 Agent/DeepSeek 规划质量**。

## 5. 依赖

未改 requirements（无新增依赖、无框架引入）；无需 pip check。

## 6. 未验证项

1. **真实 Agent/真实 DeepSeek 规划未接入、未验证**（`planner_live_verified=false`）；本轮只有固定流程与显式模拟规划器。
2. **浏览器主路径留待 Astra**（demo-notes 检查表）；stub 不冒充浏览器证据。
3. TinyAgent 官方示例未运行（按任务禁止），Windows CPU + DeepSeek 兼容性未据其验证。
4. 真实学校语料效果不在本轮范围。
