# T039 验证记录（verification.md，submission_revision=1）

> 命令真实执行、退出码实测。必要验证仅限任务书范围；**未重跑 UI/ASR/Agent/全量/T030 缺节漂移矩阵**；零外部调用。

## 1. 新契约/跨度/准入与冻结校验（一次）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python .cache/t039/build-v2-questions.py` | 24 题/58 证据；仅 6 题允许字段变更（u03/u04/q08/q10/u01/u02）；**意外字段漂移=0**；meta（schema_version/split/is_synthetic/metric_semantics）不变 | 0 |
| QuestionDataset 契约校验 + u03 逐源准入（parse_manifest v1.2 + compute_allowed_document_ids） | 契约 OK（21 可答/3 不足）；u03 gold 源 bed3ac **准入**、span==quote 逐字 OK、db05e0 **排除** | 0 |
| `python scripts/check-real-eval.py --pack …v1.2 --questions …v2/questions.json --freeze …v2/freeze.json` | `CHECK OK: 24 题 / 58 条证据；冻结哈希核对 37 项` | 0 |

freeze.json 五节 schema；实现 hash=**当前实际文件**（chunk.py/filters.py 含 T034/T038 变更，非 T030 旧值）；模型身份=本机 BGE 配置文件。

## 2. 三模式本轮原始输出（既有 CLI，各一次）

```
python -m campus_assistant.evaluation.run --manifest …v1.2/manifest.json --corpus-root …v1.2 --questions …v2/questions.json --top-k 5 --mode {bm25,dense,hybrid} --model-path models/bge-small-zh-v1.5
```

| mode | valid | n | R / H / M | exit |
|---|---|---|---|---|
| bm25 | true | 21 | 0.7380952380952381 / 0.7619047619047619 / 0.6190476190476191 | 0 |
| dense | true | 21 | 0.7142857142857143 / 0.7142857142857143 / 0.46984126984126984 | 0 |
| hybrid | true | 21 | 0.7142857142857143 / 0.7142857142857143 / 0.5634920634920635 | 0 |

完整 JSON+stderr+exitcode 存 `results/`；无 document_id/候选/生成/Agent；每 mode 独立构建索引（未改框架）。

## 3. 聚合/分组一致性与共同子集

| 检查 | 结果 |
|---|---|
| aggregate.json 重算 | 由本轮 results/*.json 完整输出计算（未复制旧 summary_by_type/group）；不足 n=3 空检索率三模式 0.000 |
| 共同子集（原 20 可答） | R/H/M 与 T030 存储**逐值一致**；**60/60（20×3）命中序列与分数逐项一致**（排名变化=无） |
| 两例手算 | u03：单源 OR、[0,452)⊇[101,129)、rank1、MRR 1.0 ✓；q10：f1×7 OR、f2×7 OR、组间 AND、两前提不判冲突 ✓ |

## 4. 旧输入/实验/用户意见不变（前后 SHA）

| 文件 | SHA | 结论 |
|---|---|---|
| v1.1 manifest / v1.3 questions / v1.3 freeze | `34e182f1…` / `5fde70a3…` / `fd2f2476…` | 未变 |
| 模板 v1.2 / T031 / T034 实验 | `78f1c1d9…` / `57b22f93…` / `cef9f162…` | 未变 |
| 用户意见记录 | `2e1af149…` | 未变 |

**7/7 未变**。新产物身份单列：v2 questions `4e39229e…`、freeze `8c289b2a…`、aggregate `fcecdc9c…`。

## 5. 文档整理核对

- review-supplement.md 四项齐（原意见/处置/逐字引用/示例释义标注「非产品实时生成」/待确认）；未要求重确认模板 33 项；无代签。
- T038-doc-errata.md：步骤 5 事实更正（18 份准入/5 条命中/83eb 排除）+ 浏览器证据归属 Astra。
- README：v1.2 正斜杠引号命令（含空格路径）+ v1.1 历史命令保留；human-review-pending 过时表述修正（用户意见已接收/模板确认/开放与新改待复核/现行性未认证）。

## 6. 未验证/边界

- 未跑：UI/ASR/Agent/全量/浏览器；产品算法/评分器/筛选/provider 未改。
- 新基线不代表校园 QA 准确率/可靠拒答/新盲测；示例释义不代表 DeepSeek 生成正确回答；新修订**待定向人工复核**；学校现行性未认证。
