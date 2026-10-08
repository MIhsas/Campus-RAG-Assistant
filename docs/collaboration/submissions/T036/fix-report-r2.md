# T036-R2 修复说明（fix-report-r2.md，submission_revision=3）

> 范围按 [T036-R2](../../reviews/T036-R2.md)：仅改离线 HTML 模板、行为桩、当前工具入口文档与提交说明。**构建器/gold/模板/产品页面/历史/Astra 文件未改**；未重复 pytest/模型/实验/浏览器；零外部调用、无下载/安装/commit/push。T036-v1/v2 包与模拟示例保留；revision 2 提交六件归档 `rev2/`（6/6 字节核验）。

## 修复 1（P1）：NodeList 无 some 导致意见筛选抛错

**问题**：`human-review-pack.html` 把 `card.querySelectorAll('.op-sel')` 原样存入 `_opinionSelects`，消费处直接 `sels.some(...)`——真实 DOM 的 querySelectorAll 返回 **NodeList**（可索引/迭代/forEach/item，**无 Array.some**），任何非空意见筛选都抛 `sels.some is not a function`（Astra `T036-nodelist-probe.cjs` 复现，exit 1）。

**最小修复**（消费处转换，保留已通过的卡片归属逻辑）：

```js
const sels = Array.from(c._opinionSelects || []);  // NodeList → 数组（可迭代/类数组均可）
ok = sels.some(function(s){ return s.value === op; });
```

「只读本卡片实际意见行、文字∩意见条件、改意见同步重刷、摘要卡不计入匹配」等 R1 行为全部保留未动。

## 修复 2：行为桩强化为 NodeList 形态（真实守护）

`check-review-pack.cjs` 新增 `NodeListLike`（**非 Array、可索引、可迭代、有 forEach/item、无 some/map/flatMap**），`querySelectorAll`（元素与 document 级）一律返回该形态；新增 4 项**形态断言**（非 Array+内部数组、无 Array 方法、有 forEach/item、可索引/迭代）。页面若退回 `sels.some` 直写，形态链与功能链都会失败——不是字符串断言。原 24 项（15 默认/导出 + 9 归属因果链）保持。

## 验证（实际命令/退出码）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `build-human-review-pack.py … --out-dir …/T036-v3` | 77 条引用逐字核对；24 题(20+4)/57/13/20 齐备；全部意见未复核 | 0 |
| `check-review-pack.cjs --pack-dir …/T036-v3 --write-sample …` | **28 checks passed**（15+9+4 形态断言；含「需修订筛选只显示 q01」等功能链） | 0 |
| `node docs/collaboration/reviews/T036-filter-probe.cjs --pack-dir …/T036-v3` | `{"expected_visible":["q01"],"actual_visible":["q01"],"pass":true}` | **0** |
| `node docs/collaboration/reviews/T036-nodelist-probe.cjs --pack-dir …/T036-v3` | `{"pass":true,"actual_visible":["q01"]}`（NodeList 形态探针，原样运行、未改标准） | **0** |

## 输出与入口同步

| 项 | 路径 / SHA |
|---|---|
| **当前包 T036-v3** | `.cache/human-review/T036-v3/`：review.html `aefcbdd2…`、pack.json `53dccd30…`、README.md `66bc59f4…` |
| 模拟示例 | `T036-v3-simulated-export.json`（`f11eab84…`，模拟操作测试） |
| 模板/桩 | `human-review-pack.html` `bb1b4001…`、`check-review-pack.cjs` `7f5c8057…` |
| 保留 | T036-v1/v2 包与旧模拟示例原样 |
| 入口同步 | `human-review-pending.md` §0 与 `demo-notes.md` 当前入口均指向 **T036-v3**（v1/v2 标注为历史备查） |

## 证据层级与未验证

DOM/JS 桩 + 两份 Astra 形态/功能探针；**无真实浏览器证据**（file:// 安全策略拒绝未绕过、未再尝试）。人工语义审定 **unreviewed**，未代填结论。
