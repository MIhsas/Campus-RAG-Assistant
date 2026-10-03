# T027 检索对照评测报告（evaluation-report.md，revision 3）

**数据版本**：dataset `eval-v2-synthetic` **v2.1**（T027-R1 相关性复核 + T027-R2 限定事实分组修订，见 `gold-revisions.md`）；指标语义 `fact_group_or_v1.1`（可替代证据组：组内 OR、组间 AND；**组内每条来源独立支持组的完整事实**）。rev1/rev2 结果完整保留（`rev1/`、`rev2/`）。
**数据性质：全部合成资料（13 文档 / 52 块 / 24 题），未经真实校园质量验证；本报告是合成管线实验记录，不是校园准确率结论。** 三模式同语料/题集/条件/top_k=5；K=3 同命中补充口径。零外部模型调用。

## 1. 聚合指标（可回答题 n=20 为分母；材料不足题 n=4 单独分母）

### 主口径 K=5

| 模式 | Evidence Recall@5 | Hit@5 | MRR@5 | rev2 → v2.1 变化 |
|---|---|---|---|---|
| BM25 | **0.950** | **0.950** | **0.925** | 不变（q10/q16/q17 三题重检索后仍全组覆盖） |
| Dense (bge-small-zh-v1.5) | **0.900** | **0.900** | 0.706 | R/H 升（q10 限定后双事实覆盖）；MRR 降（q16 精度限定收窄 gold，见案例 3） |
| Hybrid (RRF k=60) | **0.950** | **0.950** | 0.892 | 不变 |

### 补充口径 K=3

| 模式 | Recall@3 | Hit@3 | MRR@3 |
|---|---|---|---|
| BM25 | 0.950 | 0.950 | 0.925 |
| Dense | 0.800 | 0.800 | 0.683 |
| Hybrid | 0.950 | 0.950 | 0.892 |

### 材料不足题（n=4，不入 recall 分母）：三模式空检索率均 0.000、有结果题数 4

**有命中不等于有依据、空检索不等于模型可靠拒答**（实测不变）。

## 2. 按题型分组（K=5）

| 题型 | n(可答) | BM25 R/H/M | Dense R/H/M | Hybrid R/H/M |
|---|---|---|---|---|
| direct 直述 | 4 (4) | 1.000/1.000/1.000 | 1.000/1.000/0.812 | 1.000/1.000/0.875 |
| paraphrase 同义改写 | 3 (3) | 1.000/1.000/1.000 | 1.000/1.000/0.833 | 1.000/1.000/1.000 |
| low_keyword 少关键词 | 2 (2) | 1.000/1.000/1.000 | **0.500/0.500/0.100** | 1.000/1.000/1.000 |
| multi_evidence 多证据 | 3 (3) | 0.667/0.667/0.667 | 0.667/0.667/0.500 | 0.667/0.667/0.667 |
| distractor 相似主题干扰 | 3 (3) | 1.000/1.000/1.000 | 1.000/1.000/1.000 | 1.000/1.000/1.000 |
| filtered 年份/日期筛选 | 5 (5) | 1.000/1.000/0.900 | 1.000/1.000/0.733 | 1.000/1.000/0.867 |
| unanswerable 材料不足 | 4 (0) | 单独分母（见上） | 同左 | 同左 |

## 3. 按筛选分组（K=5）

| 分组 | n(可答) | BM25 R/H/M | Dense R/H/M | Hybrid R/H/M |
|---|---|---|---|---|
| no_filter | 16 (13) | 0.923/0.923/0.923 | 0.846/0.846/0.688 | 0.923/0.923/0.885 |
| filtered（q10/q11 条件题） | 2 (2) | 1.000/1.000/1.000 | 1.000/1.000/0.750 | 1.000/1.000/1.000 |
| g-year-defer（年级对） | 2 (2) | 1.000/1.000/1.000 | 1.000/1.000/0.667 | 1.000/1.000/1.000 |
| g-campus-defer（校区对） | 2 (2) | 1.000/1.000/0.750 | 1.000/1.000/0.667 | 1.000/1.000/0.667 |
| g-time-defer（日期对） | 2 (1) | 1.000/1.000/1.000 | 1.000/1.000/1.000 | 1.000/1.000/1.000 |

