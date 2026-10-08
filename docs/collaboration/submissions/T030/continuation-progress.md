# T030 执行进度（continuation-progress.md）

## T030-R2 返工（2026-10-07 起，当前阶段）

授权：docs/collaboration/reviews/T030-R2.md（仅两处标注收尾；冻结校验已关闭不重测）。目标：submission_revision=3、responds_to=T030-R2、dataset v1.3。

待办：
1. [完成] 归档 v1.2 基线：`data/evaluations/sicau-rag-pilot-eval-v1/archive-v1_2-rev2base/`（题集/freeze/标注说明/results 全树 28 文件）+ `submissions/T030/rev2/` 七件，逐一 SHA-256 字节核验 10/10 一致。rev1 与 midway 归档未触碰。
2. [完成] q10 两条 f1 跨度补齐：f1-s6（cc25/dc971233）503-526→503-536、f1-s7（bb8b/090f4a9c）470-493→470-503，均延长至「和答辩成绩（50%）」（两个组成部分+比例齐备；「组成」尾词仍被分页截断、不入跨度）。rationale/revision_note 更新（含半事实断言指引）。
3. [完成] q13 后半问改为「依据该办法第十条和第十一条，哪些课程不作学分认定？」；rationale 声明本题为受单块引文证据契约限制的开发集题目、不覆盖第四条情形；gold f1/f2/f3 不变。
4. [完成] dataset_version 1.2→1.3（authoring_note 补 R2 修订）；annotation-check.md 同步（q10/q13 行、◆标记、运行策略=仅 q13 重检索）；freeze.json 重冻（frozen_at 2026-10-07，questions_sha256=`5fde70a332744b642e48014abc82902009abc1a106a84e6241b3c460e4faed5c`，annotation sha `8d391b62…`，38 项）。
5. [完成] q13 三模式子集重检索（`results/rerun-v13/`，各 exit 0；q13：bm25 1/1/1.0、dense 1/1/0.333、hybrid 1/1/1.0）+ eval-v2-rescore 合并（23 题复用重计分 + q13 rerun，exit 0）。
   - v1.3 汇总（K=5,n=20）：BM25 0.725/0.750/0.600；Dense 0.700/0.700/0.443333…；Hybrid 0.700/0.700/0.541666…。唯一分数变化=q13 dense MRR 0.5→0.333（新题面排名）；q10 重计分后分数不变（原样记录）。
   - 一致性核验（对照 archive-v1_2-rev2base）：72/72 排名与来源逐项一致（q13 vs rerun-v13，其余 vs v1.2）；22 题×3=66/66 未变题分数一致；无其他差异。
6. [完成] 聚焦探针升级（focused-probe.py）：每场景带期望断言、失败返回非零；新增 q10 半事实断言（覆盖导师50%的单独命中→recall 0.0/f1 未覆盖；完整跨度→recall 0.5/f1 覆盖；f1-s6/f1-s7 两组各 4 断言全过）；`--skip-matrix` 跳过缺节/漂移矩阵（R1 日志仍有效）。`focused-probe-r2-output.txt`：15 checks / 0 failures / PROBE OK，exit 0。（首轮断言曾因期望值未舍入失败 exit 1——证明失败路径生效，修正比较逻辑后通过。）
7. [完成] 报告与四件（submission_revision=3、responds_to=T030-R2、dataset v1.3）：gold-revisions（§0 v1.3 轮+哈希链+指标列）、annotation-check（v1.3）、human-review（程序化重建 24 行）、evaluation-report（版本/指标/逐题/手算含 q10 半事实对照）、report、verification、submission、changed-files。
   - 附带数据一致性修复：合并产物的 summary_by_type/summary_by_filter_group 为源运行遗留值（T027-R2 合并脚本不重算分组字段），已按 run.py 同一聚合口径补算并加 group_summary_note；报告 §2 分组数字同步刷新（如 dense multi_fact MRR 0.458→0.583，为遗留值更正而非实验变化）。
8. [完成] 提交材料就绪（submission_revision=3），停止执行，等待 Astra 验收。

