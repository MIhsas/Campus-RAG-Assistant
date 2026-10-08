# T036 真实题集与模板离线人工复核包 — 实施报告（report.md，submission_revision=2）

身份：task_id=T036、task_revision=v1+T036-R1、**submission_revision=2、responds_to=T036-R1、status=ready_for_review、external_model_calls=0、planner_live_verified=false、human_review_status=unreviewed**。仅修离线模板意见筛选与行为检查；gold/模板/历史/Astra 文件只读；未重跑无关 pytest/模型/实验/浏览器；零外部调用、无下载/安装、未 commit/push。**未代填任何人工结论。**

## T036-R1 修复（详见 [fix-report.md](fix-report.md)）

**意见筛选错误归属（P2）已修复**：`applyFilter()` 不再用全局短证据 ID/正文/跨度数字猜归属（`f1-s1` 等跨题重复曾致仅 q01 需修订却显示 20 题）——改为**只读本卡片实际拥有的意见行 select 当前值**（渲染时绑定 `_opinionSelects`），本卡片任一行匹配才展示；无意见行卡片（模板摘要卡）不计入匹配步骤；改意见即同步重刷筛选；意见 select 显式设初值（未复核）。

新增因果链回归（24 checks，含原有 15 项保持）：仅 q01/f1-s1 需修订→**只显示 q01**、同名 f1-s1 的 q02 不误入；切回未复核/全部符合本卡片状态；模板一条引用→只显示其所属步骤（共享块 d64f4351 末步不误入）。**Astra 探针原样核对 exit 0**（pass=true，expected/actual 均为 q01）。

## 输出（T036-v1 保留，构建 T036-v2）

| 项 | 路径 / SHA |
|---|---|
| 新包（**全部意见未复核**） | `step2_code/backend/.cache/human-review/T036-v2/`：review.html `7c82cf0d…`、pack.json `53dccd30…`、README.md `66bc59f4…` |
| 新模拟导出示例 | `T036-v2-simulated-export.json`（`55ce174b…`；record_title=模拟操作测试；仅 1 项需修订——非真实复核结论） |
| 保留 | `T036-v1/` + `T036-v1-simulated-export.json` 原样；非空目录拒覆盖规则保持 |

包内容（构建时 77 条引用逐字/跨度/哈希核对 exit 0）：24 题（20+4）×57 证据 + 13 步×20 引用；逐条 quote/原块全文/相邻块/页码定位/本地原件路径；OR/AND 语义与「无 gold≠无规定」注记。人工记录：四档意见初值全未复核、无预填签名日期；导出**新 JSON**（含输入 SHA），不写回 gold/模板/历史文件；不自动保存。

（非阻断）pack.json 本地原件为相对工作区路径——从 `F:\Collage Paper` 解析即可。

## 证据边界

意见筛选/导出 = **DOM/JS 桩**（24 项 + Astra 探针）；**无真实浏览器证据**（file:// 被安全策略拒绝，未绕过）——Astra 短清单见 [demo-notes.md](demo-notes.md)。人工语义审定仍为 **unreviewed**。

完成后停止，等待 Astra 验收。T037 未发布。
