# T011 适用条件筛选与检索收尾 — 实施报告

## 概述

一次交付“选择校区、学生类型、入学年份、查询日期 → 三模式检索 → 查看适用理由 → 原文核对”的可演示流程，并完成 T010-R1 列出的五项收尾。筛选在候选截断前做文档准入，三模式共用同一准入集合；暂不自动判断学生资格，不生成政策答案。语料仍为合成夹具，不代表四川农业大学真实政策。

身份：task_id=T011、task_revision=v1、submission_revision=1、status=ready_for_review。

## 1. 筛选语义（后端）

### 新增 `retrieval/filters.py`

- `compute_allowed_document_ids(documents, filters)`：返回准入 document_id 集合与排除原因计数。**未提供任何筛选时返回 None（不限制），与空集合（无一通过）语义区分。**
- 口径：统计对象为文档；每份被排除文档只计入首个命中原因，优先级 `scope_unknown`（被筛维度为空数组=未知）→ `scope_mismatch` → `date_unknown_from`（effective_from=null）→ `not_yet_effective` → `expired`；各原因计数互斥。口径文本随响应 `filter_summary.counting_rules` 返回。
- 日期筛选两端包含（effective_from ≤ 查询日 ≤ effective_to）；`effective_to=null` 不证明永久有效，日期筛选下结果注明“未标注截止”；`published_at` 不代替 `effective_from`。同一家族多版本不去重、不猜“最新版”。
- `extract_filter_options(documents)`：从已解析语料提取去重的校区/类型/年级选项。

### 检索器（`bm25.py`、`dense.py`）

- `search(..., allowed_document_ids=None|set)`：准入在打分候选中先应用，再取 Top-K（不是先截全库 Top-K 再删项）。BM25 的 N/df/IDF 仍为全库统计；Dense 准入后排名从 1 重排；Hybrid 各路（top 20）都从准入集合取候选、从 1 排名后 RRF（`api/search.py` 调用侧传入同一准入集合）。空准入集合直接返回空结果，不回退到不符合条件的文档。无筛选时行为与 T010 完全一致。

### API（`api/search.py`）

- POST `/api/v1/search` 新增可选 `filters`：`campus`、`student_type`（单值字符串）、`admission_year`（整数）、`as_of_date`（YYYY-MM-DD，真实日历校验）；`extra=forbid`，未填不限制。
- 响应回显规范化 `filters`，新增 `filter_summary`（active、document_total、allowed_count、excluded_counts、counting_rules、notes）。
- status 新增 `filter_options`、`embedding_model_revision`、`embedding_max_seq_length`、`truncated_chunk_count`、`embedding_error`；`embedding_model` 改为简洁模型 ID（目录名），不再返回本机绝对路径。

## 2. 前台闭环（`static/search.html`）

- 四项筛选控件（校区/类型/年级下拉 + 查询日期输入）与“清除条件”。下拉选项来自 status 的 `filter_options`，均带“不限”；日期默认不限制。
- 提交后展示该次查询实际采用的条件与结果数量（使用响应回显，之后编辑控件不改写条件说明）；无结果区分“没有满足所选条件的资料”与“满足条件的资料中没有检索命中”，两种空态都提供“清除条件”操作；失败重试沿用上次 mode/query/filters 快照。
- 结果保留原文跳转、适用范围与日期信息；`effective_to` 为空显示“未标注截止”。顶部文案改为“证据检索结果，不是自动生成的政策答案，也不是资格认证。”
- 语义/混合结果以实际 hits 为准，不再被 BM25 `query_tokens` 为空提前拦截；仅关键词模式无命中且无有效搜索词时保留提示。维持静态页面，无框架迁移。

## 3. T010-R1 五项收尾

