# T025 逐条结果核对表（模板）

> 本表由 `scripts/live-smoke-planner.py` 在每次运行后**按实际动作自动生成**（结果 JSON 的 `checklist` 字段与 stderr 摘要）。
> **不预写通过结论**：dry-run 的「实测」列一律为「待实际运行核对」（pass=null）；真实运行时逐条填实测值。
> 完成口径（T024-R1）：完成=生成可核对结果，不代表学校审批、办事已办妥或待办已保存。

固定输入：查找缓考依据并整理办理草稿 / proc-apply-defer / admission_year=2023（T025 任务固定合成题，编译进脚本，不接受改写）。

| # | 核对项 | 预期 | 实测（运行时生成） | 通过 |
|---|---|---|---|---|
| 1 | 是否实际搜索 | search_policy 至少一次成功并返回命中 | 待实际运行核对 | — |
| 2 | 草稿是否存在且事项/条件正确 | 草稿存在、procedure_id=proc-apply-defer、条件=年级 2023 | 待实际运行核对 | — |
| 3 | 引用是否与直接 service 相同 | 草稿引用与本地 build_draft 直接结果逐条一致 | 待实际运行核对 | — |
| 4 | 是否需人工核实 | saveable=false/待核实项如实标注（不隐藏） | 待实际运行核对 | — |
| 5 | 是否有失败/提前 finish | 无失败动作、无缺产物提前结束（status=completed） | 待实际运行核对 | — |
| 6 | 是否零自动保存 | 零自动保存（不写待办/localStorage/任何存储） | 只写出 --out 运行记录 | ✓ |

配套记录（同一结果 JSON）：输入快照、语料/模板哈希与合成标记、实际配置（不含密钥）、preflight 各行、run 状态与 stop_reason、服务端结论文案、实际动作与观察摘要、工具结果/引用、逐轮 provider 审计（缺失 null）、发送处 HTTP 计数（`http_observed_at_send`，与 `planner_http_attempts` 交叉核对）。

退出码约定：dry-run 成功=0；live/mock 仅当 status=completed 且核对表无失败项且 HTTP 计数一致时=0；前置/技术失败或未达 completed=1；argparse 用法错误=2。
