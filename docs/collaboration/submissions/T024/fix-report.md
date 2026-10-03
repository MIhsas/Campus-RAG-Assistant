# T024-R1 定向返工 — 修复报告（fix-report）

身份：task_id=T024、task_revision=v1、**submission_revision=2、responds_to=T024-R1**、status=ready_for_review、planner_live_verified=false、external_model_calls=0。rev1 四件及轨迹已归档 `*.rev1.*` 保留（live-smoke-plan.md 未变，不归档）。本轮仅改 workflow 完成判定、结果区模式标注及直接相关测试/说明；未改探针（`T024-R1-probe.py` 为 Astra 文件，通过标准不动）；零外部模型调用、无下载、无安装。

## 修复 1（P1）：finish 未检查应完成的产物 → 服务端产物判定

**问题**（Astra 探针 + 真实浏览器复现）：`had_failures` 只看失败不看产物；模型直接 finish 或只检索后 finish 均被标 `completed`；页面显示 mock 的「全部办理工作已完成」但没有草稿。

**修复**（`agent/workflow.py`）：新增 `_finish_verdict()`——**完成由服务端按必要产物判定**（本入口任务=按用户选定事项查依据、整理办理草稿 → 必要产物为 `search` + `draft`），模型 summary 不决定成功：

| 情形 | status | 文案（服务端） |
|---|---|---|
| 缺产物、有部分结果 | `partial` | 「任务未完成：缺少××。已保留××结果；未补调用、未重试。」+ 完成定义注 |
| 缺产物、无任何结果 | `stopped` | 「任务未完成：缺少××，本次无任何结果。未补调用、未重试。」+ 完成定义注 |
| 产物齐但期间有失败/被拒 | `partial` | 「必要产物已生成，但期间有失败/被拒动作，未全部完成。」 |
| 产物齐且无失败 | `completed` | 「查找依据与办理草稿均已生成。」+ saveable 注 + 完成定义注 |

- **缺失步骤列出**（查找依据/整理草稿）；**保留已完成结果**；**不补调用、不重试**（探针实测 requests 数与调用数不变）。
- **模型结束语不作主结论**：从 message 移出，写入 `planner_summary` 字段并在事件中标注「仅记录，不作结论」。
- **资料不足草稿**：`saveable=false` 时 message 明确「草稿 saveable=false（依据不足或需更新，暂不可保存）」；所有完成文案固定注明「完成仅指生成可核对结果，不代表学校审批、办事已办妥或待办已保存」。
- **固定流程同一原则**：流程尾部改用 `_finish_verdict`——搜索失败+草稿成功（或反之）标 `partial` 并列缺失步骤，不再无提示 `completed`。正常 search→draft→finish 仍 `completed`。

**回归**（聚焦三类 + 边界一项）：
- `TestCompletionVerdict`（test_deepseek_planner.py 新增 4 项）：直接 finish → `stopped`、无产物、message 无「全部办理工作已完成」、`planner_summary` 仅记录、请求恰 1；search→finish → `partial`、检索结果保留、message 含「缺少整理草稿/未补调用」、请求恰 2；完整链 → `completed` + 服务端完成定义文案；saveable=false 草稿显式标注。
- `TestFixedWorkflowVerdict`（test_agent_workflow.py 新增 2 项）：搜索异常+草稿成功 → `partial` 列缺失；干净链 → `completed` + 服务端文案。
- **Astra 独立探针原样运行**：`finish_without_tools` → stopped、`search_then_finish` → partial、draft 均 null、`exit 0`（通过标准未改）。

## 修复 2（P2）：DeepSeek 结果被误标「模拟规划」→ 按本次响应区分模式

**问题**：plan 按钮一律传 `isSim=true` 给渲染，DeepSeek 成功/partial 结果附加「模拟规划，非DeepSeek实时规划」，与状态区模式冲突。

**修复**（`static/workflow.html`）：渲染改为**按本次响应 `workflow_kind` 标注**——`fixed` → 「固定流程…非大模型 Agent」；`simulated_planner` → 「模拟规划，非DeepSeek实时规划」；`deepseek_planner` → 「DeepSeek 规划（…）」+「已配置 ≠ 已联调验证（planner_live_verified=false）」。mock 标识不再靠错误产品文案，而来自服务端 `workflow_label`/模型身份的**显式标注**（mock 注入时模型名自带「模拟，非真实 DeepSeek」）。T023-R1 快照、年份拦截、失败清空、手动保存边界全部保持。

**回归**（`check-workflow-behavior.cjs`，**stub 层级非真实浏览器**）：场景④ deepseek 形状 partial 结果——结果区含「DeepSeek 规划」「已配置 ≠ 已联调验证」且**不含「模拟规划」**；场景⑤（新增）对照——模拟响应标模拟不标 DeepSeek，固定响应标「固定流程/非大模型 Agent」且不带任何规划模式字样。**重点断言在结果区（run-label），不只按钮。**

## 非阻断整理（随单校正）

- `api/agent.py` 模块说明：「No remote planning exists」→ 校正为远程规划适配器已存在、须显式开启、按响应标注模式、未联调验证。
- `workflow.py` CANCEL_NOTE：「规划调用均为本地计算」→ 校正为「工具为本地同步计算，规划调用可能是远程 HTTP；均不支持中途取消，停止只终止后续调度」。
- 预算计数保持已测试口径，未新增计费审计系统。

## 验证（聚焦，真实退出码）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_deepseek_planner.py tests/test_agent_workflow.py -q -p no:cacheprovider --basetemp .cache/t024r1 --tb=short -rs
# 45 passed（39+6 新增），退出码 0

./.venv/Scripts/python.exe "F:/Collage Paper/docs/collaboration/reviews/T024-R1-probe.py"
# finish_without_tools → stopped；search_then_finish → partial；draft 均 null；退出码 0（探针未改）

"D:/nodejs/node.exe" scripts/check-workflow-behavior.cjs
# 5 scenarios passed（vm stub 层级，非真实浏览器），退出码 0

"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 9 HTML files passed syntax check.，退出码 0

./.venv/Scripts/python.exe scripts/trace-agent-planner.py
# 8 runs：direct_finish/reject_swap → stopped(incomplete_artifacts)；其余按新判定；退出码 0
```

按返工单未重跑全量/ASR/embedding/问答 provider（未改共享代码 qa/deepseek.py）。**无浏览器能力：结果区模式断言为 vm stub 层级，不冒充浏览器验证，交 Astra 补验。**

## 未验证项

1. 浏览器真实交互（结果区三模式标注、缺草稿不显「完成」）交 Astra。
2. 真实 DeepSeek 规划仍未联调验证（planner_live_verified=false）。
