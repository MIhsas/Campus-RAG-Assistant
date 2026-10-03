# T027 验证记录（submission_revision=2，responds_to=T027-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。按返工单只跑聚焦验证（等价证据首位计分、多事实部分覆盖、旧 8 题兼容及相关评测测试）；**未跑 UI/ASR/Agent/全量**；零外部模型调用、无下载、无安装；未改检索算法/参数。rev1 记录归档 `verification.rev1.md`。

## 1. 聚焦测试（81 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_evaluation.py tests/test_evaluation_cli.py tests/test_evaluation_v2.py -q -p no:cacheprovider --basetemp .cache/t027r1 --tb=short -rs
# 81 passed in 10.47s
# 退出码：0
```

对照返工单聚焦项（新增事实组语义 4 项 + 既有 77 项全过）：

- **等价证据首位计分**：`test_alternative_second_source_scores_full`——同事实两逐字等价来源、仅命中第二来源 → 该事实 recall=1.0/hit=1.0/mrr=1.0（实测对应 q05/q15：Dense rank1 为替代来源，MRR 0.5→1.0）。
- **多事实部分覆盖不得满分**：`test_two_facts_partial_coverage_half`（两必要事实覆盖一组 → recall 0.5；实测 q10 Dense R=0.5）；`test_alternatives_do_not_dilute_denominator`（3 来源 1 事实 → 分母 1，不稀释）。
- **旧 8 题兼容**：`test_old_eight_questions_still_validate_and_score_identically`——旧集合法（无新字段亦过、metric_semantics 回落 unit_evidence_v1.0）、summary 与 rev1 **逐项一致**（evidence_recall=1.0、hit=1.0、mrr=0.9167、6 可答+2 不足）。
- 相关评测测试：q16/q17 同题不同筛选准入断言（事实组各自覆盖；fd-2025 不入 q16 命中、fd-2024 不入 q17）、不足题不入 recall 分母、q12/q20/q21 消歧断言（q12 题面含「2024版」、q20/q21 同对同题且含「线上」）、fact_id/revision_note/metric_semantics 字段校验。

## 2. 重算与一致性核验（真实命令）

```bash
# gold-only 变化 21 题：已存排名重计分（允许口径）
./.venv/Scripts/python.exe scripts/eval-v2-rescore.py --questions examples/evaluation-v2/questions.json --rev1-questions …/rev1/questions.rev1.json --results …/rev1/results-rev1/{bm25,dense,hybrid}.json --out …/rescore-from-rev1.json
# rescored: 21 | changed_for_rerun: ['v2-q12', 'v2-q20', 'v2-q21']；退出码 0

# 题面变化题重跑检索（三模式各一次，EXIT 0/0/0）+ 对照聚合（EXIT 0）
# 指标（K=5）：bm25 R0.950/H0.950/M0.925；dense R0.875/H0.900/M0.739；hybrid R0.950/H0.950/M0.892
```

- **一致性交叉核对**（内联脚本，退出码 0）：21 题 × 3 模式「已存排名重计分」与「全新重跑」recall/hit/mrr **逐项零偏差**——未变化数据无隐性漂移；未混用旧哈希（v2.0 冻结 `dataset-hashes.json`，rev1 哈希/题集/结果存档 `rev1/`）。
- rev1 题集存档完整性：`rev1/questions.rev1.json` 由 rev1 草稿确定性重建并核对 sha256=`0d58ed95…`（与 rev1 冻结值一致，逐字节）。

## 3. 指标手算对照（evaluation-report 第 5 节详列）

- **多证据 q10（BM25，事实组口径）**：f1 组（3 源）+ f2 组（5 源）各至少一源完整覆盖 → 事实 2/2 → Recall=1.0、MRR=1.0——与机器一致（分母变化来自语义修订而非命中变化，rev1 逐证据口径记 0.5）。
- **部分覆盖（Dense q10）**：仅 f2 组覆盖 → 1/2 → Recall=0.5——组间 AND 不得满分，与机器一致。
- **不足题 q24**：gold 空 → R/H/M=None 不入分母；returned=5 计有结果数——与机器一致。

## 4. 依赖

未安装依赖、未下载模型、requirements 未改。无需 pip check。

## 5. 未验证项

1. q12 失分原因（版本元数据 vs 文本检索）为待验证假设，未做对照实验（如实标注于报告）。
2. 真实校园语料、统计显著性不在本轮范围；不为任何模式调参。
3. 生成/规划质量证据类别分开，未混入本实验。
