# T036 真实题集与模板离线人工复核包 — 实施报告（report.md，submission_revision=3）

身份：task_id=T036、task_revision=v1+T036-R1+T036-R2、**submission_revision=3、responds_to=T036-R2、status=ready_for_review、external_model_calls=0、planner_live_verified=false、human_review_status=unreviewed**。仅改离线模板/行为桩/工具入口文档/提交说明；构建器、gold/模板/产品页面/历史/Astra 文件只读；未重复 pytest/模型/实验/浏览器；零外部调用、无下载/安装、未 commit/push。**未代填任何人工结论。**

## T036-R2 修复（详见 [fix-report-r2.md](fix-report-r2.md)）

**P1 NodeList 兼容**：意见筛选消费处改 `Array.from(c._opinionSelects || []).some(...)`——真实 DOM 的 querySelectorAll 返回 NodeList（无 Array.some），原直写 `.some` 会在任何非空意见筛选时抛错。**卡片归属逻辑（R1）保留**：只读本卡意见行、文字∩意见条件、改意见同步重刷、摘要卡不计入匹配。

**桩强化（真实守护）**：`querySelectorAll` 返回 **NodeListLike**（非 Array、可索引/迭代、有 forEach/item、**无 some/map/flatMap**）+ 4 项形态断言——页面若退回 `.some` 直写即失败（非字符串断言）。

**验证**：T036-v3 构建 exit 0（77 条引用逐字核对、24/57/13/20 齐备、全部意见未复核）；`check-review-pack.cjs` **28 checks passed**（15+9+4）exit 0；**两份 Astra 探针原样运行均 exit 0**（filter-probe 与 nodelist-probe：expected/actual=[q01]）。

## 输出与入口

| 项 | 路径 / SHA |
|---|---|
| **当前包 T036-v3** | `step2_code/backend/.cache/human-review/T036-v3/`：review.html `aefcbdd2…`、pack.json `53dccd30…`、README.md `66bc59f4…` |
| 模拟示例 | `T036-v3-simulated-export.json`（`f11eab84…`，模拟操作测试、仅 1 项需修订——非真实结论） |
| 保留 | T036-v1/v2 包与旧模拟示例原样；非空拒覆盖保持 |
| 入口同步 | `human-review-pending.md` §0 与 `demo-notes.md` 均指向 **T036-v3**（v1/v2 历史备查） |

包内容不变（pack.json 与 v1/v2 逐字节相同——构建器与输入未改）：24 题（20+4）×57 证据 + 13 步×20 引用，逐字 quote/原块全文/相邻块/定位/本地原件路径。

## 证据边界

筛选/导出=DOM/JS 桩 + Astra 形态/功能探针；**无真实浏览器证据**（file:// 安全策略拒绝，未绕过）。人工语义审定 **unreviewed**。

完成后停止，等待 Astra 验收。T037 未发布。
