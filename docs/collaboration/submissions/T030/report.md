# T030 真实语料检索基线与证据标注 — 实施报告（revision 3）

身份：task_id=T030、task_revision=v1+T030-R1+T030-R2、**submission_revision=3、responds_to=T030-R2**、status=ready_for_review、**external_model_calls=0、planner_live_verified=false**。零外部模型调用、无下载/安装、未 commit/push；未修改已验收语料包 v1.1、产品算法（parser/chunker/retriever/filters/metrics/run）、旧 gold（旧 8 题与 T027 v2.1 全保留）。数据版本 **dataset_version=1.3**（与提交修订号分别记录，不混淆）。

## 概述（相对 revision 2 的变化，T030-R2 两处收尾）

R2 确认冻结校验修复已关闭（不重复返工）；本轮仅修两处标注及相关产出：

1. **q10 两条 f1 半事实（P1）**：cc25/dc971233、bb8b/090f4a9c 的 f1 引文原止于「导师评定成绩（50%）」，未含第二组成部分「和答辩成绩（50%）」——半事实被当成完整 f1（R2 最小探针实证单命中误计 Recall 0.5）。已延长两跨度至含答辩 50%（两个组成部分+比例齐备；被分页截断的句尾「组成」不追补）。q10 query/conditions 不变，**复用排名重计分，分数不变（如实记录）**。聚焦断言固化「只命中导师50%不能覆盖完整 f1」。
2. **q13 题面范围（P2）**：后半问改为「**依据该办法第十条和第十一条**，哪些课程不作学分认定？」——条文限定取代「不作/不进行」换词；声明本题为受单块引文证据契约限制的开发集题目，**不称其为该办法全部排除情形**（第四条情形继续如实入档）。gold 不变，**仅 q13 三模式重检索**。

## 交付物

| 文件 | 内容 |
|---|---|
| [evaluation-report.md](evaluation-report.md) | 三模式汇总/分组/24 题逐题/失分案例/观察与假设/手算（含 R2 半事实对照）/局限/建议 |
| [gold-revisions.md](gold-revisions.md) | v1.3 轮（R2）变更 + 历轮逐题修订清单、rev1→v1.2 分数差异全录、哈希链 |
| [human-review.md](human-review.md) | 24 题人工核对材料（v1.3 题面/gold）；**复核栏全部「未复核」** |
| [verification.md](verification.md) | 真实命令/退出码、探针断言、来源一致性核验 |
| `data/evaluations/sicau-rag-pilot-eval-v1/questions.json` | 题集 v1.3（SHA-256 `5fde70a332744b64…`，57 条证据） |
| `…/freeze.json` | v1.3 冻结（38 项） |
| `…/results/{bm25,dense,hybrid}.json` | 合并重计分（23 题复用 + q13 rerun；`rescore-v13.json` 记录逐题来源） |
| `…/results/rerun-v13/` | q13 三模式子集 CLI 三件套（各 exit 0） |
| `…/annotation-check.md` | 标注核对 v1.3（q10/q13 行更新、运行策略） |
| [fix-checks/](fix-checks/) | 聚焦探针（含失败断言与 q10 半事实断言）及 R1/R2 两份输出 |
| 归档 | `rev1/`、`rev2/`、`data/…/rev1/`、`midway-20261004-v1_1-draft/`、`archive-v1_2-rev2base/`（均只读） |

## 关键结果（K=5，可答题 n=20，dataset v1.3）

| 模式 | Recall@5 | Hit@5 | MRR@5 | v1.2→v1.3 |
|---|---|---|---|---|
| BM25 | **0.725** | **0.750** | **0.600** | 无变化 |
| Dense (BGE 本地) | 0.700 | 0.700 | 0.443 | MRR 0.452→0.443（仅 q13） |
| Hybrid (RRF) | 0.700 | 0.700 | 0.542 | 无变化 |

- 不足题 4 题单独分母：空检索率 0.000（2 未记载 + 2 准入排除，非「拒答率」）。
- 与 T027 合成指标**分表对照、不合并分母**；本基线为开发集检索基线，**不是正式校园准确率**；Hit/MRR 不是整题答对率。
- q10 跨度补齐后重计分分数不变、q13 题面限定后 dense MRR 下降，均原样记录，**不主张检索能力改进、不以得分为标准设计标注**。

## 验证摘要（详见 verification.md）

- 最终校验器正向一次：CHECK OK（24 题/57 证据/38 项），exit 0（冻结校验代码本轮未改，未重复缺节/漂移矩阵——R1 日志仍有效）。
- q10 半事实探针：8 断言全过（半命中 recall 0/f1 未覆盖；完整跨度 recall 0.5/f1 覆盖）；探针汇总断言使失败返回非零（本轮曾实测断言失败路径 exit 1）。
- q13 子集三模式 exit 0；合并重计分 exit 0；72/72 排名与来源逐项一致、22 题×3=66/66 未变题分数零漂移；q05 计分回归与 q11 手算维持一致。

完成后停止，等待 Astra 验收。T031 未发布。