## T030-R1 续接（已完成，2026-10-07，submission_revision=2 / dataset v1.2）

- 续接窗口启动：2026-10-07（Asia/Shanghai），执行者 MiMo，授权范围仅 T030-R1。
- 已按顺序读取：根 CLAUDE.md、docs/collaboration/STATUS.md、handoffs/T030-R1-20261004-MiMo续接.md、handoffs/T030-R1-20261004-新窗口提示词.txt、reviews/T030-R1.md。
- 续接原则：从已落盘进度继续，不从零重跑；不覆盖用户/Astra 文件；小步执行、每步更新本文件。

## 本窗口起点已确认（依据交接单 + 本窗口初步目录盘点）

- 提交目录 `docs/collaboration/submissions/T030/` 现有 7 件：changed-files.json、evaluation-report.md、gold-revisions.md、human-review.md、report.md、submission.json、verification.md。
- **提交目录 rev1/ 当前不存在**（交接单称“存在但为空”；本窗口实测无此目录），需新建并按原字节归档 v1 四件 + human-review。
- `data/evaluations/sicau-rag-pilot-eval-v1/`：questions.json / annotation-check.md / freeze.json（v1.1）、results/（24题合并三模式）、results/rerun/（10题子集）均在。
- 同目录 `rev1/`（数据侧）已存在：annotation-check.md、freeze.json、questions.json、results/ — 为真正 rev1 题集归档，只读不覆盖。
- `.cache/t030/` 与 `.cache/astra-t030/`（audit-latest.json、freeze-wrong-questions-hash.json、parsed.json）在位。
- evaluation-report.md 仍在“## 3. 逐题结果”标题处中断（待本窗口续写）。

## 待办队列（按交接单第6节顺序）

1. [完成 2026-10-07] 保存历史与中间成果：
   - `submissions/T030/rev1/`：report.md、verification.md、submission.json、changed-files.json、human-review.md 五件按原字节归档，逐一 SHA-256 与源文件核验一致（report f54b4cf0…、verification 0dbcb0c3…、submission f9a760a4…、changed-files 55db8e63…、human-review c88345cb…）。
   - `data/evaluations/sicau-rag-pilot-eval-v1/midway-20261004-v1_1-draft/`：v1.1 中断现场（题集/标注/freeze/结果全树/两份报告草稿）+ README.md 说明；questions.json 复制后哈希 55dec5eb… 与源及 Astra 快照一致。该归档明确标注非 rev1、非最终 rev2。
   - 旧 revision 1 的 evaluation-report.md 原件：全项目（含 .cache）检索无真实备份，**记录缺失，不伪造**。已写入中间归档 README 与本文件。
2. [完成 2026-10-07] q06/u04 语义与 fact 分组修正：
   - 完整原文核实：f74aff0841628203（83eb 学籍指南，PDF 第4页）含三个不同情形——①基本信息（姓名/性别/出生日期/身份证号）有误更正：学生本人提交申请及证明材料到成都校区 1 教 105 室或雅安校区综合楼 217 室办理；②录取信息有误：培养单位统一报研究生院（主体/程序不同）；③在校期间修改姓名、身份证号：另一情形（合法变更而非差错更正），其引文还省略雅安楼栋。
   - 采用交接单推荐设计：q06 题面限定「学籍基本信息有误需要更正时，学生本人去哪里办理？」；gold 收敛为单 fact f1、单一完整条款来源（span 80-175，含情形+主体+地点，不再截取地点片段）；撤销原 f1/f2（跨情形两个必要事实 + f2 引文缺楼栋）。
   - u04 同题筛选对同步 query；student_type=本科 保守排除未知 scope 的产品语义保留不变。
   - 已写回 questions.json，对比中间归档确认仅 q06/u04 变更、24题结构完好（文件 47439 字节）。
   - 注意：q06/u04 query 相对 results/rerun 所用 v1.1 题面又有变化，后续需仅对这两题重新检索。
