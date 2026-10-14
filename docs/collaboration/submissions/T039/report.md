# T039 新语料基线与人工意见定向落实 — 实施报告（report.md，submission_revision=2，responds_to=T039-R1）

身份：task_id=T039、task_revision=v1、**submission_revision=2、responds_to=T039-R1、status=ready_for_review、external_model_calls=0、planner_live_verified=false、human_review_status=user_review_received_with_open_items（109/3/2 保留）**。旧题集/实验/模板/用户意见只读；未改产品算法/评分器/筛选/provider/页面；零外部调用、无下载/安装、未 commit/push。

**revision 2 说明**：revision 1 经 Astra 核对数据/计分正确，退回两项 P2——差异清单共享对象缺陷、四项复核补充原文不足（[T039-R1](../../reviews/T039-R1.md)）。本修订按返工单定向修复并收尾（详见 [fix-report.md](./fix-report.md)）；**不重做 T039、不重跑三模式**。dataset 仍 2.0。revision 1 七件提交归档于 `rev1/` 保持原样。数据/计分小节（§1—§3）沿用 revision 1 已核对内容，其中失效表述已更正。

## 1. 独立新题集 v2.0（标注先行，详见 gold-revisions / annotation-check / field-diff）

`data/evaluations/sicau-rag-pilot-eval-v2/`：24 题/58 证据（57 继承 + u03 新增 1）；dataset_id `sicau-pilot-eval-v2` / v2.0 / dev / fact_group_or_v1.1。**仅实施四项已核实修订**（其余 query/conditions/gold 引文与事实组逐字继承）：

- **u03 → 可答**：v1.2 核实 bed3ac 日期（2019-11-07）→ as_of=2026-10-03 准入；gold=bed3ac/ebab438f[101:129]（完整前提含逾时后果；复用 q09 同事实源身份）；**db05e0 日期未知不入严格 gold**（仅未核实候选）。question_type=direct、missing=null；已查范围与推导入档，不从排名反推。
- **u04 保持严格不足**：rationale/missing 注明「严格准入依据不足，可主动查看独立未核实候选原文」——候选不作正式依据、不猜本科办理地点。
- **q08**：仅 rationale 采纳简洁释义（不带修订决定措辞）；引文「修改为」原样保留；跨度/事实组不变。
- **q10**：仅 rationale 明确普通 50/50 与互评 40/10/50 为**不同前提**、不按年份断言 2016 废止、f1/f2 不合并；14 条 gold 不变；用户废止建议维持 T037 部分采纳、不代撤回。
- u01/u02 保持不足与「未确认」；措辞限定「首批 20 份范围内缺依据（不称学校无规定）」。

字段级差异（**revision 2 更正**）：旧 `build-v2-questions.py` 的 field-diff 因共享对象缺陷无效（24 题全记 changed_fields=[]，“意外漂移=0”不成立）；现由独立检查器 `check-field-diff.py` 重生成 `field-diff.json`——6 题非空差异（q08/q10=`rationale,revision_note`；u01/u02/u04=`missing,rationale,revision_note`；u03=`answerable,evidence,missing,question_type,rationale,revision_note`）、18 题无变更、所有 query/conditions 不变、仅 u03 gold 改动；正向 exit 0、隔离负向（q07:query 注入）exit 1 均符合预期；原 Astra audit 复跑 `MISMATCHES=0`、exit 0。

authoring_note 如实：模型辅助修订、用户意见 109/3/2 已接收、新修订待定向人工复核（非全未复核、非完整教师 gold）。`review-status.json` 保存旧记录路径+SHA+原 tally+意见关联+新待复核项（不改用户原 JSON、不代签）。

## 2. 新冻结与三模式基线（先标注后冻结后运行；历史执行，revision 2 未重跑）

