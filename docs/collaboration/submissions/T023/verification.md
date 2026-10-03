# T023 验证记录（submission_revision=2，responds_to=T023-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦返工三链 + 隔离回归；按返工单**未重跑全量/ASR/embedding/真实 DeepSeek**；零外部模型调用、无下载、无安装；未读取/打印密钥。rev1 记录归档于 `verification.rev1.md`。

## 1. 受限编排测试（20 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_agent_workflow.py -q -p no:cacheprovider --basetemp .cache/t023r1b --tb=short -rs
# 20 passed, 2 warnings in 0.97s
# 退出码：0
```

- 原 18 项（正常检索→缓考草稿对照直接 service、未知工具/非法参数先拒、重复停止、预算、条件不放宽、缺模板/缺输入回退、不自动保存/不调真实模型、Agent 默认关）保持全过。
- **新增 T023-R1 隔离回归 2 项**（`TestPlannerRunIsolation`）：
  - `test_same_instance_two_runs_both_execute`：同一 `ScriptedPlanner` 实例两次 `run_planner_loop` 均 `tool_calls_used=2`；第二次草稿 `procedure_id=proc-review-grade`、检索 `query=成绩复核`、快照 `filters=None`——结果属第二次运行。
  - `test_same_client_two_consecutive_api_runs`：同一 TestClient 两次 `POST /api/v1/agent/plan/run`（第一次 缓考/年级2023，第二次 成绩复核/不限），第二次照常执行且结果属第二次快照，第一次结果未被覆盖。

## 2. 页面因果链（vm stub 层级，非真实浏览器）

```bash
"D:/nodejs/node.exe" scripts/check-workflow-behavior.cjs
# check-workflow-behavior: 3 scenarios passed（vm stub 层级，非真实浏览器）
# 退出码：0
```

- 场景①（修复 2）年份三类：`2023` 提交且 `admission_year:2023`；空白提交且 `null`（=不限）；`abc`、`2023abc` **不发请求** + 「入学年份格式无效」+「未提交本次请求」（不截断、不静默转不限）。
- 场景②（修复 3）成功→422：旧依据/草稿隐藏、办理链接移除、「本次未生成新结果」+错误信息；改动输入框后展示仍绑定「本次提交快照」。
- 场景③ 网络异常与 422 共用清理：同样无残留入口。

**证据层级声明：以上为 vm stub 交互模拟，不是真实浏览器证据；浏览器真实交互复验由 Astra 补做，不以 stub 冒充。**

## 3. JS 语法

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 9 HTML files passed syntax check.（退出码 0，workflow.html 修复后复验）
```

## 4. 本地调用轨迹（真实运行，零外部调用）

```bash
./.venv/Scripts/python.exe scripts/trace-agent-run.py
# [normal_fixed_defer_draft] completed tool_calls=2
# [simulated_planner_happy] completed tool_calls=2
# [simulated_unknown_tool_and_bad_args] completed tool_calls=0
# [simulated_relax_rejected_then_no_progress] partial no_progress tool_calls=1
# [shared_planner_run_1_defer] completed tool_calls=2
# [shared_planner_run_2_grade_review] completed tool_calls=2
# 退出码：0 → call-trace.json
```

`shared_planner_run_1/2` 为**同一模拟规划器实例**连续两跑（T023-R1 修复 1 的运行级证据），各自独立执行、结果属各自快照。rev1 轨迹归档 `call-trace.rev1.json`。

## 5. 许可调查校正（随单）

根 README（commit `a5ae08d…`）经 contents API 取回并存 `tinyagent-snapshot/root-README.md`（14798 字节，SHA-256 `dab40facf4b68b2697a1a1a1e4e7cf8c2282a6ca9f326fd2ad91c5f3c22f7e6f`，上游 blob `9408f00ca2704ec7e1b75b0c1f920c68b65e17a5`）。第 193—197 行 LICENSE 段声明 CC BY-NC-SA 4.0。`tinyagent-assessment.md` 已修正事实并撤回「无任何许可声明」的绝对推断；对具体代码适用范围保留疑问；reference 定位不变。

## 6. 依赖

未改 requirements；未安装依赖；无需 pip check。

## 7. 未验证项

1. **浏览器真实交互复验**（三条修复链 + 主路径）交 Astra；stub 不冒充浏览器。
2. 真实 Agent/真实 DeepSeek 规划未接入、未验证（planner_live_verified=false）。
3. TinyAgent 子目录代码许可适用范围疑问如实保留，未作绝对结论。
4. 真实学校语料效果不在本轮范围。
