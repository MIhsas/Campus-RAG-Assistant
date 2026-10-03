# T027 检索对照评测与论文证据包 — 实施报告（revision 3）

身份：task_id=T027、task_revision=v1、**submission_revision=3、responds_to=T027-R2**、status=ready_for_review、**external_model_calls=0**、planner_live_verified=false、tinyagent_integration_kind=reference。**数据版本 2.0→2.1**（metric_semantics fact_group_or_v1.1 不变）；rev1/rev2 题集/哈希/结果/报告完整保留（`rev1/`、`rev2/`、`*.rev1.*`/`*.rev2.*`）。零外部调用、无下载/安装；未改产品算法、原语料、旧 8 题、`metrics.py` 既有规则。

## 概述（三次修订脉络）

T027 v1 建立独立合成评测集（24 题/13 文档）并完成三模式对照；R1 引入可替代证据组（组内 OR、组间 AND）并撤销 twin 约定；**R2 限定修正 q10 与 q16/q17 的事实分组与题意歧义**：OR 组内每条来源须独立支持组的完整事实——医院证明与书面说明不合并、宽泛「考前」与「考前 3 个工作日」不互替；q10 题面限定 2024 级使材料要求确定，q16/q17 来源系列题面限定保留精确时限比较。详见 `fix-report-r2.md` 与 `gold-revisions.md` 第 4 节。

## 功能交付（对照 R2 返工单）

1. **q10 事实确定**：题面+条件限定「2024级本科生」→ 材料要求确定为医院证明（2 等价源，各自完整支持）；「医院证明或学院书面说明」合取口径与「须同时提交书面情况说明」剔除（不同材料要求不互替，不同文件≠互为替代）；**不把各文件要求变全体 AND**。Astra 探针误判（仅审批+书面说明记满）由回归实测消除。
2. **q16/q17 精度不互替**：同题查询限定来源系列「按入学年级适用的缓考申请办法」——q16 gold=2024 版完整规定「考前提交」、q17 gold=2025 版完整规定「考前 3 个工作日提交」；跨精度合并撤销；双向不互替回归锁定。同题不同筛选对照保留。
3. **OR 完整性原则**：组内每条证据独立支持组声明的完整事实（规则行 + gold-revisions 原则行 + 两语义回归）。
4. **重算**：q10/q16/q17 题面/条件变化 → **子集重检索**（3 题×3 模式，`rerun/`）；其余 21 题**复用 rev2 已存排名计分**（未重复全库向量编码）；合并 `results/` v3。**一致性核验**：21 题×3 模式与 rev2 逐项一致（零偏差）。rev2 题集/哈希/结果保留（`rev2/`）。
5. **汇总/报告/案例/手算更新**：evaluation-report rev3（指标表、6 案例、手算 3 例）；gold-revisions 第 4 节修订理由；gold-review 规则与速查更新；指标变化如实（含 q16 精度收窄的 Dense MRR 下降——**不以得分为依据选措辞**）。

## 指标（v2.1，K=5，n=20）与变化

| 模式 | R@5 | H@5 | MRR@5 | rev2 → v2.1 |
|---|---|---|---|---|
| BM25 | **0.950** | **0.950** | **0.925** | 不变 |
| Dense | **0.900** | **0.900** | 0.706 | R/H 升、MRR 降（q16 精度收窄如实代价） |
| Hybrid | **0.950** | **0.950** | 0.892 | 不变 |

q10/q16/q17 重检索后均全事实组覆盖；**Hybrid 仍未显示整体优势**（观察/假设分离口径沿用）。

## 验证摘要（真实命令见 verification.md / fix-report-r2.md）

- **83 passed**（evaluation + cli + v2，含 R2 语义回归 2）：书面说明不得满足医院证明事实（探针场景 Recall=0.5）、「考前」不得替代「考前 3 个工作日」（Recall=0.0 双向锁定）。
- **手算对照 3 例**与机器一致；**21 题一致性零偏差**；受影响 3 题子集重检索 EXIT 0/0/0。
- 仅两处标注回归 + 受影响评测验证；未跑 UI/ASR/Agent/全量。

## 修改与新增文件（rev3 增量）

- 修改：`examples/evaluation-v2/questions.json`（v2.1，仅 q10/q16/q17）、`scripts/eval-v2-rescore.py`（合并输出）、`tests/test_evaluation_v2.py`（语义回归 2 + 版本断言）
- 提交另附：`fix-report-r2.md`、`gold-revisions.md`（R2 节）、`rerun/`（3 题子集重检索）、`rescore-from-rev2.json`、`rev2/`（题集/哈希/结果存档）；四件更新 rev3
- 未修改：旧 `examples/evaluation`、语料夹具、产品检索算法、`metrics.py`、Astra 文档

完成后停止，等待 Astra 验收。T028 未发布。