- freeze.json 五节 schema（dataset/corpus_pack/implementation/model/annotation），指向 v1.2/new questions；**实现 hash 取当前实际文件**（chunk.py、filters.py 等含 T034/T038 变更，未抄 T030 旧 hash）；模型=本机 BGE（无下载）。check-real-eval.py：`CHECK OK 24 题/58 证据/37 项`，exit 0。
- 既有 `campus_assistant.evaluation.run` 各 mode 一次（24 题、TopK=5、max_chars=500、overlap=0、同四条件；无 document_id、无候选、无生成/Agent）：results/*.json+stderr+exitcode 全存，valid=true×3。
- aggregate.json 由本轮完整输出重算（含分组），未复制旧 summary。

## 3. 结果（详见 evaluation-report.md；已存指标身份，revision 2 未重测）

| 模式 | 新基线 n=21 R/H/M | 共同子集 n=20 R/H/M（=T030 存储对照） |
|---|---|---|
| BM25 | 0.738/0.762/0.619 | 0.725/0.750/0.600（60/60 排名与分数一致） |
| Dense | 0.714/0.714/0.470 | 0.700/0.700/0.44333…（同上） |
| Hybrid | 0.714/0.714/0.563 | 0.700/0.700/0.54166…（同上） |

- **分表对照**（v1.1/v1.3 n=20 vs v1.2/v2.0 n=21）：差异来自分母/准入/gold 修订，**不称算法改善**。
- **共同子集 20×3=60 项排名与得分全部一致**（原文/条件/事实组未变；排名变化=无）。
- **u03 专项**：三模式 rank1 命中 bed3ac/ebab438f、MRR 1.0（手算：单源 OR、[0,452)⊇[101,129)）。**u04**：正式命中≠合规依据（严格不足；候选单列）。
- 手算二例（u03 准入事实、q10 双前提 OR/AND）见 evaluation-report §4–5；不足 3 题空检索率 0.000（独立分母，不叫拒答率）。

## 4. 人工复核补充与整理（review-supplement / T038-doc-errata / README / human-review-pending）

- review-supplement.md（revision 2 已扩充）：q08/q10/u03/u04 四项——每项含 query/条件、来源标题/版本/document_id、block_id、页码、字符跨度、本机路径与**保留换行的逐字原引切片**（q08/u03 另给规范化摘录并声明；q10 两前提各有完整原引+上下文；u04 两页原文并列、标未核实候选）；示例释义标「模型辅助、非产品实时生成」。Astra 盘点独立比对 8/8 逐字一致。不重复要求确认模板 33 项；无代签。
- T038-doc-errata.md：demo-notes 步骤 5 更正（本科 **18 份准入、正式 5 条命中**、83eb 排除——非空搜索）；浏览器证据归属 Astra（T038-browser），非 MiMo 自跑。
- README：v1.2 当前真实运行命令（含空格路径正斜杠引号写法）+ v1.1 历史基线边界（历史限制不冒充当前实现）；候选查看≠正式答案/≠已确认本科适用。
- human-review-pending（revision 2 收尾）：§0 T036-v3 收窄为「首次意见对应历史包」；§1 区分历史 v1.3 与当前 v2.0 题集；顶部/§2/§5 统一口径（用户意见已接收、模板 33 项确认、开放项+新改项待复核、现行性未认证、不称导师审定）。

## 验证摘要（详见 verification.md / continuation-progress.md）

历史执行：新契约/跨度/准入与冻结校验一次通过；三模式原始输出与 aggregate/分组一致；两例手算；旧输入/实验/用户意见 **7/7 SHA 未变**。Astra 盘点：差异正向 exit 0/隔离负向 exit 1（预期）、8 条原引 8/8 一致。新窗口执行：38 项文件 SHA 对照盘点快照 drift=0；**原 Astra audit 复跑一次 exit 0**（72 行计分、60 共同排名、36 分组、新跑 BM25 24 行一致、`MISMATCHES=0`、status=ok）。**新基线不代表校园 QA 准确率/可靠拒答/新盲测；示例释义不代表 DeepSeek 已生成正确回答；程序化逐字一致≠语义审定。**

完成后停止，等待 Astra 验收。T040 未发布。
