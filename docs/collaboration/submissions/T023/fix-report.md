# T023-R1 定向返工 — 修复报告（fix-report）

身份：task_id=T023、task_revision=v1、**submission_revision=2、responds_to=T023-R1**、status=ready_for_review、tinyagent_integration_kind=reference、planner_live_verified=false、external_model_calls=0。rev1 全部文件已归档为 `*.rev1.*` 保留。

本轮仅改：`agent/planner.py`（规划状态）、`static/workflow.html`（页面）、直接相关测试/检查/说明；未接真实规划器、未改产品语料/gold、无下载/安装/付费调用。

## 修复 1（P1）：模拟规划状态跨请求共享，第二次运行空完成

**问题**（Astra 真实浏览器复现）：`ScriptedPlanner._i` 游标在实例内累加，app state 复用同一实例，连续两次点击模拟规划，第二次「工具调用 0 次、脚本动作已全部执行完毕」，结果消失。

**修复**（`src/campus_assistant/agent/planner.py`）：改为**无状态脚本按本轮 `round_no` 取动作**（返工单给出的两种方案之一）——删除 `_i` 游标，`next_action` 以 `round_no - 1` 直接索引不可变脚本；每次运行从第 1 轮重新开始，同一注入实例服务任意多次连续运行均独立执行，不靠重启/刷新/reset。注入边界未改（返工单允许调整，此处无需调整）。

**回归**（同一 app/client 连续两次请求，第二次换事项与条件）：
- `tests/test_agent_workflow.py::TestPlannerRunIsolation` 2 项（新增）：
  - `test_same_instance_two_runs_both_execute`：同一实例两次 `run_planner_loop` 均 `tool_calls_used=2`，第二次草稿 `procedure_id=proc-review-grade`、检索 `query=成绩复核`、快照 `filters=None`。
  - `test_same_client_two_consecutive_api_runs`：TestClient 两次 `POST /plan/run`（第一次 缓考/2023，第二次 成绩复核/不限），第二次照常执行 2 次工具且结果属第二次快照，第一次结果未被覆盖（草稿仍为 proc-apply-defer、快照仍 2023）。
- 本地调用轨迹 `call-trace.json` 新增 `shared_planner_run_1_defer` / `shared_planner_run_2_grade_review`：同一实例连续两跑，各 `tool_calls=2`（rev1 轨迹归档于 `call-trace.rev1.json`）。

## 修复 2（P1）：非空无效年份被静默转为不限

**问题**：`workflow.html` `parseInt('abc')` → NaN → JSON 转 null，条件被放宽（草稿出现「需医院证明」、办理链接年级为空）。

**修复**（`static/workflow.html`）：新增 `parseYearStrict()`——留空=不限（保留用户意图）；非空必须整串匹配 `^[0-9]{4}$` 且在 1900—2100，否则**提示并停止提交**（`buildBody` 返回错误，`run()` 不发请求）。不截断部分字符串（`2023abc` 整串非法，不会取成 2023），不再经 parseInt 静默转 null。

**回归**（三类，`scripts/check-workflow-behavior.cjs` 场景①）：`2023` → 提交且 `admission_year: 2023`；空白 → 提交且 `null`（=不限）；`abc` 与 `2023abc` → **不发出请求** + 显示「入学年份格式无效……留空表示不限」+「未提交本次请求」。

## 修复 3（P2）：失败后旧依据/旧草稿/办理入口残留

**问题**：成功运行后填 `bad-date` 触发 422，旧 evidence-panel/draft-panel 与可点击办理链接仍显示为当前内容，无失效标识。

**修复**（`static/workflow.html`）：采用返工单建议的**简单清空方案**——`clearResults()` 在每次新请求开始时清空并隐藏依据/草稿/办理入口/步骤区；失败（422、无效 JSON、网络异常）经同一 `showFailure()` 清理路径，明确显示「**本次未生成新结果**；下方不保留旧依据与旧草稿」。成功结果新增「**本次提交快照**」行（事项/问题/条件取自服务端回传 `r.snapshot`），办理链接本就绑定 `r.snapshot`——输入框此后再改不影响已展示结果。

**回归**（`scripts/check-workflow-behavior.cjs` 场景②③）：成功→422：旧面板隐藏、办理链接移除、「本次未生成新结果」+错误信息；成功→网络异常：同一清理生效（共用逻辑）；成功后改动年份输入框，快照行仍显示「年级=2023」（绑定提交时快照）。

## 随单整理：TinyAgent 根 README 许可声明调查

补存固定 commit（`a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2`）根 README 原文（`tinyagent-snapshot/root-README.md`，14798 字节，SHA-256 `dab40facf4b68b2697a1a1a1e4e7cf8c2282a6ca9f326fd2ad91c5f3c22f7e6f`，上游 blob `9408f00c…`；经 GitHub contents API 按该 commit 取回，当日 raw 直连被重置，来源 URL 与返工单一致）。根 README 第 193—197 行 LICENSE 段声明 **CC BY-NC-SA 4.0**（署名-非商业性使用-相同方式共享）+「默认 CC 4.0，各子项目可另选协议」注记。

`tinyagent-assessment.md` 已修正事实：**GitHub license=null / 无独立 LICENSE ≠ 无任何许可声明**（撤回 rev1 的绝对推断）；对 `content/TinyAgent` 具体代码的适用范围如实保留疑问，不作任一绝对结论。**维持 reference 定位**（自研受限编排，不复制源码、不引依赖、快照仅留档）——该决策在任何许可情形下均保守不越界。

## 验证（聚焦，真实退出码）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_agent_workflow.py -q -p no:cacheprovider --basetemp .cache/t023r1b --tb=short -rs
# 20 passed（18 + 新增隔离回归 2），退出码 0

"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 9 HTML files passed syntax check.（退出码 0，workflow.html 修改后）

"D:/nodejs/node.exe" scripts/check-workflow-behavior.cjs
# check-workflow-behavior: 3 scenarios passed（vm stub 层级，非真实浏览器），退出码 0

./.venv/Scripts/python.exe scripts/trace-agent-run.py
# 6 runs，shared_planner_run_1/2 各 tool_calls=2（退出码 0）
```

按返工单未重跑全量/ASR/embedding/真实 DeepSeek；工厂装配未改，run_entry 无需补测。**无浏览器工具：修复 2/3 的交互证据为 vm stub 层级（check-workflow-behavior.cjs），不冒充浏览器验证，浏览器复验由 Astra 补做。**

## 未验证项

1. 浏览器真实交互复验（三条修复链）交 Astra。
2. 真实 Agent/真实 DeepSeek 规划仍未接入（planner_live_verified=false）。
3. TinyAgent 子目录代码的许可适用范围疑问如实保留，未作绝对结论。
