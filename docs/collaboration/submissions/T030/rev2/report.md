# T030 真实语料检索基线与证据标注 — 实施报告（revision 2）

身份：task_id=T030、task_revision=v1+T030-R1 返工、**submission_revision=2、responds_to=T030-R1**、status=ready_for_review、**external_model_calls=0、planner_live_verified=false**。零外部模型调用、无下载/安装、未 commit/push；未修改已验收语料包 v1.1、产品算法（parser/chunker/retriever/filters/metrics/run）、旧 gold（旧 8 题与 T027 v2.1 全保留）。数据版本 **dataset_version=1.2**（与提交修订号分别记录，不混淆）。

## 概述（相对 revision 1 的变化）

revision 1 被 [T030-R1](../../reviews/T030-R1.md) 退回修改，三项必修已完成：

1. **冻结校验实际为空操作（P1）**：`scripts/check-real-eval.py` 已按真实 freeze schema（dataset/corpus_pack/implementation/model/annotation 五节）核对哈希，缺关键结构/空清单/零项检查均明确失败，哈希漂移非零退出；随单补入标注说明文件哈希。聚焦回归（有效结构通过、错哈希拒绝、缺结构拒绝、五类单点哈希漂移参数化检查）全部符合期望，Astra 错哈希探针复跑通过。
2. **可替代证据漏标（P1）**：q05 五源齐、q08 同文重述计源；续接复核另发现并补全 **q10 教学管理族 4 组跨版本源**（同类漏标）。q05 替代源计分回归实证（dense MRR 0.2→0.5、hybrid 1/3→1，与 Astra 反事实数字一致）。
3. **题目范围与标准答案不一致（P1）**：q01/q02 初修限定、q06/u04 基本信息情形限定与 fact 重组、q11 四情形、q12 基本申请条件、q14/q15 对照范围、q18 前提消歧、q13 短期课程排除补全；24 题逐题「修改/不变及理由」见 [gold-revisions.md](gold-revisions.md)。

## 交付物

| 文件 | 内容 |
|---|---|
| [evaluation-report.md](evaluation-report.md) | 三模式汇总（v1.2/草稿/rev1 三列对照）/分组/24 题逐题/失分案例/观察与假设分离/2 题手算/局限/≤3 项建议 |
| [gold-revisions.md](gold-revisions.md) | 逐题两轮修订清单（修改/不变及理由）、rev1→v1.2 分数差异全录、rev1 哈希更正 |
| [human-review.md](human-review.md) | 24 题人工核对材料（同步 v1.2 题面/gold）；**复核栏全部「未复核」**，含签署区 |
| [verification.md](verification.md) | 全部真实命令/退出码、聚焦回归、来源一致性核验 |
| `data/evaluations/sicau-rag-pilot-eval-v1/questions.json` | 题集与标注 v1.2（SHA-256 `799ed1c112d0b89f…`，57 条证据） |
| `…/freeze.json` | v1.2 冻结（38 项：题集/manifest/20 文件/11 实现/BGE 身份/标注说明） |
| `…/results/{bm25,dense,hybrid}.json` | 合并重计分结果（20 题复用排名 + 4 题 rerun-v12；`rescore-v12.json` 记录逐题来源） |
| `…/results/rerun/`、`…/results/rerun-v12/` | 两次真实子集 CLI 输出（10 题 v1.1 / 4 题 v1.2），含 stderr+exitcode |
| `…/annotation-check.md` | 标注核对 v1.2（事实分组表、不足题已查范围、运行策略） |
| `scripts/check-real-eval.py` | 冻结校验修复（真实 schema、拒绝零项通过、分类哈希核对） |
| [fix-checks/](fix-checks/) | 聚焦回归探针及其输出、Astra 探针复跑输出 |
| `rev1/`、`data/…/rev1/`、`data/…/midway-20261004-v1_1-draft/` | rev1 提交件与数据归档、v1.1 中断现场归档（只读） |

## 关键结果（K=5，可答题 n=20，dataset v1.2）

| 模式 | Recall@5 | Hit@5 | MRR@5 |
|---|---|---|---|
| BM25 | **0.725** | **0.750** | **0.600** |
| Dense (BGE 本地) | 0.700 | 0.700 | 0.452 |
| Hybrid (RRF) | 0.700 | 0.700 | 0.542 |

- 不足题 4 题单独分母：空检索率 0.000（2 未记载 + 2 准入排除，非「拒答率」）。
- 与 T027 合成指标**分表对照、不合并分母**；本基线为开发集检索基线，**不是正式校园准确率**；Hit/MRR 不是整题答对率。
- 得分升降全部来自标注/题面语义修正（补源、消歧、前提补全、fact 重组），算法/模型/语料未变，**不主张检索能力改进**；反向变化（q03/q01-dense/q04/q11-bm25）原样记录。

## 验证摘要（详见 verification.md）

- `check-real-eval.py` CHECK OK（24 题/57 证据；冻结 38 项），exit 0；错哈希/缺结构/五类单点漂移全部 exit 1；Astra 探针复跑 exit 0（wrong_hash_rejected=True）。
- v1.2 重检索 4 题×三模式子集 CLI 各一次 exit 0；合并重计分 exit 0；72 条排名与来源逐项一致、gold 未变题 54/54 分数零漂移。
- q05 替代源计分回归与 Astra 反事实数字一致；2 题手算与机器值一致。
- 样本局限如实：24 题/20 份、子集+复用混合口径、已见诊断题 5/24、无显著性检验、人工未复核。

完成后停止，等待 Astra 验收。T031 未发布。
