# T036-R1 修复说明（fix-report.md，submission_revision=2）

> 范围按 [T036-R1](../../reviews/T036-R1.md)：仅修离线 HTML 模板的意见筛选、行为检查与 T036 提交说明。gold/模板/历史产物/Astra 文件未改；未重跑无关 pytest/模型/实验/浏览器；零外部调用、无下载/安装/commit/push。**T036-v1 包与旧模拟示例原样保留**；新包 `T036-v2/` 重新构建（全部意见未复核）；revision 1 提交五件原字节归档 `rev1/`（5/5 核验）。

## 修复：意见筛选错误归属（P2）

**问题**（Astra 因果链复现）：`human-review-pack.html` 的 `applyFilter()` 遍历全局 state，用 `k.split('/').slice(-1)[0]`（短证据 ID / 引用跨度数字）是否出现在卡片正文猜归属——`f1-s1` 等 ID 在多题重复、跨度数字不唯一。仅 q01/f1-s1 设「需修订」时，筛选错误放行 q01—q20 全部 20 张可答题卡片。

**修复**（简单实现，按返工单方案）：

1. 每个意见行的 select 标记 `op-sel` 类；卡片渲染完成时将**本卡片实际拥有的意见行 select 列表**绑定为 `card._opinionSelects`。
2. `applyFilter()` 的意见条件**只读这些 select 的当前值**（`sels.some(s => s.value === op)`）——不扫描全局 state，不用短 ID/正文/跨度数字猜归属。
3. 语义：**本卡片任一意见行匹配才展示**（题目本身/证据/步骤/引用均如此）；文字条件与意见条件求交；空意见筛选=全部。**无意见行的卡片（模板摘要卡）不匹配任何意见筛选**（仅无意见筛选时作为上下文展示，不计入匹配步骤）。
4. **修改意见即同步重刷筛选**（select change 处理器调用 `applyFilter()`），避免残留旧显示。
5. 附带一致性修正：意见 select 显式 `sel.value = st.opinion`（与真实 select 选中语义一致，初值=未复核）。

## 新增因果链回归（check-review-pack.cjs，含 `--pack-dir`）

| 断言 | 结果 |
|---|---|
| 仅 q01/f1-s1 需修订 → 按「需修订」筛选**只显示 q01** | OK（got q01） |
| 同名 f1-s1 的 q02 不误入（无短 ID 误归属） | OK |
| 切回「未复核」→ 24 卡片（每卡实际拥有未复核行）；空筛选=全部 | OK |
| 模板一条引用设需修订 → **只显示其所属步骤**；摘要卡（无意见行）不计入；共享块 d64f4351 的末步不误入 | OK |
| 改回未复核即同步重刷（需修订筛选下 0 匹配） | OK |
| 原有 15 项（默认 114/114 未复核、单项导出语义、输入 SHA、离线断言）**保持** | OK（共 24 checks passed，exit 0） |

**Astra 探针原样核对**：`node docs/collaboration/reviews/T036-filter-probe.cjs --pack-dir …/T036-v2` → `{"expected_visible":["q01"],"actual_visible":["q01"],"pass":true}`，**exit 0**（未修改探针与通过标准）。

## 新输出与保留

| 项 | 路径 / SHA |
|---|---|
| **新包（全部未复核）** | `.cache/human-review/T036-v2/`：review.html `7c82cf0d…`、pack.json `53dccd30…`、README.md `66bc59f4…` |
| 新模拟导出示例 | `.cache/human-review/T036-v2-simulated-export.json`（`55ce174b…`，record_title=模拟操作测试，仅 1 项需修订） |
| 保留 | `T036-v1/` 与 `T036-v1-simulated-export.json` 原样；非空目录拒覆盖规则保持 |
| 修改文件 | `scripts/human-review-pack.html`（`1b760de8…`）、`scripts/check-review-pack.cjs`（`0bcd3921…`）；构建器未改 |

（非阻断说明）pack.json 中「本地原件」为相对工作区路径——从 `F:\Collage Paper` 解析即可打开原件；本轮未改构建器。

## 证据层级

意见筛选/导出行为 = **DOM/JS 桩**（check-review-pack.cjs 24 项 + Astra 探针）；本轮**无真实浏览器证据**（file:// 被浏览器安全策略拒绝，未绕过）。人工语义审定仍为 **unreviewed**，未代填任何结论。
