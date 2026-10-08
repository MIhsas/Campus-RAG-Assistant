# T034 重叠分块离线对照 — 实施报告（report.md，submission_revision=1）

身份：task_id=T034、task_revision=v1、**submission_revision=1、status=ready_for_review、external_model_calls=0、planner_live_verified=false**。零外部模型调用（本地既有 BGE）、无下载/安装、未 commit/push、未修改 Astra 文件/STATUS/CLAUDE。原语料、T030/T031/T032/T033 实验、模板与历史提交只读未动。

## 概述

对真实 T030 v1.3 开发集做**一次固定参数**对照：baseline=历史无重叠分块 vs candidate=500 字窗口/100 字重叠（步长 400）。原题面/四条件/gold/评分公式/TopK/BM25/BGE/RRF 全部不变，**不混入 T031 文件选择条件**，不网格搜索、不按得分改题。详见 [experiment-report.md](experiment-report.md) 与 `data/evaluations/sicau-rag-overlap-v1/`（`frozen-config.json` 跑前冻结 + `experiment.json` 逐题原始输出）。

**实现**（`corpus/chunk.py` 最小扩展）：可选 `overlap_chars`（默认 0，**旧 chunk ID/顺序/文本/字段语义/表格处理逐字节兼容**——golden ID 回归通过）；仅作用于 paragraph 块内窗口；尾窗到块尾终止；table_row/解析块不变、不跨页拼块、不改原文；重叠运行以 `block_window_overlap_v1` 策略名与参数进入 chunk ID（身份明确）。只由独立实验脚本显式调用，**未改产品默认、网页开关、服务参数、检索模型与评分公式**。

## 关键结果（K=5，可答 n=20；不足 n=4 单独分母，空检索率双分支 0.000）

| 模式 | Recall base→cand | Hit base→cand | MRR base→cand |
|---|---|---|---|
| BM25 | 0.725→0.725 | 0.750→0.750 | 0.600→0.596 |
| Dense | 0.700→**0.675** | 0.700→0.700 | 0.443→**0.467** |
| Hybrid | 0.700→0.700 | 0.700→0.700 | 0.542→**0.583** |

- **边界事实**（实际案例 2 处）：q10 f1-s7、q20 f1-s2 的 gold 源跨度被 500 硬边界切开，candidate 有完整覆盖块——「候选中存在完整事实」改善（q10 f1 可覆盖源 6/7→7/7、q20 2/3→3/3），但因 OR 组内他源已满足，**未转化为 question 级 Recall 变化**（两个层次如实区分）。
- **回退**（3 处）：q11 dense Recall 1.0→0.5（重叠窗口挤占 top5）；q10 dense MRR 1.0→0.5；q17 bm25 MRR 0.333→0.25（同块重叠窗口重复命中挤占）。
- **重复命中**：candidate top5 内 3–4 题/模式存在同块/重叠区间命中（各 4 对）。
- **无改善**：72 对比行中 65 行完全相同（含全部既有失分题）。

## 结论（默认不切换）

收益（2 处源可覆盖性、Dense/Hybrid MRR 小升）与代价（Dense Recall 回退、重复挤占、个案回退）相互抵消且不稳定。**建议不采用为产品默认（保持 overlap=0）**；`overlap_chars` 保留为显式实验参数。本轮**不改变产品默认配置**。

## 验证摘要（详见 verification.md）

新增业务回归 9 项（默认字节/ID 兼容 golden、重叠跨度逐字+尾窗终止、跨硬边界事实仅候选完整覆盖、table_row 不变、参数校验）全过；既有 chunk 54 项、检索/评测聚焦 98 项全过；BM25 未改路径兼容检查 **24/24** 与 T030 存储排名一致（基线身份明确，未覆盖）。

完成后停止，等待 Astra 验收。T035 未发布。
