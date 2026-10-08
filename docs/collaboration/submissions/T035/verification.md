# T035 验证记录（verification.md，submission_revision=2）

> 本轮（T035-R1）仅做返工单允许项：链接/路径、秒数合计、已存数值、源码命令写入位置与历史证据范围核对。**未运行两实验脚本、浏览器、模型、全量测试**；命令真实执行、退出码实测。

## 0. T035-R1 轮核对（2026-10-08）

| 核对项 | 结果 | 退出码 |
|---|---|---|
| 归档 revision 1（delivery 8 件 + submission 5 件 → `archive-t035-rev1/`、`rev1/`） | **13/13 SHA-256 字节一致**；T028 归档与 rev1 历史未覆盖 | — |
| 交付包 8 个 md 相对链接解析 | **10/10 存在** | 0 |
| defense-script 秒数预算表合计 | [30,20,140,120,130,50,50,20] = **560 秒** ∈ [480,600]，与正文「合计 560」及 README/human-review 表述一致 | 0 |
| 已存机器数值在文档（T030 dense/hybrid MRR、T034 三分支 MRR、T031 selection MRR 等 6 项） | 逐值在 thesis-outline/experiment-index 表中 | 0 |
| 源码写入位置核对（**只读，未执行脚本**） | `evaluate-source-selection.py`：`--out` 存在（L64/L163–165）但 **freeze.json 固定写 EXP_DIR**（L191–192）；`evaluate-overlap-chunks.py`：**frozen-config.json（L155）/experiment.json（L387）固定写 EXP_DIR，无输出参数** ——与修复后 windows-runbook §4/evidence-matrix 说明一致 | 0 |
| 历史证据范围核对 | defense-script 逐操作标注与 T029-R2/T031-R1/T031-R2/T032-R1/T033-R1 各评审范围一致；T032-R1 明示未复验项（提醒日期、模板逐条原文跳转）已改标 `[代码/桩]`/`[现场待核验]` | — |
| 八件旧状态全扫（留待接入/待提供/默认关闭/时长/分母） | 无残留（README、human-review 的时长表述已同步预算口径） | 0 |

## 1. 修复后文档与源码/产物的一致性声明

| 文档主张 | 依据 |
|---|---|
| 两实验脚本会覆盖既有实验/冻结文件；source-selection 的 --out 不保护 freeze.json | 源码写入点（上表）；**未实测覆盖行为**（按 R1 要求不运行破坏性探针） |
| 主线 560 秒预算、/ask 显式整理依据后出现入口 | 文档操作顺序核对（ask.html 入口仅在问答结果区）；本轮无浏览器演练 |
| 表 6-2/6-3/6-4 数值 | 已存机器产物（T030 results、T031/T034 experiment.json）核对，未重算 |
| T034 勘误四则 | `T034-doc-errata.md`（revision 1 起保留，本轮未改） |

## 2. revision 1 轮验证（历史记录）

链接 10/10、serve-corpus/chunk `--help` 对照、机器指标逐值核对、主流程抽查 3 处（详见 `rev1/verification.md`）；T034 四项勘误、实验分表、reference 定位、planner partial、人工未复核口径经 R1 确认保留。

## 3. 未验证项（如实）

- 两实验脚本未运行（会覆盖历史证据；禁止在当前工作区例行执行）。
- 浏览器未补测；defense-script 中 `[现场待核验]` 步骤（提醒日期、逐条原文跳转、首页状态页、检索侧空态、语音录音等）未现场执行。
- 人工审定（24 题 gold、模板语义/现行性）仍为**未复核**（human-review-pending.md，不代签）。
