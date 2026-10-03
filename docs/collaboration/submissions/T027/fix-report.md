# T027-R1 定向返工 — 修复报告（fix-report.md）

身份：task_id=T027、task_revision=v1、**submission_revision=2、responds_to=T027-R1**、status=ready_for_review、external_model_calls=0、planner_live_verified=false。**数据版本 1.0 → 2.0；指标语义 unit_evidence_v1.0 → fact_group_or_v1.1。** rev1 题集/gold/哈希/结果完整保留（`rev1/` + `dataset-hashes.rev1.json`）。仅改 v2 标注、必要评测兼容与测试；未调检索算法/参数/模型，零外部调用、无下载/安装。

## 修复 1（P1）：可替代证据系统性复核（全部 24 题，不只 Dense 失分题）

**问题**：rev1「twin 排定」把未限定来源题的逐字相同/等价原文误记为不相关——文档身份被当作相关性判断；q05/q15 为已核实实例，q04/q18 同类，且需全量复核。

**修复**：全量相关性复核（依据=原文语义等价性，**先于重算冻结**，未按检索结果定向）；引入**可替代证据组**（`Evidence.fact_id`）：组内 OR（任一替代来源完整覆盖即满足）、组间 AND（不同必要事实分别要求）；重复来源不作多个必须找齐的事实稀释 Recall（41 条来源 → 23 个必要事实组）。每条替代来源逐一核对准入条件/块/跨度/逐字 quote；仅主题相关或内容冲突的句子不算（不同材料要求可并存为同组；5 日 vs 3 日冲突不可；不同适用对象/奖项不算等价）。**修订 11 题**（q02/q04/q05/q08/q10/q12/q15/q16/q18/q20/q21），13 题复核后不变——清单、理由、前后哈希见 `gold-revisions.md`，逐题 `revision_note` 内联留痕。**rev1 完整保留**：题集逐字节存档（重建核对 sha256=0d58ed95… 一致）、哈希、结果目录 `rev1/results-rev1/`。

**指标影响（实测）**：q05/q15 Dense MRR 0.5→1.0（替代来源首位计正确）；q02 Dense R0→1.0、q16 Dense R0→1.0、q10 BM25/Hybrid R0.5→1.0。总聚合：BM25 0.950/0.950/0.925、Dense 0.875/0.900/0.739、Hybrid 0.950/0.950/0.892（R/H/M@5）。

## 修复 2（P1）：q12 版本歧义消除（题面消歧，不藏 rationale）

**问题**：q12 同时存在 5 工作日（虚构 2024 版）/3 工作日（虚构 2025 版）而题面未限定版本，gold 唯一指 v1 属任意指定。

**修复**：题面明确限定——查询改为「虚构2024版缓考申请办法规定的缓考申请的提交期限和附加材料是什么」（记录为消歧修订，`revision_note` 注明）；v2 干扰资料**保留不删**；其他版本的冲突口径（3 日）明确不算正确来源。q20/q21 同步消歧渠道维度（「线上还是纸质」，同对同题保持）——消歧依据为题意与 gold 一致性（题面变化 → **重跑检索**，见下）。**如实记录**：q12 重跑后三模式均 R0/H0/M0（top1 为标题块，答案块出 top-5）——失分如实保留，未回头改措辞提分；观察/假设分离记录于 evaluation-report 案例 4。

## 修复 3：重算方法与一致性（仅标注变化重计分；题面变化重检索）

- **21 题查询/条件未变**：按允许口径用已存排名重计分（`scripts/eval-v2-rescore.py` → `rescore-from-rev1.json`）；**q12/q20/q21 题面变化 → 重跑受影响检索**（全量三模式重跑以保持输出统一；未变化数据仅一次必要编码）。
- **一致性交叉核对**：21 题 × 3 模式「已存排名重计分」vs「全新重跑」**逐项零偏差**——未混用旧哈希（v2.0 新冻结 `dataset-hashes.json`，rev1 哈希存档）。
- 新逐题/聚合结果、案例、手算对照、方法说明全部更新（evaluation-report / gold-review / experiment-methods）。

## 随单修正（一并完成）

1. **观察与假设分离**：evaluation-report 第 6 节改写——「Dense 弱与小型模型有关」「差异来自词面而非其他原因」等因果表述降级为**待验证假设**；MRR/排序变化按实测直接报告，不升华为机理结论；**「RREF」笔误改「RRF」**。
2. **夹具警示语说明**：复用夹具正文「不得用于论文评测」为原夹具标注（保留不动），本轮读法=合成管线实验、不代表真实论文校园效果——evaluation-report 第 9 节说明来源用途差异。

## 验证（聚焦，真实退出码）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_evaluation.py tests/test_evaluation_cli.py tests/test_evaluation_v2.py -q -p no:cacheprovider --basetemp .cache/t027r1 --tb=short -rs
# 81 passed（77 + 新增事实组语义 4），退出码 0
```

对照返工单聚焦项：
- **等价证据首位计分**：`test_alternative_second_source_scores_full`（q05 型：仅命中第二替代来源 → 该事实满分）+ 实测 q05/q15 Dense MRR→1.0。
- **多事实部分覆盖不得满分**：`test_two_facts_partial_coverage_half`（覆盖一组 → 0.5）+ `test_alternatives_do_not_dilute_denominator`（3 来源 1 事实分母=1）+ 实测 q10 Dense R=0.5。
- **旧 8 题兼容**：`test_old_eight_questions_still_validate_and_score_identically`（summary 与 rev1 逐项一致：R1.0/H1.0/M0.9167、6+2）；旧集目录零改动。
- 相关评测测试全过（含 q16/q17 准入断言、不足题分母、q12/q20/q21 消歧断言）。
- 一致性核对脚本输出 21 题×3 模式零偏差（rescore vs 重跑）。

未跑 UI/ASR/Agent/全量（未涉相关改动）；未重复无关测试。

## 未验证项

1. q12 失分原因（版本元数据 vs 文本检索）为**待验证假设**，未做对照实验。
2. 真实校园语料、统计显著性不在本轮范围。
3. 生成/规划质量证据类别分开（未混入）。
