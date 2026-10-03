# T027 验证记录（submission_revision=3，responds_to=T027-R2）

工作目录 `F:\Collage Paper\step2_code\backend`。按返工单只做两处标注回归及受影响评测验证；**未跑无关全量/UI/ASR/Agent**；零外部模型调用、无下载/安装；未改产品算法、原语料、旧 8 题。rev1/rev2 记录归档 `verification.rev1.md`/`verification.rev2.md`。

## 1. 两处标注回归（新增，83 项全过）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_evaluation.py tests/test_evaluation_cli.py tests/test_evaluation_v2.py -q -p no:cacheprovider --basetemp .cache/t027r2b --tb=short -rs
# 83 passed in 10.85s
# 退出码：0
```

1. **q10 材料事实**（`test_q10_material_sources_same_requirement_no_mix`）：v2.1 q10 f2 组两源均为医院证明要求（无书面说明混入）、条件=2024 级；**Astra 探针场景实测**——命中 f1 审批源 + 「须同时提交书面情况说明」块（非 f2 来源）→ 事实覆盖 1/2、**Recall=0.5**（rev2 探针得到 1.0 的误判消除）。
2. **q16/q17 精度不互替**（`test_q16_q17_precision_not_interchangeable`）：q17 gold 含「3 个工作日」、q16 gold 不含天数、同题「按入学年级适用」来源限定；宽泛「考前」命中对 q17 → **Recall=0.0**；反向 3 日句命中对 q16（不同来源系列跨度）→ **Recall=0.0**（双向锁定）。

受影响评测验证（既有 81 项全过）：q16/q17 同题不同筛选准入断言、不足题分母、消歧断言、旧 8 题行为逐项一致（R1.0/H1.0/M0.9167）、事实组 OR/AND/分母语义 4 项——均不受三题修订影响。

## 2. 受影响题重检索与排名复用（真实命令与退出码）

```bash
# q10/q16/q17 子集重检索（各模式一次）：rerun/{bm25,dense,hybrid}.json — EXIT 0/0/0
# 21 题复用 rev2 排名计分 + 合并（eval-v2-rescore.py）— EXIT 0
#   rescored: 21 | rerun: ['v2-q10', 'v2-q16', 'v2-q17']
# 聚合（eval-v2-compare.py）— EXIT 0
```

- **一致性核验**（内联核对，退出码 0）：21 题 ×3 模式合并结果与 rev2 记录**逐项零偏差**；`rescore-from-rev2.json` 中 source 字段区分 rescored_from_saved_ranking / rerun。
- **未重复全库向量编码**：21 题零编码；仅 3 题子集重跑（每模式一次索引构建，边界已在 merge_note 注明）。
- rev2 完整保留：`rev2/questions.rev2.json` 逐字节核对 sha256=25f379a2… 与 `rev2/dataset-hashes.rev2.json` 一致；`rev2/results-rev2/` 原样。
- v2.1 哈希冻结：`dataset-hashes.json`（questions=afdedadf…；语料/manifest 与 rev1/rev2 一致未变）。

## 3. 三题重检索实测结果（详见 evaluation-report 案例 1—3）

- q10（双事实）：三模式 R=1.0 全组覆盖（BM25/Hybrid rank1 fd-2024；Dense rank2/3）。
- q16：BM25/Hybrid rank1 fd-2024（MRR 1.0）；Dense rank3（MRR 0.333）。
- q17：三模式 rank1 fd-2025（MRR 1.0）。
- 手算对照 3 例（q10 事实组/精度互替/q24 不足题）与机器一致。

## 4. 指标变化（rev2 → v2.1，K=5）

BM25 0.950/0.950/0.925 不变；Dense 0.875→0.900 / 0.900→0.900 / 0.739→**0.706**（q16 精度收窄如实代价）；Hybrid 0.950/0.950/0.892 不变。**未以得分为依据选择措辞**。

## 5. 依赖

未安装、未下载、requirements 未改。无需 pip check。

## 6. 未验证项

1. q12 失分假设未做对照实验（不在本轮范围，延续 rev2 口径）。
2. 真实校园语料、统计显著性不在范围；不为任何模式调参。
