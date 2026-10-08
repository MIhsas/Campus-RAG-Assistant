# T030 验证记录（verification.md，submission_revision=2 / dataset v1.2）

> 所有命令在 Windows（Git Bash）下由后端 `.venv\Scripts\python.exe` 真实执行；下表退出码均为实测。未运行项在文末明确标注。工作目录如未说明为 `step2_code/backend`。

## 1. 标注与冻结校验

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python scripts/check-real-eval.py --pack ../../data/corpora/sicau-rag-pilot-v1.1 --questions ../../data/evaluations/sicau-rag-pilot-eval-v1/questions.json --freeze ../../data/evaluations/sicau-rag-pilot-eval-v1/freeze.json` | `CHECK OK: 24 题 / 57 条证据（契约、引句、准入、事实分组）；冻结哈希核对 38 项（dataset/corpus/implementation/model/annotation）` | 0 |

- quote==解析块切片逐字一致、span 合法、document_sha256/parser_version 与冻结包一致、每条 gold 通过本题条件准入、fact 分组规则（组内 OR/组间 AND、不足题带 missing）全部通过。
- freeze v1.2：frozen_at=2026-10-07；questions_sha256=`799ed1c112d0b89f12491087677d8b33c01d3105498cafaa061c878b198ca1a7`；annotation-check.md 哈希已随单冻结；38 项 = 1 题集 + 1 manifest + 20 语料 + 11 实现 + 4 模型身份 + 1 标注说明。

## 2. 聚焦回归（fix-checks/focused-probe.py，输出全文见 fix-checks/focused-probe-output.txt）

| 场景 | 期望 | 实测退出码 | 结论 |
|---|---|---|---|
| 真实 freeze（正向） | 0 | 0 | 通过 |
| 缺 dataset / corpus_pack / implementation_sha256 / embedding_model / annotation_files（各一） | 1 | 5 场景均 1 | 明确 FAIL，无「零项通过」 |
| corpus_pack.files 空清单 | 1 | 1 | `FAIL: freeze.corpus_pack.files 缺失或为空清单` |
| 单点哈希漂移：语料文件 / 实现文件 / 模型身份 / 标注说明 / 题集 / manifest（参数化各一） | 1 | 6 场景均 1 | 分类 FAIL 行正确（含路径） |
| Astra 错哈希探针复跑 `python docs/collaboration/reviews/T030-audit.py` | 0 且 wrong_hash_rejected=True | 0 | submitted exit=0；wrong_questions_hash exit=1（`FAIL: freeze: 题集 questions_sha256 与实际文件不符`）；`wrong_hash_rejected= True`（输出存 fix-checks/astra-probe-rerun.txt） |

- 探针为只读+隔离副本（改写 freeze 副本存 `.cache/t030-r2/focus-freeze/` 与 `.cache/astra-t030/`），未改产品、未覆盖历史 audit-v1 证据。

## 3. q05 替代源计分回归（同排名、两套 gold 对照；focused-probe.py 第 4 节）

| 模式（rev1 已存排名） | rev1 gold（2 源）R/H/M | v1.2 gold（5 源）R/H/M |
|---|---|---|
| BM25 | 1.0/1.0/1.0 | 1.0/1.0/1.0 |
| Dense | 1.0/1.0/**0.2** | 1.0/1.0/**0.5** |
| Hybrid | 1.0/1.0/**0.333…** | 1.0/1.0/**1.0** |

与 Astra 反事实探针数字一致（Dense MRR 0.2→0.5、Hybrid 1/3→1）——旧 MRR 失真由漏标引起，非算法弱点。

## 4. v1.2 重检索与合并（最小范围）

| 命令（`python -m campus_assistant.evaluation.run …--questions .cache/t030-r2/questions-v1_2-changed-subset.json`） | 输出 | 退出码 |
|---|---|---|
| `--mode bm25` | `results/rerun-v12/bm25.json`（valid=true） | 0 |
| `--mode dense --model-path models/bge-small-zh-v1.5` | `results/rerun-v12/dense.json`（valid=true） | 0 |
| `--mode hybrid --model-path models/bge-small-zh-v1.5` | `results/rerun-v12/hybrid.json`（valid=true） | 0 |
| `python scripts/eval-v2-rescore.py …`（20 题已存排名重计分 + 4 题 rerun 合并） | `results/{bm25,dense,hybrid}.json` + `results/rescore-v12.json` | 0 |

- 子集输入=4 题（q06/q13/q18/u04，v1.2 题面变化题）；BGE 为本地 `models/bge-small-zh-v1.5`，一次加载，无下载/联网。
- 合并工具为既有 `scripts/eval-v2-rescore.py`（**未修改**；其内置 note/merge_note 字样含「T027-R2」模板标签，实际合并口径以 rescore-v12.json 的 changed_for_rerun 与本记录为准）。
- **排名来源一致性核验**（独立脚本，对照 rerun-v12/rerun/rev1 三代来源）：72/72 条 hit_summary 逐项一致；gold 未变题 54/54 分数三元组零漂移；预期 gold 变更分差 5 处（q05 dense/hybrid、q10×3）全部可解释，无其他差异。

## 5. 最终指标（K=5，n=20）

BM25 0.725/0.750/0.600；Dense 0.700/0.700/0.452；Hybrid 0.700/0.700/0.542（Recall/Hit/MRR）。两题手算（q11 四事实 AND 覆盖、q05 OR 补源对照）与机器输出一致，见 evaluation-report §6。

## 6. 未运行/未验证项（如实标注）

- 未重跑：20 题全量三模式检索（按 R1 仅变更题重检索，其余复用排名）；全量 pytest；UI/ASR/Agent；性能/安全压力测试。
- 未验证：人工逐题复核（状态=未复核，不代签）；24 题 gold 的教师/学生确认；运行次数与冻结时点先后的第三方证明（时间戳仅文件系统记录）。
- 未做：外部模型调用、下载/安装、commit/push、产品算法修改、旧 gold 修改。
