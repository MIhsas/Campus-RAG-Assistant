# T024 验证记录（submission_revision=2，responds_to=T024-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦返工两链（完成判定、结果区模式标注）；**零外部模型调用、无下载、无安装**；loopback mock + `trust_env=False`；按返工单未重跑全量/ASR/embedding/问答 provider（未改共享代码）。rev1 记录归档 `verification.rev1.md`。

## 1. 聚焦测试（45 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_deepseek_planner.py tests/test_agent_workflow.py -q -p no:cacheprovider --basetemp .cache/t024r1 --tb=short -rs
# 45 passed, 2 warnings in 12.79s
# 退出码：0
```

- **T024-R1 新增 6 项**：
  - `TestCompletionVerdict`（4）：直接 finish（mock 结束语「【模拟】全部办理工作已完成」）→ **stopped**、无产物、message 不含结束语、`planner_summary` 仅记录、请求恰 1；search→finish → **partial**、检索结果保留、message 含「缺少整理草稿/已保留查找依据/未补调用、未重试」、请求恰 2；完整链 → completed + 服务端「均已生成」与「不代表学校审批、办事已办妥或待办已保存」文案；saveable=false 草稿（未知校区筛除依据）→ completed（产物齐）+「saveable=false/暂不可保存」显式。
  - `TestFixedWorkflowVerdict`（2）：搜索 handler 异常+草稿成功 → **partial** 列出「缺少查找依据」；干净固定链 → completed + 服务端完成定义文案。
- 原 39 项保持全过（含 swap/relax 用例按新判定改为 stopped + 「任务未完成」断言；隔离、条件锁、零规划请求、attempts/零重试、装配、loopback 全链对照直接 service 等不变）。

## 2. Astra 独立探针（未改，通过标准未动）

```bash
./.venv/Scripts/python.exe "F:/Collage Paper/docs/collaboration/reviews/T024-R1-probe.py"
# finish_without_tools → status=stopped, draft=null, calls=0, http_attempts=1
# search_then_finish   → status=partial,  draft=null, calls=1, http_attempts=2
# 退出码：0
```

## 3. 页面结果区模式标注（vm stub 层级，非真实浏览器）

```bash
"D:/nodejs/node.exe" scripts/check-workflow-behavior.cjs
# check-workflow-behavior: 5 scenarios passed（vm stub 层级，非真实浏览器），退出码 0

"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 9 HTML files passed syntax check.，退出码 0
```

- 场景④（断言在**结果区** run-label）：deepseek 形状响应 → 含「DeepSeek 规划」「已配置 ≠ 已联调验证」、**不含「模拟规划」**；partial 失败文案/保留结果/attempts 展示不变。
- 场景⑤（新增对照）：模拟响应 → 标「模拟规划」不标 DeepSeek；固定响应 → 标「固定流程/非大模型 Agent」且不带规划模式字样。
- ①—③（年份严格校验、失败清空、网络异常共用清理、快照绑定）保持通过——T023-R1 边界未回归。

**证据层级声明：vm stub 交互模拟，不是真实浏览器证据；浏览器复验交 Astra，不以 stub 冒充。**

## 4. Mock 调用轨迹（重新生成，真实运行）

```bash
./.venv/Scripts/python.exe scripts/trace-agent-planner.py
# [adapter_loopback_full_chain] completed stop=finished http_attempts=3 tools=2
# [adapter_isolation_run_1_defer] completed stop=finished http_attempts=3 tools=2
# [adapter_isolation_run_2_grade_review] completed stop=finished http_attempts=3 tools=2
# [adapter_reject_relax_and_swap] stopped stop=incomplete_artifacts http_attempts=3 tools=0
# [adapter_success_then_http_500] partial stop=planner_error http_attempts=2 tools=1
# [adapter_illegal_json] stopped stop=planner_error http_attempts=1 tools=0
# [adapter_direct_finish_no_artifacts] stopped stop=incomplete_artifacts http_attempts=1 tools=0
# [scripted_planner_contrast] completed stop=finished http_attempts=0 tools=2
# 退出码：0 → mock-planner-trace.json（8 runs；rev1 归档 mock-planner-trace.rev1.json）
```

direct_finish/缺产物场景按新判定输出 stopped + 服务端文案；`planner_summary_recorded_only` 字段单列模型结束语（不作结论）。

## 5. 依赖

未安装依赖、未下载模型、requirements 未改；无需 pip check。

## 6. 未验证项

1. **浏览器真实交互复验**（结果区三模式标注、缺草稿不显「完成」）交 Astra；stub 不冒充浏览器。
2. 真实 DeepSeek 规划联调未验证（planner_live_verified=false；live-smoke-plan 仍未运行）。
