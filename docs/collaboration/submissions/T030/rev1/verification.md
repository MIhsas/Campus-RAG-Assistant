# T030 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。零外部模型调用、无下载/安装、未 commit/push；未改产品算法/旧 gold/已验收包。验证重点=标注可复现、结果可复查、分析有据。

## 1. 标注与冻结（评测前）

```bash
./.venv/Scripts/python.exe scripts/check-real-eval.py --pack …/sicau-rag-pilot-v1.1 --questions …/questions.json
# CHECK OK: 24 题 / 37 条证据（契约、引句、准入、事实分组）  退出码 0
# freeze.json 随后保存（题集/manifest/20 文件/11 实现文件/BGE revision+配置哈希；含拟题来源与人工复核状态=未复核）
```

- 引句逐字=解析块切片（37/37）；每条 gold 通过本题 conditions 准入（产品 T011 规则）；不足题必带 `missing` 且无 evidence；可答题每题 ≥1 fact、每 fact ≥1 源。
- 事实分组语义核对见 `data/evaluations/sicau-rag-pilot-eval-v1/annotation-check.md`（q01/q02 五源等价、q10 两事实非替代、q14/q15 版本约束等逐条依据）。

## 2. 三模式运行（各一次，冻结后）

```powershell
# 工单命令（PowerShell）等价执行；输出 stdout JSON→results/<mode>.json，stderr→<mode>.stderr.log，退出码→<mode>.exitcode.txt
& .\.venv\Scripts\python.exe -m campus_assistant.evaluation.run --manifest …\manifest.json --corpus-root … --questions …\questions.json --top-k 5 --mode bm25
# dense / hybrid 同命令加 --model-path models\bge-small-zh-v1.5
```

- 退出码：bm25=0、dense=0、hybrid=0（exitcode.txt 三份）。
- 结果内 `questions_sha256=a9f284b0…`、`manifest_sha256=34e182f1…` 与 freeze **一致**；`truncated_chunk_count=0`（dense/hybrid）；索引块数与分段耗时记录于各 JSON（单次耗时非性能结论）。
- 汇总（K=5，n=20）：BM25 0.633/0.650/0.483；Dense 0.633/0.650/0.391；Hybrid 0.683/0.700/0.421。不足题空检索率 0.000（未记载 2 + 准入排除 2）。

## 3. 手算对照（evaluation-report §5）

- 多事实 q11（BM25）：f1/f2 覆盖、f3 未入 top5 → 2/3=0.667；rank1 相关 → Hit 1.0、MRR 1.0——与机器 `0.667/1.0/1.0` **一致**。
- 等价来源 q01（Dense）：五源 OR 命中任一源即满足 f1 → 1/1=1.0（分母=事实数）；rank1 相关 → MRR 1.0——与机器 `1.0/1.0/1.0` **一致**。

## 4. 冻结后未改动核对

- freeze 后未改题/未调参/未重跑（三模式各恰一次）；`check-real-eval.py --freeze freeze.json` 可复核（文件哈希口径）。
- T029 勘误按冻结 manifest：ddf41747 日期 null（不据旧说明补写）、57c0945c effective=2013-01-01——u03 准入排除判定即基于此。

## 5. 真实核查 / 未运行

**真实核查**：§1—§4 本轮实际执行（校验/冻结/三模式/手算）。
**未运行**：UI/ASR/Agent/全量测试（默认无产品代码变更，仅新增 check-real-eval.py 校验工具）；未重复向量编码（每模式一次）；无浏览器实操（如需浏览器复核交 Astra）。
**未验证**：正式校园准确率（24 题开发集、人工未复核）；可靠拒答（不足题空检索率 0）；统计显著性。

## 6. 依赖

未安装新依赖；未联网；BGE 本地加载（revision `7999e1d3…`）；新增仅 `scripts/check-real-eval.py`（复用 QuestionDataset/parse/filters）。
