# 证据矩阵（evidence-matrix.md）

> T028 交付包｜2026-09-28。每项主张标注**实现位置**、**验证层级**与**局限**。验证层级严格区分：
> **[实现]** 代码存在且被测试覆盖｜**[合成实验]** T027 合成评测（v2.1）｜**[模拟]** mock provider/脚本规划器/loopback mock（明确标注的模拟）｜**[历史真实调用]** T014/T025 受控真实 API 冒烟（各自任务记录）｜**[未验证]** 尚无证据。
> 不把设计、mock 与真实冒烟混写。本表为作者（执行模型辅助）整理，非独立教师/盲评标注。

## 1. 数据与解析

| 主张 | 实现 | 验证层级 | 证据 | 局限 |
|---|---|---|---|---|
| TXT/DOCX 逐块解析、块 ID 稳定 | `corpus/parse.py`（`PDF_PARSER_VERSION`/块 ID 派生） | [实现] | `tests/test_corpus_parse.py`、`test_corpus_chunk.py` | 仅简体中文合成/样例文本 |
| 文本型 PDF 逐页解析、页码定位 | `corpus/parse.py::parse_pdf`（pdf_page locator） | [实现] | `tests/test_pdf_corpus.py`（11 项） | 无文本/扫描 PDF 明确报错不冒充成功；未做 OCR |
| 无文本/加密 PDF 显式失败 | 同上 | [实现] | `tests/test_pdf_corpus.py` | — |
| 元数据登记不猜测 | `scripts/register-corpus.py`（is_synthetic 严格 JSON 布尔） | [实现] | `tests/test_run_entry.py::TestT021R1Fixes` | 真实学校元数据待用户提供 |
| 语料哈希与来源核对 | manifest `sha256`、run 输出 `corpus_documents` | [实现][合成实验] | T027 `dataset-hashes.json`（rev1/2/3 冻结） | — |

## 2. 检索与筛选

| 主张 | 实现 | 验证层级 | 证据 | 局限 |
|---|---|---|---|---|
| BM25 检索（k1=1.5,b=0.75,chunk≤500） | `retrieval/bm25.py`、`corpus/chunk.py` | [实现][合成实验] | `tests/test_retrieval_*.py`；T027 v2.1 BM25 R@5=0.950 | 合成小样本，不外推 |
| Dense/Hybrid(RRF k=60) 检索 | `retrieval/dense.py`、`hybrid.py`、`embedding.py`（bge-small-zh-v1.5 本地） | [实现][合成实验] | T027 v2.1 Dense 0.900/0.900/0.706、Hybrid 0.950/0.950/0.892（R/H/M@5） | Hybrid 未显示整体优势；Dense MRR 偏低为样本观察 |
| T011 适用性筛选（None=不限；空数组=未知≠所有人） | `retrieval/filters.py::compute_allowed_document_ids` | [实现][合成实验] | `tests/test_search_filters.py`；T027 同题筛选对（g-year/campus/time-defer）准入断言 | 真实学校 scope 语义待资料到位确认 |
| 逐题条件作用于三模式同一口径 | `evaluation/run.py`（按题 compute_allowed_document_ids→allowed_document_ids） | [实现][合成实验] | `tests/test_evaluation_v2.py::TestConditionsAdmission` | — |

## 3. 证据、引用与问答