## 4. 代表性案例

**案例 1（T027-R2 材料事实确定）v2-q10「2024级本科生缓考申请的证明材料和审批流程」**：适用范围限定后材料要求确定为**医院证明**（fd-2024「附医院证明」/登记表「需医院证明」两源等价，各自完整支持该要求）；「医院证明或学院书面说明」合取口径与「须同时提交书面情况说明」**不再并组**（不同材料要求不互替）。重检索后三模式**双事实组全覆盖（R=1.0）**：BM25/Hybrid rank1 即 fd-2024（审批+材料同块），Dense 于 rank2/3 覆盖。rev2 的探针误判（仅审批+书面说明即记满）由回归测试锁定消除。

**案例 2（T027-R2 精度不互替）v2-q16/q17（g-year-defer）**：来源系列=按入学年级适用的缓考申请办法——q16 gold=2024 版完整规定「须在考前提交」、q17 gold=2025 版完整规定「须在考前 3 个工作日提交」。宽泛「考前」不满足 q17 的 3 日要求（反之亦然，回归双向锁定）。重检索后 q16：BM25/Hybrid rank1 fd-2024（MRR 1.0）、Dense rank3（MRR 0.333）；q17 三模式 rank1 fd-2025（MRR 1.0）。同题不同筛选、不同精确度规定的对照成立。

**案例 3（精度限定的如实代价）**：q16 的 Dense MRR 由 rev2 的 1.000（当时 gold 含多源、rank1 命中 cmp-v2 3 日句）变为 **0.333**（gold 收窄到 fd-2024 完整规定后其 dense 排名 rank3）——全局 Dense MRR 0.739→0.706 的主要来源。**不为得分回改措辞**；这是「精确时限比较」语义的直接结果，如实报告。

**案例 4（版本消歧·持续观察）v2-q12**：维持 v2.1 未再改动；重检索未覆盖范围（复用 rev2 排名计分）——三模式仍 R0/H0/M0（观察与假设见 rev2 报告口径：版本信息在元数据、答案块字面重合低——待验证假设，非结论）。

**案例 5（等价证据首位计分，沿用 rev2 修正）v2-q05/q15**：逐字同句/同期限多源组内 OR，Dense rank1 替代来源计正确（MRR 1.0）——rev2 已核实，v2.1 不变。

**案例 6（不足题有命中）v2-q24**：三模式全部返回结果、top1 fd-future 提及线上系统无网址——有命中≠有依据（不变）。

## 5. 指标手算对照

**多事实 v2-q10（BM25，v2.1）**：f1（审批 2 源）+ f2（医院证明 2 源）。rank1 fd-2024 块完整覆盖 f1 一源与 f2 一源 → 事实 2/2 → **Recall=1.0**；相关首排名 1 → MRR=1.0。机器一致。
**精度不互替（语义回归）**：命中 f1 源 + 「书面情况说明」句（非 f2 来源）→ 事实覆盖 1/2 → **Recall=0.5**；宽泛「考前」命中对 q17 → **Recall=0.0**——两条均由单元回归实测锁定（`test_q10_material_sources_same_requirement_no_mix`、`test_q16_q17_precision_not_interchangeable`）。
**材料不足 v2-q24**：gold 空 → R/H/M=None 不入分母；returned=5 计有结果数——机器一致（不变）。

## 6. 结论与限制（实测观察 vs 原因假设分开）

