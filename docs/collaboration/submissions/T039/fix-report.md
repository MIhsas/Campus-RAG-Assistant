# T039-R1 修复报告（fix-report.md，submission_revision=2）

身份：task_id=T039、responds_to=**T039-R1**、submission_revision=2、status=ready_for_review。
范围：仅按 `docs/collaboration/reviews/T039-R1.md` 定向修复差异审计与四项复核补充，并收尾文档/提交；**不重做 T039、不重跑三模式、不改 gold/冻结/结果/聚合**。dataset 仍为 **2.0**。
执行分两段：旧窗口完成大部分修复后输出超限中断；本窗口（2026-10-09）按交接单续接收尾。证据分三层，见 §4。

## 1. 必修一：差异清单共享对象缺陷（P2）——根因与修复

**根因**：`step2_code/backend/.cache/t039/build-v2-questions.py` 建立 `old_by_id` 时直接指向 `doc['questions']` 中的对象，随后**原地修改**这些对象，再从同一 doc 建 `new_by_id`——旧对象已被改写，两侧比较恒等，`field-diff.json` 把包括 u03 在内的全部 24 题写成 `changed_fields=[]`。所谓“意外漂移=0”不能独立守护变更范围。

**修复**：新增只读差异检查器 `step2_code/backend/.cache/t039/check-field-diff.py`——从源文件**独立加载**旧/新题集（互不共享可变对象），按本任务**字段允许集**（q08/q10=`rationale,revision_note`；u01/u02/u04=`missing,rationale,revision_note`；u03=`answerable,evidence,missing,question_type,rationale,revision_note`）逐题校验并重生成派生清单 `data/evaluations/sicau-rag-pilot-eval-v2/field-diff.json`（默认只读，`--write` 仅写派生清单；不触碰冻结 questions/freeze/annotation/results/aggregate）。

**验证**（正向/一次隔离负向，Astra 盘点实跑，本窗口引用）：

- 正向 `check-field-diff.py`：exit 0；6 题非空差异（q08/q10/u01/u02/u03/u04）全部落在允许集，18 题无变更，所有 query/conditions 不变、仅 u03 gold 改动。
- 负向 `--inject-drift q07:query`：exit 1（预期）——内存注入越界被拒，未写正式题集/清单。
- 原 Astra audit 复跑（本窗口实跑一次）：exit 0，`SUBMITTED DIFF MISMATCHES: 0`，status=ok（详见 §4c）。

**处置声明**：旧 `build-v2-questions.py` 因上述缺陷**保留历史原件但不运行**（运行会覆盖冻结题集）；差异审计职能由 `check-field-diff.py` 替代。旧生成行为的实际数据产物（questions/freeze 等）经 Astra 独立核对正确，无需重算。

## 2. 必修二：四项复核补充可定位原文（P2）——根因与修复

**根因**：`review-supplement.md` 修订 1 版不满足“可对照原文”要求——q10 只有模型示例与来源简称、无完整原引/block/跨度；u04 缺办理地点与研究生院语境原文；q08 标“逐字引用”却折叠换行空白、u03 展示规范化文本而未声明。

**修复**（旧窗口完成，`build-review-supplement.py` 从已冻结 gold 与真实解析块**直接切片**，不手抄、不调模型；本窗口**不再运行**以免覆盖）：

- 每项给出当前 query/conditions、来源标题/版本/document_id、block_id、locator（页码）、字符跨度、本机原件路径。
- q08/u03：原 quote 保留换行的逐字切片；另给规范化摘录并明确标注为规范化显示；示例释义标注模型辅助、非产品生成。
- q10：f1/f2 各有独立支持的完整原引 + 相邻上下文（“开展学生互评”前提可见）；14 条 gold 只读不变。
- u04：83eb 第 1 页“所有在校生…查询等”与第 4 页“基本信息更正地点/录取信息报研究生院”两页原文并列，标注**未核实候选**而非严格本科 gold；scope 映射维持未知。

**验证**（Astra 盘点以真实解析器独立比对）：8/8 条原引与解析块逐字相等；8 个本机原件路径存在。**程序化逐字一致≠语义审定或政策现行性认证**；不重审全部 24 题/114 意见。

## 3. 随单收尾（不增加实验）

