# evaluation-v2：检索对照合成评测集（T027）

**全部合成资料，不代表真实教务政策，未经真实校园质量验证。**

## 文件

- `questions.json` — 24 题（20 可答 + 4 材料不足），dataset `eval-v2-synthetic` v1.0；含题型/条件/判定理由/缺什么标注（`authoring_note` 如实声明模型辅助编写）。
- `corpus/` — 13 份合成文档（含 2 份明显标注的干扰文档），组合既有合成夹具的逐字节拷贝 + 新增干扰资料；`manifest.json` 为评测语料清单。

## 标注口径

金标准按原文独立标注，跨度 `[char_start, char_end)` + 逐字 quote，不从检索结果反推；twin/近义干扰保守约定与人工复核清单见
`docs/collaboration/submissions/T027/gold-review.md`。数据/标注哈希冻结记录见同目录 `dataset-hashes.json`。

## 与旧题集的关系

旧 8 题基线 `examples/evaluation/` **完整保留、未改动**（兼容检查通过）。本目录为独立新评测集。

## 构建与运行

`scripts/build-eval-v2.py`（assemble/dump-blocks/fill-spans）可复现语料与跨度定位；
`-m campus_assistant.evaluation.run` 三模式运行、`scripts/eval-v2-compare.py` 对照聚合；
可复制命令见 `docs/collaboration/submissions/T027/evaluation-report.md` 第 8 节。
