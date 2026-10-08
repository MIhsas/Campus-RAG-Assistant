# T036 验证记录（verification.md，submission_revision=3）

> T036-R2 轮仅跑：新包构建、强化后的筛选/导出行为检查、两份 Astra 探针。**未重复 pytest/模型/实验/浏览器**；零外部调用。命令真实执行、退出码实测。

## 1. 新包构建（T036-v3）

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\build-human-review-pack.py' --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1\manifest.json' --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1' --questions 'F:\Collage Paper\data\evaluations\sicau-rag-pilot-eval-v1\questions.json' --procedures 'F:\Collage Paper\data\procedures\sicau-transfer-2026-v1\procedures.json' --out-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v3'
```

| 结果 | 退出码 |
|---|---|
| `核对引用: 77 条（57+20）`；`CHECK OK：24 题(20+4)/57 证据/13 步/20 引用齐备`；pack.json 与 v1/v2 逐字节相同（构建器/输入未改）；全部意见未复核 | **0** |

## 2. 强化筛选/导出行为检查（DOM/JS 桩，NodeList 形态）

```
node step2_code/backend/scripts/check-review-pack.cjs --pack-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v3' --write-sample '…T036-v3-simulated-export.json'
→ check-review-pack: 28 checks passed   (exit 0)
```

| 组 | 断言 | 结果 |
|---|---|---|
| 原 15 项（保持） | 默认 114/114 未复核、单项导出语义、输入 SHA 持久、离线（localStorage/fetch 触达即失败） | OK |
| 归属因果链 9 项（保持） | 仅 q01/f1-s1 需修订→只显示 q01；q02（同名 f1-s1）不误入；未复核/空筛选符合本卡；模板引用不误带其他步骤（共享块末步、摘要卡）；改意见同步重刷 | OK |
| **NodeList 形态 4 项（新）** | `.op-sel` 查询结果非 Array、**无 some/map/flatMap**、有 forEach/item、可索引/迭代——页面 `Array.from(...).some` 在此形态下正常工作；若退回 `.some` 直写即失败 | OK |

## 3. 两份 Astra 探针（原样运行，未改探针/标准）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node docs/collaboration/reviews/T036-filter-probe.cjs --pack-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v3'` | `{"expected_visible":["q01"],"actual_visible":["q01"],"pass":true}` | **0** |
| `node docs/collaboration/reviews/T036-nodelist-probe.cjs --pack-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v3'` | `{"pass":true,"actual_visible":["q01"]}`（NodeList 形态 DOM 桩） | **0** |

## 4. 输出与入口

| 项 | SHA / 说明 |
|---|---|
| T036-v3/review.html | `aefcbdd20f2a21f3…` |
| T036-v3/pack.json | `53dccd30c9e9d844…`（与 v1/v2 相同——数据未变） |
| T036-v3/README.md | `66bc59f40e6610de…` |
| T036-v3-simulated-export.json | `f11eab84876db524…`（模拟操作测试） |
| human-review-pack.html | `bb1b400193f961d1…`（Array.from 化消费） |
| check-review-pack.cjs | `7f5c80576e7c2d8d…`（NodeListLike 形态桩） |
| 入口同步 | human-review-pending.md §0、demo-notes.md 均指向 T036-v3（v1/v2 历史备查） |
| 归档 | revision 2 提交六件 → `rev2/`（6/6 字节一致）；T036-v1/v2 包与旧示例保留 |

## 5. 未验证/证据边界

- **无真实浏览器证据**（file:// 安全策略拒绝，未绕过/未再尝试）；形态/功能证据=DOM/JS 桩 + 两份 Astra 探针。
- 未重复：pytest、模型、检索/评测实验、ASR/Agent、全量测试。
- **人工语义审定仍为 unreviewed**（未代填结论）；构建器/gold/模板/历史/Astra 文件未改。
