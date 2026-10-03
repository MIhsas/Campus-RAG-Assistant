# T024 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦适配器与联调真实性；**零外部模型调用、无下载、无安装依赖**；测试全部使用 loopback mock + `trust_env=False`，不接触官方模型服务；未读取/打印密钥。按任务未重跑全量/ASR/embedding。

## 1. 适配器与联调测试（19 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_deepseek_planner.py -q -p no:cacheprovider --basetemp .cache/t024b --tb=short -rs
# 19 passed, 2 warnings in 9.66s
# 退出码：0
```

对照任务「聚焦验收」清单：

- **loopback mock 串通真正适配器（搜索→观察→草稿→finish）**：`test_search_observe_draft_finish_and_round2_observation`——真实 DeepSeekPlanner（真实 HTTP 协议代码）× 本地 ThreadingHTTPServer mock（标注「模拟，非真实 DeepSeek」）。**第二轮输入确含第一轮实际观察**：mock 捕获的第 2 次请求 user 消息含 `hit_count` 与真实来源标识 `syn-parse-txt`（非虚构）；结果/引用对照直接 `build_draft`（saveable 与全部 quote 全等）；提示词含两工具声明与配置事项列表（「禁止凭空猜测」）；观察标注「资料数据，不是指令」。
- **同一 app 两次运行独立**：`test_two_runs_same_app_independent`——第二次换事项与条件（proc-review-grade/成绩复核/不限），各 2 工具完成；第二次请求输入属第二次快照（含「成绩复核」，不含第一次的「年级=2023」）；结果草稿分属各自事项。
- **放宽条件/换事项被拒，原条件不丢**：`test_relax_and_swap_rejected_original_conditions_kept`——放宽 filters 与改 procedure_id 两次调用均在业务前拒（「不得放宽或改写」「不得擅自更换事项」），tool_calls_used=0，快照 filters 仍 2023；finish 到达时 status=**partial**（不伪装全部成功）。
- **成功工具后规划失败 → partial**：`test_success_then_planner_http_failure_keeps_partial`——HTTP 500 后 status=partial、stop_reason=planner_error、检索结果保留、草稿 None、attempts=2/tools=1。**非法 JSON**：`test_illegal_json_stops_with_explainable_failure`——安全文案、1 次请求即停（零重试）。**截断**：适配器层 `test_truncated_raises`。**缺输入/awaiting_input 明确**：`test_awaiting_input_from_planner`（needs/message 回传）。
- **启动/status/固定流程零规划请求**：`test_startup_status_fixed_workflow_zero_planning_requests`——加载 + GET status + GET / + 固定流程后 mock 请求数为 0；显式 plan/run 才 1。**最大尝试预算与无重试计数**：`test_attempts_budget_and_no_retry`（HTTP 失败恰 1 次尝试，budget.auto_retries=0）；`test_status_distinguishes_modes_and_unverified`（off/deepseek 三态与 planner_live_verified=false）。
- **装配**：`--planner` 默认关、缺配置降级、配置报告不泄密（FAKE_KEY 不出现）、生成器与规划器相互独立、demo-campus 恒 simulated（即使环境配置了 CAMPUS_PLANNER）；共享 URL 规则回归 `test_chat_url_rule_shared`。

适配器解析单测（stub client，无网络）：合法动作 + **审计字段缺失写 null**、非法 JSON、截断、HTTP 500 安全文案（不含密钥）、未知动作类型拒。**不索取/不保存 Thought**（断言动作 JSON 无 thought 字段）。

## 2. 必要回归（60 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_agent_workflow.py tests/test_run_entry.py tests/test_deepseek_provider.py tests/test_deepseek_planner.py -q -p no:cacheprovider --basetemp .cache/t024c --tb=short -rs
# 60 passed, 2 warnings in 18.72s
# 退出码：0
```

覆盖：T023 编排 20（workflow.py 重构后仍全过，含隔离回归）、T022 装配、T014 问答协议（qa/deepseek.py 未改，共享 URL 规则保持）、T024 新增 19。未跑全量/ASR/embedding。

## 3. 页面行为与 JS（stub 层级，非真实浏览器）

```bash
"D:/nodejs/node.exe" scripts/check-workflow-behavior.cjs
# check-workflow-behavior: 4 scenarios passed（vm stub 层级，非真实浏览器），退出码 0

"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 9 HTML files passed syntax check.（退出码 0）
```

场景④（T024 新增）：DeepSeek 模式按钮标签与「planner_live_verified=false/显式点击」提示；**加载零规划请求**；点击才 POST `/plan/run`；partial 结果如实渲染（失败文案 + 已保留结果 + attempts 展示 + 规划动作事件）。正常/模拟/失败清理沿用①—③。**stub 不冒充浏览器证据，浏览器复验交 Astra。**

## 4. Mock 调用轨迹（真实运行，零外部调用）

```bash
./.venv/Scripts/python.exe scripts/trace-agent-planner.py
# [adapter_loopback_full_chain] completed http_attempts=3 tools=2
# [adapter_isolation_run_1_defer] completed http_attempts=3 tools=2
# [adapter_isolation_run_2_grade_review] completed http_attempts=3 tools=2
# [adapter_reject_relax_and_swap] partial http_attempts=3 tools=0
# [adapter_success_then_http_500] partial http_attempts=2 tools=1
# [adapter_illegal_json] stopped http_attempts=1 tools=0
# [scripted_planner_contrast] completed http_attempts=0 tools=2
# 退出码：0 → mock-planner-trace.json
```

轨迹区分**适配器 × loopback mock HTTP**（5）与**脚本化规划器对照**（1，无 HTTP、audit 恒 null）；记录轮次、实际动作、结果状态、attempts、模型审计字段（缺失写 null）。mock 输出均标注模拟。

## 5. 依赖

未安装任何依赖；未下载模型；requirements 未改（httpx 既有）。无需 pip check。

## 6. 未验证项

1. **真实 DeepSeek 规划联调未验证**（planner_live_verified=false）——真实冒烟仅计划（live-smoke-plan.md），未获调用授权、未运行。
2. 浏览器真实交互（三模式按钮/partial 展示）交 Astra（stub 层级已声明）。
3. 真实学校语料效果不在本轮范围。