1. **行为脚本 stub**：补齐 mode-selector、筛选控件与 classList/querySelectorAll/closest 等 stub 能力，实跑 12 个场景通过；保留旧断言（空白取消、A→B 竞态、三类失败重试），新增筛选与 mode/query/filters 重试快照、条件快照、清除条件、两种空态、语义按 hits 展示。
2. **仅本地加载**：`EmbeddingService` 只接受实际本地目录（Hub ID/不存在目录拒绝，中文原因，不含路径），`SentenceTransformer(..., local_files_only=True)` 显式约束（非全局离线变量）；加载失败保留 BM25/预览并在 status 给出 `embedding_error`（已实测：`模型目录不存在：not-a-model-dir`，bm25 仍 200）。
3. **token 上限与身份**：max_seq_length=512 保留不动；`count_truncated` 统计编码时超限块数（长块仅部分参与向量计算，原文与 chunk 从不被截短覆盖，已实测计数），status/评测输出均带 `truncated_chunk_count` 与说明。revision 从下载元数据核实为 `7999e1d3359715c523056ef9478215996d62a620`（各 `.metadata` 首行一致且与 trees 缓存文件名相符）；无元数据时回退 `unknown`，不猜测。`download-embedding-model.py` 改为只拉 safetensors 一种权重格式（`ignore_patterns` 跳过 `*.bin` 等）；本地已有两份权重未删除、未重下载。
4. **完整评测 CLI**：三条完整命令与原始 JSON 输出见 `eval-bm25.json` / `eval-dense.json` / `eval-hybrid.json` 与 verification.md。8 题 gold 未改；默认无筛选，与 T010 可比。新筛选用独立夹具 `examples/filter-demo/` + API 演示，不改旧评测 schema。
5. **语义文案**：见上文前台闭环（按实际 hits 展示、顶部文案修正）。

## 4. 有限验证摘要

- 新增 `tests/test_search_filters.py` 30 项（筛选语义、三模式准入、先截断漏项、API 回显/空条件/422），手工向量，不在单测下载模型：全过。
- 一次全量回归：404 passed、1 skipped（既有 Windows 链接权限跳过）、2 warnings。pip check 无破损。JS 语法与行为脚本通过。
- 三模式评测 CLI 各一次（原始输出已存档）：Evidence Recall=1.0、Hit=1.0、MRR=0.9166666666666666，与 T010 基线一致；empty_result_rate 仍为 0（无可靠拒答，不扩大结论）。
- 真实本地 BGE 筛选 API 演示（`filter-demo.json` + `filter-demo-notes.md`）：同题换年级/日期结果正确变化，未标注范围/日期正确排除，无匹配时条件不被取消，`encode_documents_calls=1`（重复查询不重编码正文）。
- 页面筛选→搜索→原文→清除条件与一次错误重试的真实浏览器闭环：本轮无浏览器能力，**未验证**，请 Astra 补验（步骤见 verification.md 第 9 节）。stub 级行为已覆盖。

## 修改与新增文件

完整清单（含 sha256/size）见 `changed-files.json`（相对 `step2_code/backend/`；`..\README.md` 为 `step2_code/README.md`）。要点：

- 新增：`retrieval/filters.py`、`tests/test_search_filters.py`、`scripts/demo-filter-search.py`、`examples/filter-demo/`（5 文档 + manifest + README.txt）
- 修改：`api/search.py`、`main.py`、`retrieval/bm25.py`、`retrieval/dense.py`、`retrieval/embedding.py`、`evaluation/run.py`、`static/search.html`、`scripts/check-search-behavior.cjs`、`scripts/download-embedding-model.py`、`README.md`、`..\README.md`

未修改：Astra 的 tasks/reviews/STATUS、历史 submissions/T010、docs/01—04、解析与 gold 校验逻辑、8 题 gold、既有语料示例。

## 已知限制与未完成项

- 真实浏览器闭环待 Astra 补验（无浏览器能力，未写成已通过）。
- 合成资料不代表学校政策；无真实语料效果证据。无生成式问答、可靠拒答、语音、办事、正式双端、数据库、TinyAgent。
- 筛选是资料准入，不是资格结论；版本冲突决策（哪一版作答）仍未实现。
- 无结果时 empty_result_rate 仍为 0：检索仍可能返回无关候选，不能据此宣称拒答能力。
- 工作区非 Git 仓库（`git status` 报 fatal: not a git repository），如实记录，未初始化、未重置。
- 演示脚本借用 TestClient 调用真实应用与真实模型；stderr 有既有 fastapi/starlette 弃用警告，不影响结果。评测计时未做，也未与 T010 的计时比较。

完成后停止，等待 Astra 验收。T012 未发布，不自行推进。
