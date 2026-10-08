# T030 真实语料检索基线与证据标注 — 实施报告

身份：task_id=T030、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0、planner_live_verified=false**。零外部模型调用、无下载/安装、未 commit/push；未修改已验收语料包 v1.1、产品算法（parser/chunker/retriever/filters/metrics）、旧 gold（旧 8 题与 T027 v2.1 全保留）。

## 概述

以已验收的 `data/corpora/sicau-rag-pilot-v1.1/`（20 份真实资料）为**只读冻结输入**，按原文优先编制 **24 题开发集**（20 可答 + 4 不足；dataset_id `sicau-pilot-eval-v1` v1.0，metric_semantics=fact_group_or_v1.1），标注完整事实与**可替代证据**（组内 OR、组间 AND），**评测前冻结哈希**，再以同一条件（逐题 conditions、TopK=5）**各一次**运行 BM25/Dense/Hybrid。题目与标注由 **MiMo 模型辅助编制，人工复核状态=未复核**；未按检索排名反推 gold、未为提分改题。

## 交付物

| 文件 | 内容 |
|---|---|
| [evaluation-report.md](evaluation-report.md) | 三模式汇总（分母口径）/按题型分组/24 题逐题/7 个失分案例（现象与假设分开）/2 题手算对照/≤3 项优化建议 |
| [human-review.md](human-review.md) | 24 题人工核对表（题目/条件/必要事实与版本/页码·短引句/等价或不足理由/待确认点）；**复核栏全部“未复核”**，含签署区 |
| `data/evaluations/sicau-rag-pilot-eval-v1/questions.json` | 题集与标注（SHA-256 `a9f284b0…`） |
| `…/freeze.json` | 评测前冻结（题集/manifest/20 文件/11 实现文件/BGE 身份哈希；拟题来源+复核状态） |
| `…/results/{bm25,dense,hybrid}.json` + `.stderr.log` + `.exitcode.txt` | 三模式原始 stdout JSON / stderr / 退出码（各一次，均 0；哈希与 freeze 一致） |
| `…/annotation-check.md` | 标注核对（程序化 + 语义两层；事实分组表；不足题已查范围） |
| `scripts/check-real-eval.py` | 小校验工具（契约/引句/准入/事实分组/冻结哈希；复用既有类，不另造评测器） |

## 关键结果（K=5，可答题 n=20）

| 模式 | Recall@5 | Hit@5 | MRR@5 |
|---|---|---|---|
| BM25 | 0.633 | 0.650 | **0.483** |
| Dense (BGE 本地) | 0.633 | 0.650 | 0.391 |
| Hybrid (RRF) | **0.683** | **0.700** | 0.421 |

- 不足题 4 题单独分母：空检索率均 0.000（**2 未记载 + 2 准入排除**，非“拒答率”）。
- 与 T027 合成指标**分表对照、不合并分母**；本基线为开发集检索基线，**不是正式校园准确率**；Hit/MRR 不是整题答对率。
- 失分主因（可观测）：页级大块+chunk 切分使目标跨度 chunk 未入 top5（q06/q08/q12/q14/q15/q19）；同族重复文档挤占（q11/q10）；文号 token 吸引到页眉块（q12/q14/q15）；RRF 融合掉出（q17）。原因假设均标注“待验证”，未下机理结论。

## 验证摘要（详见 verification.md）

- `check-real-eval.py` CHECK OK（24 题/37 证据：契约/引句逐字/准入/事实分组）；freeze 于运行前保存、运行哈希一致。
- 三模式各一次 EXIT 0；2 题手算与机器值一致；T029 勘误按冻结 manifest 执行。
- 样本局限如实：24 题/20 份、单次运行、已见诊断题 5/24、无显著性检验。

完成后停止，等待 Astra 验收。T031 未发布。