| 主张 | 实现 | 验证层级 | 证据 | 局限 |
|---|---|---|---|---|
| 原文摘录（extractive）与证据引用 | `api/ask.py`、`qa/evidence.py`（span/块/文档/哈希/preview 链接） | [实现] | `tests/test_ask_api.py`、`tests/test_qa_evidence.py` | 摘录可按跨度回溯≠该摘录回答了问题 |
| DeepSeek 生成问答适配（结构化 JSON、错误安全映射、零重试） | `qa/deepseek.py`、`qa/providers.py` | [实现] | `tests/test_deepseek_provider.py` | 协议已验证；生成质量未评测 |
| 生成输出校验为**结构校验**（段落非空 + 引用 ID∈实发证据集） | `qa/providers.py::validate_generation` | [实现] | 本地核对（T028-R1）：不受支持文本+合法 E1 → kind=answer | **不含语义蕴含校验**；编号有效≠答案忠于证据；零证据可短路，非空不相关证据不保证识别不足 |
| 真实生成链路可通（受控冒烟） | T014 `live-smoke-deepseek.py` | **[历史真实调用]** | `submissions/T014/`（2 题、1 次 no_hits 短路、usage 370+37=407 tokens） | 仅证明链路；非生成质量结论 |
| 引用跨度与解析块一致（非自证） | T021-R1 跨度独立对照测试 | [实现] | `tests/test_pdf_corpus.py::test_citation_spans_match_parsed_blocks` | — |

## 4. 办事、自查与比较

| 主张 | 实现 | 验证层级 | 证据 | 局限 |
|---|---|---|---|---|
| 带引用办理草稿 + saveable 门（资料不足不冒充完整） | `procedures/service.py::build_draft/verify_snapshot` | [实现] | `tests/test_procedures.py`；本地核对（T028-R1）：proc-review-grade+年级2023 → insufficient/saveable=false（附表引用被准入筛除），proc-apply-defer+2023 → ready | 合成模板（2 事项）；引用核对为结构核对（哈希/跨度/准入）≠语义正确性；不代表学校受理 |
| 办理页手动保存待办（localStorage） | `static/procedures.html` | [实现][模拟] | `scripts/check-procedures-behavior.cjs`（stub 级） | 浏览器行为为 stub/历史浏览器证据（T016—T023 各任务记录） |
| 条件自查（三态、unknown≠满足） | `selfcheck/service.py` | [实现] | `tests/test_self_check.py` | 合成规则一例 |
| 版本比较（条号对齐 + SequenceMatcher 顺序匹配 + 相似度分级） | `comparison/service.py`（T017-R1 lookahead 修复；内部函数名 `_lcs_pairs`，实现为 difflib.SequenceMatcher，非严格 LCS） | [实现] | `tests/test_comparison.py` | 仅段落文本，不含表格语义 |

## 5. 受限编排（Agent 可替换层）

| 主张 | 实现 | 验证层级 | 证据 | 局限 |
|---|---|---|---|---|
| 只读双工具（search_policy/build_checklist_draft）+ 越权拒绝 | `agent/tools.py`（filters/procedure_id 声明隐藏、传入即拒） | [实现] | `tests/test_agent_workflow.py`、`test_deepseek_planner.py` | — |
| 固定流程（选事项→检索→草稿，非 LLM Agent） | `agent/workflow.py::run_fixed_workflow` | [实现] | `tests/test_agent_workflow.py` | — |
| 服务端产物判定（缺草稿≠completed） | `_finish_verdict`（T024-R1） | [实现] | T024-R1 探针 exit 0 | — |
| 模拟规划器（脚本、无 HTTP、标注模拟） | `agent/planner.py::ScriptedPlanner`（无状态按 round_no） | **[模拟]** | `check-workflow-behavior.cjs`、demo-campus 注入 | 非模型能力证据 |
| DeepSeek 结构化规划适配器（真实 HTTP 协议） | `agent/deepseek_planner.py`（call/finish/awaiting_input、审计白名单） | [实现][模拟] | `tests/test_deepseek_planner.py`（loopback mock 串通） | 协议经 mock 验证；真实规划见下 |
| 真实规划往返（受控冒烟） | T025 `live-smoke-planner.py --mode live` | **[历史真实调用]** | `submissions/T025/live-run.json`（4 次官方 HTTP、审计齐备、第 1 轮改写 filters 被拒） | **partial/failed_actions——完整无失败流程未通过**；planner_live_verified=**false** |
| 规划参数收敛/观察截断透明 | T026 声明收紧、obs total/listed/truncated | [实现][模拟] | `tests/test_agent_workflow.py`、`tests/test_deepseek_planner.py`；`docs/collaboration/submissions/T026/offline-replay.json` | 改进未经真实模型验证 |