3. [进行中] 全 24 题语义复核（逐题列修改/不变及理由）。已完成的判定：
   - q03/q04：版本消歧（2019〕7号）维持不变；bb8b 两级审批/开集原因与其他版本三级/闭集表述按版本排除，理由成立。
   - q05：五源齐（287d×2/6e12/c0ccb/c888）；cc25/bb8b「答辩前提交」缺周数限定正确排除。不变。
   - q07：c0ccb 单源完整；c888 同句「直至；」缺字属实、正确排除。不变。
   - q09：「30分钟后」全库仅 bed3ac+db05e0 两源，齐。不变。
   - q16/q17：版本限定下各自唯一源属实（同句20%见于2020/教学管理族他版、30%另见bb8b他文，均按版本排除）。不变。
   - q19：第九条违纪处理=取消该科目成绩，块内完整。不变。
   - q20：「选题意义」全库 3 处=现有 3 源，齐。不变（旧窗口已补 cc25/bb8b 两源）。
   - q01/q02：「初修缓考85/补考75」全库 5 处=现有 5 源；c0ccb/c888 无此规则。q02 的 68fb 源原引文缺「补考」主题词，已扩为完整子句（q11 f2-s1 同步）。
   - q13（修改）：发现同文第十条短期课程（学时<16）排除漏标；补 f2；题面收窄为「不作或不进行学分认定」课程属性排除口径；f1 补「认定遵循…原则」框架跨度；第四条修读情形排除（跨分页两块、单块无独立完整支持）如实记录不入 gold。
   - q18（修改）：原引文从「其补考后」起、代词无指代，且题面泛问「少数民族」≠原文「因学习困难的民族地区少数民族」——题面消歧 + 跨度补前提（同 q08 口径）。
   - q10（修改）：发现 q05 同类漏标——教学管理族 c0ccb/ca36d9c1、6e12/34172617、cc25/dc971233+32d42892、bb8b/090f4a9c+6b65febc 共 4 组跨版本源（f1×4、f2×4）未标；已补（cc25/bb8b 的 f1 句分页截断取完整子句口径，与 287d 表注源同口径）。现 14 条证据。
   - u01：全库无缓考门数上限表述（「缓考申请」5 处均为程序，无数量限制）。不变。
   - u02：「晚归」0 处、「宿舍」仅转专业住宿安排 2 处。不变。
   - u04：「1教105/217」仅 83eb（scope 未知）；本科筛选下准入排除成立。不变（题面已随 q06 限定）。
   - q11：教发〔2018〕10号四情形枚举与题面显式范围一致（第五节毕业前自修不在题面枚举内）。不变（f2 跨度已随 q02 修复）。
   - q12/q14/q15：源块核对属实（44392bef 三项/9d80c82d 两项/44392bef 均合格）。不变。
   - 影响检索的题（query 变化）：q06、u04、q13、q18；其余本轮为 gold-only 或不变。
   - 全部 49 条证据 quote==slice 待 checker 终验；引文截断扫描已过（无句中残缺）。
3. [完成 2026-10-07] 全 24 题语义复核完成（判定详见上文；q06/q10/q13/q18/q02 五题有修订，其余不变并有逐题理由）。
4. [完成 2026-10-07] 版本递增与重新冻结：
   - questions.json → dataset_version=1.2，authoring_note 补 v1.2 修订说明；24 题 / 20 可答 / 57 条证据（q10 扩源 6→14）。
   - annotation-check.md 重写为 v1.2 口径（q06/q10/q13/q18/q02 行更新、运行策略按最终题面修正）。
   - freeze.json 重新生成：dataset_version=1.2，questions_sha256=`799ed1c112d0b89f12491087677d8b33c01d3105498cafaa061c878b198ca1a7`（不再沿用 55dec5…），annotation-check 哈希 `1ad802d2…`，其余节（语料/实现/模型/参数）原样不变；冻结项 38。frozen_at=2026-10-07。
   - v1.1 草稿冻结保留在 midway 归档，未追溯改写。
