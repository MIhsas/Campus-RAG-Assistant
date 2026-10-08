# T035 验证记录（verification.md，submission_revision=1）

> 本轮只做文档链接/路径、API/启动参数与源码/--help 对照、机器指标与表格一致性核对，及主流程抽查（≤3 处实现 + 附带一致性断言）；未重跑浏览器/模型/实验/全量测试。命令在 Windows（Git Bash）下真实执行，退出码实测。

## 1. 归档核验

| 项 | 结果 |
|---|---|
| `docs/delivery/archive-t028-delivery/` 六件 vs 原位六件（归档前） | **6/6 SHA-256 字节一致** |
| 旧 `docs/delivery/rev1/` | 保留未动（只读） |

## 2. 文档链接与路径

| 检查 | 结果 | 退出码 |
|---|---|---|
| 交付包 7 个 md 的相对链接解析 | **10/10 存在** | 0 |
| 新文档内联路径（`data/…`/`docs/collaboration/submissions/…`） | 归一化为完整路径后全部可解析（简写已修正） | 0 |

## 3. API / 启动参数与源码、--help 对照

| 命令/检查 | 结果 | 退出码 |
|---|---|---|
| `python scripts/serve-corpus.py --help` | `--manifest --corpus-root --port --embedding-model-dir --asr-model-dir --generator {off,deepseek} --planner {off,deepseek} --procedures --self-check` ——与 windows-runbook §2 记载逐项一致 | 0 |
| `python -m campus_assistant.corpus.chunk --help` | 含 `--max-chars`、`--overlap-chars`（0=默认无重叠）——与手册/实验参数一致 | 0 |
| 源码字段抽查（read-only grep） | `api/search.py`：`document_id`/422/`/documents`；`api/procedures.py`：`related_keywords`+`source_document_ids`；`retrieval/source_selection.py`：`intersect_allowed`/`build_source_selection` ——与文档描述一致 | 0 |

## 4. 机器指标与文档表格一致性

| 检查 | 结果 | 退出码 |
|---|---|---|
| 表 6-2/E1（T030 v1.3）：BM25 0.725/0.75/0.6、Dense 0.7/0.7/**0.44333333333333336**、Hybrid 0.7/0.7/**0.5416666666666667** | 与 `data/evaluations/sicau-rag-pilot-eval-v1/results/*.json` summary 逐值一致 | 0 |
| 表 6-3/E2（T031）：selection MRR **0.5033333333333333 / 0.5483333333333333 / 0.5**；baseline 0.35/0.23333333333333334/0.2833333333333333 | 与 `sicau-rag-source-selection-v1/experiment.json` aggregates 逐值一致 | 0 |
| 表 6-4/E3（T034）：candidate BM25 MRR **0.5958333333333333**、Dense R **0.675**/MRR **0.4666666666666667**、Hybrid MRR **0.5833333333333333** | 与 `sicau-rag-overlap-v1/experiment.json` aggregates 逐值一致（机器交叉断言 exit 0） | 0 |
| 表 6-1（T027 历史值 0.950/0.900/0.705833/0.891667） | 与 archive-t028 evidence-matrix 记录一致（历史原值保留） | — |

## 5. 主流程抽查（3 处实现，read-only）

| 实现 | 核对点 | 结果 |
|---|---|---|
| `retrieval/source_selection.py` | 交集先准入（`intersect_allowed`）、摘要计数（`build_source_selection`）与文档描述一致 | OK |
| `static/ask.html` | 目录驱动入口（`relatedCandidates` 关键词∩`source_document_ids`）、快照链接（`proceduresLinkFor` 不含 document_id） | OK |
| `corpus/chunk.py` | `overlap_chars` 可选、默认 `block_window_v1` 兼容、`STRATEGY_OVERLAP` 身份 | OK（tests/test_chunk_overlap+test_corpus_chunk 63 项既有记录佐证，本轮未重跑） |

## 6. 历史证据引用（未重跑）

- 浏览器主路径：T031-R2（双向条件恢复、未知文件 422）、T033-R1（2026 入口/2023 不推荐、预选不自动草稿、历史快照）——见 `docs/collaboration/reviews/`。
- 实验机器值：T030-R1/R2/R3、T031、T034-R1（Astra 独立重算 144 分支一致）。

## 7. 未验证项（如实）

- 本轮未运行：浏览器、模型编码、实验脚本、全量 pytest、UI/ASR/Agent。
- 人工审定（24 题 gold、模板语义/现行性）仍为**未复核**（见 human-review-pending.md，不代签）。
- defense-script 中标 `[本轮未实跑]` 的步骤未现场执行，不称已验证。
