# T039-R1 续接进度（新执行窗口 MiMo）

日期：2026-10-09。执行环境：Windows 11，Git Bash（同机 `F:\Collage Paper`）。
解释器：`F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe`。
授权：仅 T039-R1（`docs/collaboration/reviews/T039-R1.md`）。本文件按小步骤追加更新。

## 继承进度（来自交接单与盘点快照，非本窗口实跑）

- 新差异检查器 `step2_code/backend/.cache/t039/check-field-diff.py` 与修正的 `data/evaluations/sicau-rag-pilot-eval-v2/field-diff.json` 已落盘；Astra 盘点实跑正向 exit 0、`q07:query` 隔离负向 exit 1（预期），本窗口不重复。
- `submissions/T039/review-supplement.md` 四项（q08/q10/u03/u04）已补齐；Astra 独立核对 8 条原引逐字一致、8 个本机原件路径存在。不重审 24 题/114 项，不再运行 build-review-supplement.py 覆盖。
- README v1.2 历史边界说明、human-review-pending 顶部/§2/§5、evaluation-report 分组表已更新；最终一致性收尾见步骤 2-3。
- revision 1 提交 7 件与旧 diff/helper 已归档至 `submissions/T039/rev1/` 与 `.cache/t039/archive-r1/`，不覆盖。
- 尚未完成（本窗口目标）：human-review-pending §0/§1 收尾、verification.md 命令修复与证据归属、fix-report.md、report/submission/changed-files 收尾、原 Astra audit 复跑一次、revision 2 提交。

## 本窗口实际步骤记录

### 步骤 1a：读取交接文档并核对文件身份（进行中）

已读：新窗口提示词、交接单 `handoffs/T039-R1-20261009-MiMo续接.md`、盘点快照 `handoffs/T039-R1-20261009-盘点.json`、返工单 `reviews/T039-R1.md`、STATUS.md、PROTOCOL.md。

命令（cwd=`F:\Collage Paper`，本窗口实际经 Git Bash 调用同一解释器）：

```text
python -c "<读取盘点.json，对 readonly/partial/rev1 三组逐文件比对 SHA256>"
# 结果：total checked: 38，drift_or_missing: 0，退出码 0
```

结论：23 只读文件、8 部分成果文件、7 件 rev1 归档与盘点快照全部一致，无漂移；`submissions/T039/` 当前无 fix-report.md / continuation-progress.md（本文件为新建），submission.json 仍 revision 1。git 脏文件为 T037—T039 累积修改，不作为本轮返工清单。

下一步：步骤 2 —— human-review-pending §0/§1 收尾、verification.md 修复。

### 步骤 2：human-review-pending 收尾（已完成）

`docs/delivery/human-review-pending.md` 定向修改两处：§0 改为「T036 首次意见对应历史包」（删除“当前包=T036-v3/日常入口”措辞，当前四项入口指向 T039 review-supplement）；§1 拆分「当前题集 v2.0」与「历史题集 v1.3」两行（不触碰旧文件）。链接保持 `../collaboration/...` 相对解析。未为文案重跑任何实验。

### 步骤 3：保全旧失败审计记录并复跑原 audit（提前于元数据收尾执行，便于结果一次写入终稿）

1. 复跑前 `cp reviews/T039-audit.json submissions/T039/T039-audit-rev1-failed-preserved.json`——保全旧失败历史（6 条差异不匹配的 revision 1 审计输出），SHA `41f043a2e069da80…` 与原件逐字节一致（探针设计为覆盖写 T039-audit.json）。
2. 命令（cwd=`F:\Collage Paper`，新窗口实际经 Git Bash 调用同一解释器与参数）：

```text
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\docs\collaboration\reviews\T039-audit.py'
# stdout: SCORES OK: 72 rows; common rankings/scores 60 ; fresh BM25 24 rows; group checks 36
# EXPECTED CHANGES: q08/q10=[rationale,revision_note]; u01/u02/u04=[missing,rationale,revision_note]; u03=[answerable,evidence,missing,question_type,rationale,revision_note]
# SUBMITTED DIFF MISMATCHES: 0
# stderr: 4 条 "Ignoring wrong pointing object" PDF 解析警告（原样出现，非失败）
# 退出码：0
```

3. 探针写入 `reviews/T039-audit.json`（status=ok）与 `reviews/T039-bm25-fresh.json`（新 SHA 前缀 `53e6f459…` / `049973d4…`）——原返工单明确要求的审计输出例外；探针源码/判据未改。内部一次 BM25 全 24 题与已存结果逐行一致；未编码向量、未调云模型、未覆盖 results/。

下一步：verification.md 终稿、fix-report.md、report/submission/changed-files 元数据收尾。

### 步骤 4：提交文档与 revision 2 元数据收尾（已完成）

- `verification.md` 重写终稿：修复转义损坏/缺引号命令（解释器、脚本、含空格参数分别加引号）；`bm25|dense|hybrid` 改为按 mode 各一次模板；标题 submission_revision=2；历史执行/Astra 盘点/新窗口执行三层证据归属；写入 audit 复跑实测结果。
- `fix-report.md` 新增：必修一（共享对象缺陷根因/独立检查器修复/正负向与 audit 验证）、必修二（补充材料根因/切片修复/Astra 8/8 比对）、随单收尾、三层证据与命令、归档声明、限制。
- `report.md` 更新 revision 2：返工说明；**更正**原“意外漂移=0”失效表述（旧 build 脚本 field-diff 不可信，现引用独立检查器 6 题允许差异+零越界）；验证摘要收尾。
- `submission.json`：submission_revision=2、responds_to=T039-R1、status=ready_for_review。
- `changed-files.json`：实测哈希 14 项核对通过（含新辅助脚本 check-field-diff.py / build-review-supplement.py）；continuation-progress.md 为运行日志不列哈希（避免自指过期）；git 脏文件未计入。
- `evaluation-report.md` 对照 `aggregate.json` 实际核对：分组表 12 值与共同子集 n=20 三模式值一致，未改动。
- revision 1 七件归档与 `.cache/t039/archive-r1/` 未覆盖；旧失败审计保全副本 SHA `41f043a2…` 逐字节一致。

### 步骤 5：终检（已完成）

命令（cwd=`F:\Collage Paper`，本窗口实跑）：

```text
python -c "<38 文件对照盘点快照 + changed-files 14 项哈希 + deliverables 存在性 + 链接解析>"
# 快照 38 项：drift 仅 verification.md 与 human-review-pending.md——恰为本返工授权修改文件（盘点为改前基线），预期内
# 23 只读文件 + 7 件 rev1 归档：零漂移
# changed-files 哈希项 14/14 匹配；submission.json: 2 / T039-R1 / ready_for_review
# deliverables 10 项全部存在；交叉链接 5/5 解析到实际文件
# 退出码 0
```

## 提交状态（本窗口最终）

**submission_revision=2、responds_to=T039-R1、status=ready_for_review、dataset 2.0 不变。** 提交目录 `docs/collaboration/submissions/T039/`。未做：真实浏览器跳转验证、新修订人工确认、学校政策现行性认证（均不在本返工授权内/无授权）。零外部模型调用、无下载安装、无 commit/push、未改 Astra 文件（audit 审计输出写入为返工单明确例外）。`planner_live_verified=false`；T040 未发布。**按授权停止，等待 Astra 验收。**
