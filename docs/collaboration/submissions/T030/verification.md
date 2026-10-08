# T030 验证记录（verification.md，submission_revision=3 / dataset v1.3）

> 所有命令在 Windows（Git Bash）下由后端 `.venv\Scripts\python.exe` 真实执行；退出码均为实测。未运行项在文末明确标注。本轮（T030-R2）验证范围按返工单：最终校验器正向一次、q10 半事实探针、q13 子集结果、未变题一致性、更新手算；**未重复缺节/漂移矩阵**（冻结校验代码未改，R1 日志 `fix-checks/focused-probe-output.txt` 仍有效）。

## 1. 归档与冻结（v1.2 → v1.3）

| 动作 | 结果 |
|---|---|
| 归档 v1.2 基线 → `data/…/archive-v1_2-rev2base/`（题集/freeze/标注说明/results 28 文件）+ `submissions/T030/rev2/` 七件 | 逐一 SHA-256 字节核验 **10/10 一致**；rev1 与 midway 归档未触碰 |
| 重新冻结 `freeze.json` v1.3 | frozen_at=2026-10-07；questions_sha256=`5fde70a332744b642e48014abc82902009abc1a106a84e6241b3c460e4faed5c`；annotation-check 哈希 `8d391b62…`；38 项（1 题集+1 manifest+20 语料+11 实现+4 模型身份+1 标注说明） |
| 最终校验器正向：`python scripts/check-real-eval.py --pack …--questions …--freeze …` | `CHECK OK: 24 题 / 57 条证据（契约、引句、准入、事实分组）；冻结哈希核对 38 项`，**exit 0** |

## 2. q10 半事实探针与聚焦断言（fix-checks/focused-probe.py，输出 `focused-probe-r2-output.txt`）

脚本本轮升级：每场景带期望断言、任一失败即 exit 1；新增第 5 节 q10 半事实断言；`--skip-matrix` 跳过缺节/漂移矩阵。

| 断言组 | 期望 | 实测 | 结果 |
|---|---|---|---|
| real-freeze-exit | 0 | 0 | OK |
| q05 计分回归（bm25/dense/hybrid × rev1/当前 gold 两套） | 1.0/1.0、0.2/0.5、0.333/1.0（MRR） | 逐项一致 | 6/6 OK |
| q10 f1-s6/f1-s7 半命中（仅导师50%） | recall=0.0 且 f1 未覆盖 | 0.0 / False | 4/4 OK |
| q10 f1-s6/f1-s7 完整跨度（含答辩50%） | recall=0.5 且 f1 覆盖 | 0.5 / True | 4/4 OK |

- 汇总：**15 checks / 0 failures / PROBE OK，exit 0**。
- 断言失败路径有效性实测：首轮因期望值未四舍五入触发 `FAIL` 并 **exit 1**（PROBE FAILED），修正比较逻辑后通过——证明未来复用时失败能返回非零。
- R1 矩阵结果（缺 5 节/空清单 6 场景 exit 1、单点漂移 6 类 exit 1、Astra 探针 wrong_hash_rejected=True）保留在 `focused-probe-output.txt` 与 `astra-probe-rerun.txt`，本轮未重复执行。

## 3. q13 三模式子集重检索（仅本题，题面条文限定后）

| 命令（`python -m campus_assistant.evaluation.run …--questions .cache/t030-r2/questions-v1_3-q13-subset.json`） | q13 R/H/M | 退出码 |
|---|---|---|
| `--mode bm25` → `results/rerun-v13/bm25.json` | 1.0/1.0/1.0 | 0 |
| `--mode dense --model-path models/bge-small-zh-v1.5` | 1.0/1.0/0.333 | 0 |
| `--mode hybrid --model-path models/bge-small-zh-v1.5` | 1.0/1.0/1.0 | 0 |

- 输入为 q13 单题子集（结果 JSON 的 questions_sha256 为子集指纹；合并输出携带全量 v1.3 指纹）。

## 4. 合并重计分与一致性核验

| 项 | 结果 |
|---|---|
| `python scripts/eval-v2-rescore.py …`（23 题已存排名重计分 + q13 rerun 合并）→ `results/{bm25,dense,hybrid}.json` + `rescore-v13.json` | exit 0；`rescored: 23 \| rerun: ['q13']` |
| 排名来源一致性（q13 vs rerun-v13；其余 vs `archive-v1_2-rev2base`） | **72/72 逐项一致** |
| 未变题（22 题×3）分数一致性 | **66/66 零漂移** |
| 预期变化 | 仅 q13 dense MRR 0.5→0.333；**q10 重计分分数不变**（三模式 R/H/M 与 v1.2 相同，如实记录） |
| 分组字段一致性 | 合并工具不重算 `summary_by_type/summary_by_filter_group`（脚本未改，字段曾为源运行遗留值）；已按 run.py 同一聚合口径对合并产物补算两组字段并加 `group_summary_note`，与逐题数据一致（如 dense multi_fact MRR=0.583=(1.0+1.0+0.0+0.333)/4） |

## 5. 最终指标与手算（K=5，n=20）

BM25 0.725/0.750/0.600；Dense 0.700/0.700/0.443；Hybrid 0.700/0.700/0.542（Recall/Hit/MRR）。手算（evaluation-report §6）：q11 四事实 AND 覆盖、q05 双 gold 对照、q10 半事实对照（半命中 Recall 0 / 完整 0.5）均与机器输出一致。

## 6. 未运行/未验证项（如实标注）

- 本轮未重复：缺节/哈希漂移矩阵、Astra 探针复跑、20 题全量三模式检索、全量 pytest、UI/ASR/Agent、性能/安全压力测试。
- 未验证：人工逐题复核（状态=未复核，不代签）；运行次数与冻结时点先后的第三方证明。
- 未做：外部模型调用、下载/安装、commit/push、产品算法修改、旧 gold 修改、Astra 文件修改。
