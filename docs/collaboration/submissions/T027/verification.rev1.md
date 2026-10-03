# T027 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。按任务书只做：指标手算对照（多证据与不足题各一）+ 新题集校验 + 三模式一次正式运行 + 评测聚焦回归。**零外部模型调用、无下载、无安装**；未跑前端/ASR/agent/全量；未改产品算法。

## 1. 新题集校验

```bash
# schema + 材料不足题 missing 必填 + 冻结哈希（首次正式评测前）
./.venv/Scripts/python.exe - <<'PY'  # 校验并冻结
# schema OK: eval-v2-synthetic 1.0 | questions: 24；answerable 20 / unanswerable 4
# missing field check OK；questions_sha256=0d58ed95…、manifest_sha256=4fa135dd…
# 退出码：0 → dataset-hashes.json
```

- `scripts/build-eval-v2.py assemble`：13 文档组装（11 份既有夹具逐字节拷贝哈希一致 + 2 份新干扰文档）；`dump-blocks`：**valid 语料 52 块**。
- `fill-spans`：**23/23 条证据跨度**按原文子串精确定位（不唯一/缺失即报错）；运行内来源校验（文档哈希/解析版本/跨度/quote 逐字）全过（`results/*.json` errors=[]）。
- 独立性：标注仅用原文块（blocks-dump/blocks-text 留档），未从检索结果反推（gold-review 第 1 节）。

## 2. 三模式正式运行（一次）与聚合

```bash
./.venv/Scripts/python.exe -m campus_assistant.evaluation.run --manifest examples/evaluation-v2/corpus/manifest.json --corpus-root examples/evaluation-v2/corpus --questions examples/evaluation-v2/questions.json --top-k 5 --mode bm25 > results/bm25.json        # EXIT=0
# 同命令 --mode dense / --mode hybrid --model-path models/bge-small-zh-v1.5              # EXIT=0 / 0
./.venv/Scripts/python.exe scripts/eval-v2-compare.py --questions … --results bm25 dense hybrid …  # EXIT=0
```

- 三模式同 `questions_sha256=0d58ed95…`、`manifest_sha256=4fa135dd…`、top_k=5（合并脚本断言）；Dense/Hybrid 模型 `bge-small-zh-v1.5` rev `7999e1d3…`、`truncated_chunk_count=0`。
- 聚合（K=5，n=20）：BM25 R0.950/H1.000/M0.867；Dense 0.800/0.850/0.578；Hybrid 0.950/1.000/0.795。不足题 n=4 单独分母（三模式 empty_rate=0、with_results=4）。
- 计时仅分段记录（索引构建 vs 查询，dense 索引 12.4s / 查询 0.24s 量级），注明非统计稳定性能。

## 3. 指标手算对照（evaluation-report 第 5 节详列）

- **多证据 v2-q11（BM25）**：金标准 2 跨度被 rank1 chunk 完整覆盖 → Recall 2/2=**1.0**、Hit=1、MRR=1/1=**1.0**；机器 `recall=1.0 hit=1.0 mrr=1.0` —— **一致**。
- **不足题 v2-q24（BM25）**：gold 空 → recall/hit/mrr 不计算（None，不入分母）；returned_count=5 计入有结果数；机器 `recall=None`、聚合 `with_results=4/empty_rate=0.0` —— **一致**。

## 4. 聚焦回归（77 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_evaluation.py tests/test_evaluation_cli.py tests/test_evaluation_v2.py -q -p no:cacheprovider --basetemp .cache/t027-tests3 --tb=short -rs
# 77 passed in 10.29s
# 退出码：0
```

- 新增 `test_evaluation_v2.py`（4）：旧 8 题仍合法（无新字段亦过）、v2 字段/类型/missing 校验、**同题不同筛选准入断言**（q16 命中不含 fd-2025、q17 不含 fd-2024）、不足题不入 recall 分母。
- 既有 73 项全过；`TestDeterminism` 整字典对比排除 `timing_seconds`（分段耗时天然非确定且不作性能结论——唯一测试适配，见下）。

## 5. 旧 8 题兼容检查

```bash
./.venv/Scripts/python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --top-k 5 --mode bm25
# EXIT=0；valid=True，8 题（6 可答 + 2 不足），summary R1.0/H1.0/M0.9167，errors=[]
```

旧集运行正常、历史记录未篡改；旧 `examples/evaluation/` 目录零改动（changed-files 可核）。

## 6. 测试适配说明（唯一既有测试改动）

`tests/test_evaluation_cli.py::TestDeterminism` 原对两次运行输出做整字典相等比较；run.py 新增 `timing_seconds`（分段耗时，天然非确定）后失败。适配为比较前剔除该字段（其余输出仍逐字节一致）。**指标口径、旧结果、产品算法均未改动**；不为得分调参。

## 7. 未验证项

1. 真实学校语料效果（数据全合成）；统计显著性（单次运行、小样本，未做检验）。
2. 生成/规划质量不在本实验范围（证据类别分开，见 experiment-methods 第 7 节）。
3. 速度结论不成立（计时仅分段记录）。
