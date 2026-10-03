# T027 检索对照评测与论文证据包 — 实施报告

身份：task_id=T027、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**、planner_live_verified=false、tinyagent_integration_kind=reference。零外部模型调用、无下载、无安装；未改旧 `examples/evaluation` 8 题、原语料、模板、历史 gold；未为得分调产品算法。**数据全部合成，未经真实校园质量验证。**

## 概述

建立独立合成评测集 `examples/evaluation-v2/`（24 题 / 13 文档），按原文独立标注金标准并冻结哈希，用同一语料/题集/条件/top_k=5 实际比较 BM25/Dense/Hybrid，交付逐题结果、聚合指标、案例分析、标注复核清单与论文实验方法草稿。不足题单独分母；检索命中与回答正确严格区分。

## 功能交付（对照任务书）

1. **数据与标注**：24 题（20 可答 + 4 不足，落在 20—30 建议区间，未凑数重复改写），覆盖七类题型（直述 4/同义改写 3/少关键词 2/多证据 3/相似主题干扰 3/筛选 5/材料不足 4）；**三组同题不同筛选对照对**（年级 2024/2025、成都/都江堰、日期 2026-10/2025-10），每对准入证据不同（测试断言）。语料优先复用既有 parse/PDF/比较/筛选合成夹具（逐字节拷贝、文档 ID 保留）+ **2 份明显标注干扰文档**（研究生缓考、学校奖学金）。标注含题型/条件/answerable/精确文档块跨度/逐字引句/判定理由；不足题注明缺什么。**gold 按原文独立制定**（模型辅助编写如实声明于 `authoring_note` 与 gold-review；跨度由原文子串精确定位，未从检索结果反推）；**正式评测前冻结哈希**（`dataset-hashes.json`），无标注修订。
2. **评测管线**：扩展 `evaluation/models.py`（可选标注字段，旧 8 题兼容）与 `evaluation/run.py`（按题应用**产品同一 T011 筛选规则**；同语料/题集/条件/top_k；题型/筛选分组聚合；索引/查询分段计时）。三模式各一次正式运行（BM25 / Dense / Hybrid×本地 BGE `bge-small-zh-v1.5` rev `7999e1d3…`，未下载）。**K=5 主口径**（`metrics.py` 既有 Evidence Recall/Hit/MRR 口径未改；多证据按完整跨度覆盖、文档/块身份一致）；**K=3 仅同命中补充**。可答/不足分开分母：不足题报空检索比例与有结果数，**不入 recall 分母**；逐题 JSON/CSV 记录排名/分数/覆盖/条件/指标；记录模型 ID、语料与题集 hash、chunk/top_k/RRF 参数、命令与版本。
3. **可审阅报告**（`evaluation-report.md`）：三模式对照表 + 按题型/筛选分组 + 12 题逐题差异 + **5 个代表性案例**（成功/失败/相同结果如实展示，引句可回溯）+ **指标手算对照**（多证据 v2-q11、不足 v2-q24 各一，与机器输出一致）。**如实结论：Hybrid 未显示优势**（recall/hit 与 BM25 持平、MRR 反低 0.072），并说明样本规模与难度限制，未制造 Hybrid 必须领先。
4. **论文实验方法草稿**（`experiment-methods.md`）：实验环境/合成数据来源/标注规则/指标定义与分母/变量控制（唯一自变量=检索模式、先冻结 gold、禁调参）/主要发现与局限；**T014 真实问答、T025 真实规划、本离线检索证据分表陈述**，mock 结果不作生成质量证据；真实资料到位后的替换/补测步骤列明。

## 主要结果摘要（详见 evaluation-report.md）

K=5（n=20 可答）：BM25 **0.950/1.000/0.867** > Hybrid 0.950/1.000/0.795 > Dense 0.800/0.850/0.578（R/H/M）。多证据题三模式 recall 同为 0.667（共同短板）；Dense 弱在低频词（0.5/0.5/0.1）与筛选组 g-year-defer（0.5）；不足题 n=4 三模式空检索率均 0（有命中≠有依据）。

## 验证摘要（真实命令见 verification.md）

- **指标手算对照 2 例**（多证据 + 不足题）与机器输出一致。
- **新题集校验**：schema 24 题全过（不足题必有 missing）；`fill-spans` 23 条跨度原文子串精确定位；运行内来源校验（哈希/解析版本/跨度/quote）全过。
- **三模式一次正式运行** + 离线合并；**评测聚焦测试 77 passed**（含旧 8 题兼容、同题不同筛选准入断言、不足题分母口径）。
- **旧 8 题兼容检查**：旧集运行 valid（8 题/6 可答），旧结果记录未篡改。

## 修改与新增文件

- 新增：`scripts/build-eval-v2.py`、`scripts/eval-v2-compare.py`、`tests/test_evaluation_v2.py`、`examples/evaluation-v2/`（README、questions.json、corpus/ 13 文档+manifest）
- 修改：`evaluation/models.py`、`evaluation/run.py`（筛选/标注字段/分组聚合/计时）、`tests/test_evaluation_cli.py`（确定性断言排除非确定计时字段）
- 提交另附：`evaluation-report.md`、`results/`（逐题 JSON/CSV + 聚合 + 三模式原始输出）、`gold-review.md`、`experiment-methods.md`、`dataset-hashes.json`、`blocks-dump.json`/`blocks-text.md`（引句回溯）、`verification.md`、`changed-files.json`
- 未修改：旧 `examples/evaluation`（8 题/gold/README）、原语料夹具、模板、`metrics.py` 指标口径、产品检索算法、Astra 文档

## 可复制 Windows 命令

见 `evaluation-report.md` 第 8 节（语料构建/三模式运行/对照聚合完整命令）。

完成后停止，等待 Astra 验收。T028 未发布。