**实测观察**（v2.1）：
1. 三模式排序：BM25 ≈ Hybrid（R/H 并列 0.950/0.950；MRR 0.925 vs 0.892）> Dense（0.900/0.900/0.706）。**Hybrid 仍未显示整体优势**。
2. R2 限定使 q10/q16/q17 三题语义确定且三模式均全组覆盖；q16 精度收窄使 Dense MRR 如实下降（案例 3）。
3. 少关键词题 Dense 持续弱（q08 R0）；多证据组 recall 0.667（q12 单题拖累）；不足题三模式全有命中。

**原因假设（待验证，不作结论）**：同 rev2——Dense 对专名/低频词偏弱或与小型向量模型表达粒度有关（无规模对照）；q12 失分或与版本信息仅存于元数据有关（无元数据检索对照）。

**限制**：24 题/13 合成文档样本小；无显著性检验；不为任何模式调参/调标注（R2 修订依语义独立确定、先于重算冻结）；不外推真实校园。

## 7. 产物索引

| 文件 | 内容 |
|---|---|
| `results/{bm25,dense,hybrid}.json` | 合并模式输出（21 题 rev2 排名计分 + 3 题子集重检索；含 merge_note） |
| `results/per-question.json` `results/per-question.csv` `results/aggregate.json` | v2.1 逐题/聚合对照 |
| `rerun/{bm25,dense,hybrid}.json` | q10/q16/q17 子集重检索原始输出 |
| `rescore-from-rev2.json` | 21 题排名复用计分 + 3 题 rerun 拼接记录（source 字段区分） |
| `gold-revisions.md` | 修订清单（R1+R2 各节：前后哈希、逐题理由） |
| `rev1/` `rev2/` | 前两版题集/哈希/结果完整存档 |
| `dataset-hashes.json` 等 | v2.1/rev2/rev1 冻结哈希 |

## 8. 可复制 Windows 命令

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
# 受影响 3 题子集重检索
& .\.venv\Scripts\python.exe -m campus_assistant.evaluation.run --manifest examples\evaluation-v2\corpus\manifest.json --corpus-root examples\evaluation-v2\corpus --questions .cache\t027\questions-rerun-subset.json --top-k 5 --mode bm25 > 'F:\Collage Paper\docs\collaboration\submissions\T027\rerun\bm25.json'
# （dense/hybrid 同命令加 --model-path models\bge-small-zh-v1.5）
# 排名复用计分 + 合并
& .\.venv\Scripts\python.exe scripts\eval-v2-rescore.py --questions examples\evaluation-v2\questions.json --rev1-questions 'F:\Collage Paper\docs\collaboration\submissions\T027\rev2\questions.rev2.json' --results 'F:\Collage Paper\docs\collaboration\submissions\T027\rev2\results-rev2\bm25.json' 'F:\Collage Paper\docs\collaboration\submissions\T027\rev2\results-rev2\dense.json' 'F:\Collage Paper\docs\collaboration\submissions\T027\rev2\results-rev2\hybrid.json' --rerun-results 'F:\Collage Paper\docs\collaboration\submissions\T027\rerun\bm25.json' 'F:\Collage Paper\docs\collaboration\submissions\T027\rerun\dense.json' 'F:\Collage Paper\docs\collaboration\submissions\T027\rerun\hybrid.json' --out 'F:\Collage Paper\docs\collaboration\submissions\T027\rescore-from-rev2.json' --merged-out-dir 'F:\Collage Paper\docs\collaboration\submissions\T027\results'
& .\.venv\Scripts\python.exe scripts\eval-v2-compare.py --questions examples\evaluation-v2\questions.json --results 'F:\Collage Paper\docs\collaboration\submissions\T027\results\bm25.json' 'F:\Collage Paper\docs\collaboration\submissions\T027\results\dense.json' 'F:\Collage Paper\docs\collaboration\submissions\T027\results\hybrid.json' --out-dir 'F:\Collage Paper\docs\collaboration\submissions\T027\results'
```

## 9. 夹具警示语说明（沿用）

复用夹具正文保留原「不得用于论文评测或真实校园问答」合成警示（未改动）；本轮为合成管线对照实验，不代表真实论文校园效果。
