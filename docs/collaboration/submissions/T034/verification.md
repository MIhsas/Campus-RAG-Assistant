# T034 验证记录（verification.md，submission_revision=1）

> 命令在 Windows（Git Bash）下真实执行；退出码实测。范围=chunk 与受影响检索/评测聚焦测试 + 对照实验；未跑 UI/ASR/Agent/全量。

## 1. 新增业务回归（tests/test_chunk_overlap.py，任务指定四项 + 参数校验）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python -m pytest tests/test_chunk_overlap.py tests/test_corpus_chunk.py -q` | **63 passed**（新 9 + 既有 54） | 0 |

- **默认字节/ID 兼容**：golden chunk ID `5d015d30…` 与历史一致；默认 chunk 字段集合与旧 schema 逐键相同（无新字段）；`overlap_chars=0` 显式与缺省结果一致。
- **重叠跨度逐字与尾窗终止**：每窗 text==原块 [start,end) 切片；950 字→(0,500)(400,900)(800,950) 恰好 3 窗；900 字→(0,500)(400,900) 无冗余尾窗。
- **跨硬边界事实**：构造 gold 跨度 [480,560)——baseline 无单块完整覆盖（断言成立），candidate 窗口完整覆盖（断言成立）。
- **table_row 不变**：重叠下仍一窗、不切分、cells/跨度不变。
- 参数校验：负值/≥max_chars/非整数/bool 均 ValueError。

## 2. 受影响检索/评测聚焦测试

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python -m pytest tests/test_evaluation.py tests/test_evaluation_v2.py tests/test_retrieval_bm25.py tests/test_run_entry.py -q` | **98 passed**（评分口径未改） | 0 |

## 3. 对照实验（scripts/evaluate-overlap-chunks.py，exit 0）

| 项 | 实测 |
|---|---|
| 跑前冻结 | `frozen-config.json`：参数/输入哈希（questions `5fde70a3…`、manifest `34e182f1…`）/实现哈希/BGE 身份/T030 结果身份（questions_sha256 逐一核对一致） |
| 基线兼容 | **BM25 未改窗口路径 24/24 逐题命中序列与 T030 v1.3 存储排名一致**（不一致=0，未覆盖基线） |
| 候选编码 | Dense/Hybrid 共享同次候选编码（1233 块一次，31.9s，本地 BGE）；baseline 排名复用存储结果未重编码 |
| 聚合（n=20） | BM25 0.725/0.750/0.600→0.725/0.750/0.596；Dense 0.700/0.700/0.443→0.675/0.700/0.467；Hybrid 0.700/0.700/0.542→0.700/0.700/0.583 |
| 不足 n=4 | 双分支空检索率 0.000（未称拒答率） |
| 边界事实 | 2 处（q10 f1-s7、q20 f1-s2）：候选源可覆盖性改善，question 级 Recall 未变（OR 组已满足） |
| 回退 | 3 处（q11 dense Recall 1.0→0.5；q10 dense MRR 1.0→0.5；q17 bm25 MRR 0.333→0.25，后者伴随同块重叠重复命中 1 对） |
| 重复区间 | candidate top5：BM25 4/24、Dense 3/24、Hybrid 3/24 题有同块/重叠命中（各 4 对重叠区间） |
| 无改善 | 72 对比行中 65 行双分支指标完全相同 |
| 失败记录 | 首轮脚本分组聚合混入不足题 None 崩溃（TypeError），修正后重跑成功；首轮未写盘、无旧数据被覆盖 |

逐题原始输出（双分支 R/H/M、命中文档块区间、覆盖证据、事实可覆盖性、重复统计）见 `data/evaluations/sicau-rag-overlap-v1/experiment.json`。

## 4. 复现命令

```powershell
# step2_code/backend 下；单次运行即全部结果（无随机性）
& .\.venv\Scripts\python.exe scripts\evaluate-overlap-chunks.py
# 聚焦回归
& .\.venv\Scripts\python.exe -m pytest tests/test_chunk_overlap.py tests/test_corpus_chunk.py -q
```

## 5. 未运行/未验证（如实）

- UI/ASR/Agent/全量 pytest、显著性检验（单次实验）；「整题回答正确/答案质量」不在实验评价范围。
- 默认行为**未切换**（overlap 仍为 0）；overlap 仅为显式可选参数。
- 原语料/历史实验（T030-T033）/模板/Astra 记录只读未改；无外部调用、下载/安装/commit/push。
