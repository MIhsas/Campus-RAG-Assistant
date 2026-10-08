# T036 验证记录（verification.md，submission_revision=2）

> T036-R1 轮仅跑：新包构建、意见筛选/导出行为检查、Astra 探针原样核对。**未重复 4 项 pytest、全量/模型/实验/浏览器**；零外部调用。命令真实执行、退出码实测。

## 1. 新包构建（T036-v2）

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\build-human-review-pack.py' --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1\manifest.json' --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1' --questions 'F:\Collage Paper\data\evaluations\sicau-rag-pilot-eval-v1\questions.json' --procedures 'F:\Collage Paper\data\procedures\sicau-transfer-2026-v1\procedures.json' --out-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v2'
```

| 结果 | 退出码 |
|---|---|
| `核对引用: 77 条（57+20）`；`CHECK OK：24 题(20+4)/57 证据/13 步/20 引用齐备`；输出 review.html/pack.json/README.md | **0** |

新包全部意见初值「未复核」（pack.json `human_review_status=unreviewed`）；测试意见仅存独立模拟示例。

## 2. 意见筛选/导出行为检查（DOM/JS 桩，非浏览器）

```
node step2_code/backend/scripts/check-review-pack.cjs --pack-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v2' --write-sample '…T036-v2-simulated-export.json'
→ check-review-pack: 24 checks passed   (exit 0)
```

| 组 | 断言 | 结果 |
|---|---|---|
| 原有 15 项（保留） | 默认 114/114 未复核、reviewer/标题空、导出 record_type/输入 SHA、模拟单项变更恰 1 项其余 113 未复核、localStorage/fetch 触达即失败 | OK |
| **筛选因果链（新）** | 仅 q01/f1-s1 需修订→「需修订」筛选**只显示 q01**；q02（同名 f1-s1）不误入 | OK |
| | 「未复核」→24 卡片（每卡实际拥有未复核行）；空筛选=全部 | OK |
| | 模板一条引用需修订→只显示其所属步骤 t1；摘要卡（无意见行）不计入匹配；共享块 d64f4351 的末步 t13 不误入 | OK |
| | 改回未复核**即同步重刷**（需修订筛选下模板 0 匹配） | OK |

实现要点：意见条件只读 `card._opinionSelects`（本卡实际意见行 select 当前值），不扫全局 state、不用短 ID/正文/跨度数字猜归属；意见 select 显式设初值（与真实 select 选中语义一致）。

## 3. Astra 探针原样核对（未修改探针/通过标准）

```
node docs/collaboration/reviews/T036-filter-probe.cjs --pack-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v2'
→ {"layer":"DOM stub, not browser","changed":"q/q01/f1-s1","expected_visible":["q01"],"actual_visible":["q01"],"pass":true}   (exit 0)
```

## 4. 保留与输出 SHA

| 项 | SHA / 说明 |
|---|---|
| T036-v2/review.html | `7c82cf0daf832ea0…` |
| T036-v2/pack.json | `53dccd30c9e9d844…`（与 v1 数据一致——构建器未改、输入未变） |
| T036-v2/README.md | `66bc59f40e6610de…` |
| T036-v2-simulated-export.json | `55ce174b1fef403e…`（模拟操作测试） |
| scripts/human-review-pack.html | `1b760de8b2959764…` |
| scripts/check-review-pack.cjs | `0bcd3921912e6ab9…` |
| T036-v1 包 + 旧模拟示例 | **原样保留**；非空拒覆盖规则保持（重跑 v2 时先用全新空目录） |
| revision 1 提交五件 | 归档 `rev1/`，5/5 字节一致 |

（非阻断）pack.json 本地原件为相对工作区路径，从 `F:\Collage Paper` 解析即可。

## 5. 未验证/证据边界

- **无真实浏览器证据**（本轮 file:// 被浏览器安全策略拒绝，未绕过/未用替代浏览器）；筛选/导出为 DOM/JS 桩层级。
- 未重复：4 项 pytest、全量测试、模型、检索/评测实验、ASR/Agent。
- **人工语义审定仍为 unreviewed**（未代填结论）；gold/模板/历史产物/Astra 文件未改。
