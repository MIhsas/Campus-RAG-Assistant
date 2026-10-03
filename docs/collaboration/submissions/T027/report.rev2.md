# T027 检索对照评测与论文证据包 — 实施报告（revision 2）

身份：task_id=T027、task_revision=v1、**submission_revision=2、responds_to=T027-R1**、status=ready_for_review、**external_model_calls=0**、planner_live_verified=false、tinyagent_integration_kind=reference。**数据版本 1.0→2.0（指标语义 fact_group_or_v1.1）**；rev1 题集/gold/哈希/结果/报告完整保留（`rev1/` 与 `*.rev1.*`）。零外部调用、无下载、无安装；未改检索算法/参数、旧 `examples/evaluation`、原语料、模板、`metrics.py` 既有跨度规则。

## 概述（含 T027-R1 返工）

T027 v1 建立独立合成评测集（24 题/13 文档）并完成三模式对照。T027-R1 返工修正金标准口径：**撤销 twin 排除约定**，全量复核可接受证据并引入**可替代证据组**（组内 OR、组间 AND，重复来源不稀释分母）；**q12 版本歧义题面消歧**（q20/q21 同步渠道消歧）；gold-only 变化用已存排名重计分、题面变化重跑检索（一致性零偏差交叉核对）；报告区分实测观察与原因假设。详见 `fix-report.md` 与 `gold-revisions.md`。

## 功能交付（对照任务书 + 返工单）

1. **数据与标注（v2.0）**：24 题（20 可答+4 不足，七类题型，三组同题不同筛选对）；41 条来源跨度 → **23 个必要事实组**；修订 11 题（等价来源补齐 ×7、题面消歧 ×3 兼及 q21、q10 两事实组重排），13 题复核不变。gold 按原文独立制定/修订（未从检索结果反推），修订前后哈希冻结记录（`dataset-hashes.rev1.json` / `dataset-hashes.json`）。语料不变（11 份既有夹具逐字节拷贝 + 2 份明显标注干扰文档）。
2. **评测管线**：`evaluation/models.py` 增 `Evidence.fact_id`/`revision_note`/`metric_semantics`（向后兼容，旧 8 题行为逐项验证不变）；`metrics.py` 事实分组覆盖（跨度完整覆盖规则保留，recall 分母=事实数）；`run.py` 显式输出 `metrics_semantics`/`recall_definition` + 既有筛选/分组聚合/分段计时。新增 `scripts/eval-v2-rescore.py`（已存排名重计分，标记需重检索题）。
3. **三模式对照（v2.0 重算）**：K=5 主口径 + K=3 补充；可答/不足分开分母。**实测（R/H/M@5）**：BM25 **0.950/0.950/0.925**、Dense 0.875/0.900/0.739、Hybrid **0.950/0.950/0.892**——**Hybrid 仍未显示整体优势**（MRR 略低于 BM25）。等价证据修正使 rev1 被误记的命中得到承认（Dense 修正最明显：q05/q15 MRR 0.5→1.0、q02/q16 R0→1.0）。
4. **可审阅报告**（`evaluation-report.md` rev2）：三模式对照（含 rev1→v2 变化列）、题型/筛选分组、**6 个案例**（等价首位计分 ×2、多事实部分覆盖、版本消歧失分如实、同题筛选准入、不足题有命中 + Hit 口径变化说明）、**手算对照**（q10 事实组 + q10 部分覆盖 + q24 不足题）、实测观察与原因假设分离、夹具警示语读法说明。
5. **论文实验方法草稿**（`experiment-methods.md` rev2）：事实组指标定义与分母、变量控制（修订先于重算冻结、不为模式调参）、观察/假设分离的发现与局限、T014/T025/本实验证据分表、真实资料替换/补测步骤。
6. **金标准复核清单**（`gold-review.md` rev2）：事实组口径、逐题速查（含等价来源数）、Astra 8 项抽查清单；`gold-revisions.md` 为标注修订清单（前后哈希、逐题理由、重算与一致性核验）。

## 验证摘要（真实命令见 verification.md）

- **聚焦测试 81 passed**（evaluation + cli + v2）：等价证据首位计分、多事实部分覆盖、替代来源不稀释分母、旧 8 题行为逐项一致、q16/q17 准入、不足题分母、q12/q20/q21 消歧断言。
- **指标手算对照 3 例**（q10 满分/部分覆盖、q24 不足）与机器输出一致。
- **一致性交叉核对**：21 题×3 模式「已存排名重计分」vs「全新重跑」零偏差；`changed_for_rerun=[v2-q12,v2-q20,v2-q21]` 按题面变化重跑，未混用旧哈希。
- **旧 8 题兼容检查**：summary 与 rev1 逐项一致（R1.0/H1.0/M0.9167）。

## 修改与新增文件（rev2 增量）

- 修改：`evaluation/models.py`（fact_id/revision_note/metric_semantics）、`evaluation/metrics.py`（事实分组）、`evaluation/run.py`（指标语义输出）、`examples/evaluation-v2/questions.json`（v2.0 修订）、`scripts/eval-v2-compare.py`（事实覆盖字段）、`tests/test_evaluation_v2.py`
- 新增：`scripts/eval-v2-rescore.py`
- 提交另附：`fix-report.md`、`gold-revisions.md`、`rescore-from-rev1.json`、`rev1/`（题集/哈希/结果存档）；四件更新 rev2
- 未修改：旧 `examples/evaluation`、语料夹具、`metrics.py` 跨度覆盖/Hit/MRR 规则、产品检索算法、Astra 文档

## 指标变化一览（rev1 → v2.0，K=5）

| 模式 | R@5 | H@5 | MRR@5 | 主要变化来源 |
|---|---|---|---|---|
| BM25 | 0.950→0.950 | 1.000→0.950 | 0.867→0.925 | 等价源修正↑；q12 消歧失分↓（Hit 唯一变化源） |
| Dense | 0.800→**0.875** | 0.850→**0.900** | 0.578→**0.739** | 等价源修正全面↑ |
| Hybrid | 0.950→0.950 | 1.000→0.950 | 0.795→**0.892** | 同上 |

完成后停止，等待 Astra 验收。T028 未发布。