5. [完成 2026-10-07] 最小范围重算完成：
   - v1.2 query 变化题（q06/u04/q13/q18）× 三模式子集重检索 → `results/rerun-v12/`（各 mode.json/stderr.log/exitcode.txt，三次 CLI 均 exit 0，results.valid=true）。输入为 `.cache/t030-r2/questions-v1_2-changed-subset.json`（该结果 JSON 的 questions_sha256 为子集文件指纹，非全量题集指纹）。
   - 合并重计分：`scripts/eval-v2-rescore.py`（T027-R2 既有脚本，未修改）——20 题已存排名重计分 + 4 题重检索记录合并 → `results/{bm25,dense,hybrid}.json`（questions_sha256=799ed1c1… 全量指纹）+ `results/rescore-v12.json`（逐题来源标注 rerun/rescored_from_saved_ranking），exit 0。
   - **最终 v1.2 基线（K=5，可答 n=20）**：BM25 Recall 0.725 / Hit 0.750 / MRR 0.600；Dense 0.700 / 0.700 / 0.451666…；Hybrid 0.700 / 0.700 / 0.541666…（较 v1.1 草稿 MRR 上升为 gold 修正效应，非算法改进）。
   - 排名来源一致性核验（本窗口脚本）：72/72 条 hit_summary 与各自来源（rerun-v12×12、results/rerun×24、rev1×36）逐项一致；18 题 gold 未变者 54/54 分数三元组一致；预期 gold 变更分差 5 处（q05 dense 0.2→0.5、hybrid 1/3→1 与 Astra 反事实探针数字一致；q10 三模式因扩源上升），其余无异常。
   - 注意：results/*.stderr.log+exitcode.txt 为 2026-10-03 rev1 全量 CLI 遗留日志，非本次合并运行证据；合并工具内置 merge_note 标注「T027-R2」为其模板字样，实际口径以本文件与报告为准。
6. [完成 2026-10-07] 聚焦回归与一致性检查：
   - checker 正向：v1.2 题集+冻结 CHECK OK（24 题/57 证据/38 项），exit 0。
   - Astra 错哈希探针复跑（docs/collaboration/reviews/T030-audit.py，未修改）：exit 0，submitted exit=0、wrong_questions_hash exit=1、`wrong_hash_rejected= True`。
   - 聚焦探针 fix-checks/focused-probe.py：缺 5 节/空清单 6 场景 exit 1（无零项通过）；单点哈希漂移 6 类（语料/实现/模型身份/标注/题集/manifest）exit 1；q05 计分回归 dense 0.2→0.5、hybrid 1/3→1（与 Astra 反事实一致）。输出全文 fix-checks/focused-probe-output.txt。
7. [完成 2026-10-07] 报告与四件：
   - evaluation-report.md 补全 §0–§8（rev1 哈希更正为 a9f284b0…、v1.2 汇总/分组/逐题/失分案例/观察与假设分离/两题手算/局限/≤3 建议）；撤回旧草稿「q17 重检索后反向变化」错误表述（q17 从未重检索，与 rev1 完全一致）。
   - gold-revisions.md 重写：逐题两轮（★v1.1/☆v1.2）修改/不变及理由、rev1→v1.2 分数差异全录、计分路径按实际。
   - report.md/submission.json/changed-files.json 更新为 revision 2（submission_revision=2、responds_to=T030-R1、status=ready_for_review、external_model_calls=0、planner_live_verified=false、dataset_version=1.2 分列）；human-review.md 由 v1.2 题集程序化重建（24 行、复核栏全部未复核）。
   - changed-files.json 哈希用实测全值（曾短暂误写缩略后缀，已更正并复核）。
8. [完成 2026-10-07] 提交材料就绪，停止执行，等待 Astra 验收。

## 当前步骤

第 2 项 q06/u04 已修正。进行第 3 项：全 24 题语义复核（逐题列修改/不变及理由，覆盖未点名题目与替代来源回查）。

## 中断恢复指引

若本窗口再次中断：从本文件“待办队列”第一项未完成处续接；已写文件与日志保留；不要重跑全部实验。