- `docs/delivery/human-review-pending.md`：§0 收窄为「T036 首次意见对应历史包」（不再是当前入口措辞）；§1 区分历史 v1.3 题集与当前 v2.0 题集；顶部/§2/§5 统一口径（用户 109/3/2 已接收、模板 33 项已确认、四项新改待定向复核、学校政策现行性未认证）。旧文件未触碰。
- `submissions/T039/verification.md`：修复路径转义损坏/缺引号的命令为可复制 PowerShell 形式（解释器/脚本/含空格参数分别加引号）；`bm25|dense|hybrid` 改为按 mode 各一次的模板写法；标题更新 revision 2；历史执行/Astra 盘点/新窗口执行三层证据归属明确。三模式日志保持历史出处，**未为文案重跑**。
- `step2_code/backend/README.md`（旧窗口）：当前包 v1.2、v1.1 历史边界、旧 8 题实验 OR/冻结限制改历史说明；本窗口只读核对未再改写。
- `submissions/T039/evaluation-report.md`（旧窗口）：分组表已填已存 aggregate 实际值；本窗口核对一致，未新测。
- `submission.json`/`report.md`/`changed-files.json` 更新为 revision 2 元数据与实测哈希；revision 1 七件提交保持归档原样。

## 4. 证据层级与实际命令

### a) 历史执行（旧窗口，T039 任务期间）

check-real-eval（24 题/58 证据/37 冻结哈希，exit 0）、三模式各一次（results/ 完整日志，exit 0×3）、aggregate/分组/共同子集重算、两例手算。详见 `verification.md` §1—§3。

### b) Astra 盘点执行（2026-10-08—09 交接盘点，证据=`docs/collaboration/handoffs/T039-R1-20261009-盘点.json`）

差异正向 exit 0 / 隔离负向 exit 1（预期）；8 条原引逐字比对 8/8；8 本机原件存在；23 只读文件 SHA 快照。本窗口引用，不冒充自跑。

### c) 新窗口执行（2026-10-09 本续接窗口，cwd=`F:\Collage Paper`）

```text
# 只读身份核对（对照盘点快照逐文件 SHA256）
python -c "<38 文件比对>"   → drift_or_missing=0，exit 0

# 保全旧失败审计记录（探针覆盖写前）
cp reviews/T039-audit.json submissions/T039/T039-audit-rev1-failed-preserved.json
  → SHA 41f043a2e069da80… 与原件逐字节一致

# 原 Astra audit 复跑一次（返工单明确要求；内部一次 BM25 并写 Astra 审计输出）
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\docs\collaboration\reviews\T039-audit.py'
  → SCORES OK: 72 rows; common rankings/scores 60 ; fresh BM25 24 rows; group checks 36
  → SUBMITTED DIFF MISMATCHES: 0
  → stderr: 4 条 PDF 解析警告（"Ignoring wrong pointing object"，按盘点口径不计失败）
  → 退出码 0；写入 reviews/T039-audit.json（status=ok）与 reviews/T039-bm25-fresh.json
```

探针源码/判据/通过条件未改；未编码向量、未调云模型、未覆盖 `results/`。

## 5. 归档与不变更声明

- `submissions/T039/rev1/` 7 件与 `.cache/t039/archive-r1/`（旧 diff 清单及原构建脚本）保持原样，未覆盖。
- revision 1 失败审计输出保全为 `submissions/T039/T039-audit-rev1-failed-preserved.json`（旧失败历史不删除）。
- git 工作区脏文件为 T037—T039 累积修改，**不作为本返工清单**；未 reset/clean/还原用户文件。
- 新旧 questions/freeze、annotation-check/gold-revisions/review-status、results、aggregate、语料/manifest、模板、用户意见、历史实验、Astra 任务/评审/STATUS 全程只读（audit 审计输出写入为返工单明确例外）。

## 6. 限制与未验证

- 真实浏览器跳转未验证；新修订人工意见与学校政策现行性**未认证**。
- 语义边界维持返工单口径：q10 普通/互评为不同前提（不按发布时间宣称 2016 废止）；u04 scope 未知/严格不足保留；db05e0 日期未知只候选查看；u01/u02 未确认保留；用户 109/3/2 与模板 33 项确认不改，新项不代确认。
- 新基线 n=21 指标为已存身份（BM25 0.738/0.762/0.619；Dense 0.714/0.714/0.470；Hybrid 0.714/0.714/0.563），不代表算法改善/校园问答准确率/可靠拒答。
- `planner_live_verified=false`；T040 未发布。提交后停止，等待 Astra 验收。