## 6. 运行入口、状态与语音

| 主张 | 实现 | 验证层级 | 证据 | 局限 |
|---|---|---|---|---|
| 统一正常入口（功能全默认关、缺配置显式降级） | `scripts/serve-corpus.py` + `main.py::create_app` 显式注入 | [实现] | `tests/test_run_entry.py`；config-combos 六组合实测 | — |
| 首页实时能力状态（已配置≠已验证） | `static/home.html`（6 状态接口聚合） | [实现] | `tests/test_run_entry.py`；T022-R1 浏览器复验（Astra，历史） | 本轮未新做浏览器实操 |
| 启动/status/固定流程零规划、零生成请求 | 计数桩断言 | [实现] | `test_run_entry.py`、`test_deepseek_planner.py` | — |
| 本地 ASR（FunASR/Paraformer，静音/空转写拦截） | `asr/{adapter,audio}.py` + 路由 `api/asr.py` | [实现][模拟] | `tests/test_asr.py`；T020 真实本地转写证据（历史） | 未做识别质量评测 |
| 密钥仅本地环境变量、零落盘 | provider/planner from_env；smoke CLI 断言 | [实现] | 各 smoke/测试不泄密断言 | — |

## 7. 实验与评测

| 主张 | 实现 | 验证层级 | 证据 | 局限 |
|---|---|---|---|---|
| 合成检索评测集 v2.1（24 题/13 文档/事实组语义） | `examples/evaluation-v2/`、`evaluation/*` | **[合成实验]** | `submissions/T027/`（gold-revisions、dataset-hashes、results） | 全合成；模型辅助标注（非教师/盲评） |
| 三模式对照指标（最终） | T027 revision 3 | **[合成实验]** | K=5：BM25 0.950/0.950/0.925、Dense 0.900/0.900/0.705833、Hybrid 0.950/0.950/0.891667（R/H/M，20 可答）；4 不足题空检索率 0 | 小样本、无显著性检验；不外推真实校园 |
| 评测管线可复现（命令/哈希/版本） | `evaluation/run.py` + `eval-v2-*.py` | [实现][合成实验] | evaluation-report 第 8 节命令；21 题排名复用+3 题重检索零偏差核对 | — |

## 8. 明确未验证（论文与答辩不得写成已完成）

| 事项 | 状态 | 说明 |
|---|---|---|
| 真实学校语料效果 | [未验证] | 四川农业大学公开资料待用户提供；不爬站、不猜元数据 |
| planner_live_verified | **false** | T025 真实链路已通但完整运行 partial；不升级口径 |
| 生成/规划质量 | [未验证] | T014/T025 仅为链路冒烟，非质量评测 |
| 可靠拒答/空检索保证 | [未验证] | T027 实测三模式对不足题全部有命中（有命中≠有依据） |
| 浏览器交互（本轮） | 未新测 | 各历史浏览器证据归属 T016—T023 验收记录；T028 为文档任务，demo 脚本未在本轮实操 |
| 统计显著性 | [未验证] | 单次小样本运行，无假设检验 |

## 9. T027-R3 文字勘误（本交付包内声明，不改历史原始产出）

1. T027 evaluation-report 主表 Dense 行 rev2→v2.1 的「R/H升」应读作「**R 升、H 不变**」（rev2 Hit 已是 0.900）。
2. 「医院证明或学院书面说明」是**析取/备选表述**，不应称为「合取口径」（历史文本中的「合取」措辞系笔误）。
3. 事实分组与人工核对记录均为**作者/执行模型辅助标注**，不是独立教师标注或盲评。
