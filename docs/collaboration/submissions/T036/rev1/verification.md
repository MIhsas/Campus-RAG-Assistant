# T036 验证记录（verification.md，submission_revision=1）

> 命令在 Windows（Git Bash）下真实执行；退出码实测。范围限任务书聚焦验证；**未加载模型、未重跑实验/浏览器/ASR/Agent/无关全量**；零外部调用。

## 1. 构建命令与完整性（实际命令）

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\build-human-review-pack.py' --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1\manifest.json' --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1' --questions 'F:\Collage Paper\data\evaluations\sicau-rag-pilot-eval-v1\questions.json' --procedures 'F:\Collage Paper\data\procedures\sicau-transfer-2026-v1\procedures.json' --out-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v1'
```

| 结果 | 退出码 |
|---|---|
| `核对引用: 77 条（gold 证据 57 + 模板引用 20）`；`CHECK OK: 77 条引用逐字/跨度/哈希核对通过；24 题(20+4)/57 证据/13 步/20 引用齐备`；输出 review.html/pack.json/README.md | **0** |

- 构建前逐条核对（新解析）：文档 SHA、块存在、跨度合法、quote==块切片逐字一致；**失败即非零退出且不输出半成品**（见 §3）。
- pack.json 记录输入 SHA/版本（questions `5fde70a3…` v1.3、manifest `34e182f1…`、procedures `78f1c1d9…` v1.2）、模型辅助声明、人工未复核；逐题保留原 query/条件/事实组/理由/已查范围/修订记录；逐步保留 detail/未说明项/引用；每条含原块全文、相邻块、定位（未知如实）、本地原件路径。长 ID（document_id 64 位）未截断。

## 2. 聚焦业务检查

| 检查 | 结果 | 退出码 |
|---|---|---|
| **全条目/引文完整性**：`pytest tests/test_human_review_pack.py` | **4 passed**（计数 24/20+4/57/13/20/77；77 条 quote==块切片、身份字段齐；HTML 离线+默认未复核） | 0 |
| **单项意见导出不改其他项/输入身份**：`node scripts/check-review-pack.cjs --write-sample …`（DOM/JS 桩，**非真实浏览器**） | **15 checks passed**：默认 114/114 意见=未复核、reviewer/标题空、无测试数据；模拟 1 项「需修订+意见」→导出 JSON 恰 1 项变更、其余 113 项未复核、tally 一致、输入 SHA 不变、record_title 标「模拟操作测试」；localStorage/fetch 一旦使用即抛错（全程未触达=离线/不自动保存） | 0 |

## 3. 护栏检查

| 检查 | 结果 | 退出码 |
|---|---|---|
| 输出目录非空拒绝覆盖（重跑同目录） | `FAIL: 输出目录非空，拒绝覆盖已有复核包` | **1** |
| 隔离坏引用（副本篡改 quote） | `FAIL: …quote 与块切片不一致…`、`CHECK FAILED`；**不写任何包**；原模板/questions SHA 不变（`78f1c1d9…`/`5fde70a3…`） | **1** |

## 4. 输入与历史产物不变（前后核对）

| 文件 | 前后 SHA（均为） | 结论 |
|---|---|---|
| T030 questions.json | `5fde70a332744b64…` | 未变 |
| 真实包 manifest.json | `34e182f18178c8a8…` | 未变 |
| 模板 procedures.json | `78f1c1d9f839c41d…` | 未变 |
| T031 experiment.json | `57b22f93bd1420fa…` | 未变 |
| T034 experiment.json | `cef9f162f1eb164a…` | 未变 |

未重新计算任何评测分数；gold/模板/解析器/检索评分/历史产物未改。

## 5. 文档顺带修正核对

| 项 | 结果 |
|---|---|
| defense-script 第 3→4 段衔接（2023 对照后切回 2026→重新整理依据→确认入口→点击） | 已写入第 4 节步骤 0；子预算 30+40+40+20=**130 秒**（该节原预算不变） |
| 全脚本秒数合计 | 30+20+140+120+130+50+50+20 = **560 ≤ 600**（重算一致） |
| human-review-pending.md 工具入口 | §0 已补（打开路径/数据/用法/边界/模拟示例） |

## 6. 未验证/证据边界（如实）

- **真实浏览器未运行**：导出/浏览行为为 DOM/JS 桩证据（`check-review-pack.cjs`）；Astra 可直接打开 `review.html` 复核（短清单见 demo-notes.md）。
- **模拟导出示例非真实复核结论**（record_title 已标「模拟操作测试」）；默认复核包不含任何测试选择。
- 人工语义审定（24 题 gold、模板现行性）**仍未复核**（human_review_status=unreviewed，不代签）。
- 未跑：检索/评测实验、向量编码、ASR/Agent、全量 pytest（仅新增聚焦 4 项与桩 15 项）。
