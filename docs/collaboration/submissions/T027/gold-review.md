# T027 金标准标注与人工复核清单（gold-review.md，revision 2）

> **T027-R1 修订版**：撤销 rev1 的「twin 排除约定」（未限定来源时逐字相同/等价表述即有效证据，文档身份只定位不作相关性判断）；引入可替代证据组语义。逐题修订清单、前后哈希与重算核验见 **`gold-revisions.md`**；rev1 完整存档见 `rev1/`。

## 1. 标注来源声明（如实）

- **题目与标注由 MiMo（Claude Code 执行模型）直接阅读合成语料原文块后辅助编写**（含 T027-R1 相关性复核修订），不写成教师/学生独立标注；数据集 `authoring_note` 同步声明。
- **金标准独立于检索结果制定**：标注与修订均只依据原文语义等价性（跨度由 `build-eval-v2.py fill-spans` 原文子串精确定位）；**未从任何检索模式的返回结果反推**（修订确定后才与已存排名对照核验影响）。
- 全部语料合成（13 文档含 2 份明显标注干扰文档）；夹具内「不得用于论文评测」为原夹具警示语，读法见 evaluation-report 第 9 节。

## 2. 标注规则（v2.0）

每题：`question_type`（7 类）、`conditions`（产品同一筛选字段）、`answerable`、`rationale`、`missing`（不足题）；每条证据精确 `document_id/block_id/[char_start,char_end)` + 逐字 `quote` + **`fact_id`**。

**可替代证据组（T027-R1 核心口径 + T027-R2 完整性收紧）**：
- 同 `fact_id` = 同一必要事实的可替代来源——**组内 OR（任一来源被完整跨度覆盖即该事实满足）**；
- 不同 `fact_id` = 不同必要事实——**组间 AND（都覆盖才 recall 满分）**；
- 重复来源不作为多个必须找齐的事实稀释 Recall（分母=事实数，非来源数）；
- **组内每条来源必须独立支持该组声明的完整事实（R2）**：不同材料要求（医院证明 vs 书面说明）与不同精度要求（考前 vs 考前 3 个工作日）不互替；不同文件各自存在≠互为替代；适用范围/版本不确定时先用题面限定使事实确定；
- 等价判定标准：足以回答同一问题的同一事实表述（逐字相同、同期限/同结论不同措辞）；**仅主题相关或内容冲突的句子不算**；不同适用对象/不同奖项不算等价；
- 未标 fact_id 的旧数据（含旧 8 题）保持逐证据口径，行为验证不变。

**同题不同筛选组**（`group_id`）：g-year-defer（q16/q17）、g-campus-defer（q18/q19）、g-time-defer（q20/q21）——同对同题、conditions 不同、准入证据不同。
**题面消歧**（q12 版本限定、q20/q21 渠道维度）：限制写进题目，不藏 rationale；干扰资料保留不删（见 gold-revisions 第 2 节）。

## 3. 逐题速查（v2.0；完整 rationale/revision_note 见 `examples/evaluation-v2/questions.json`；引句原文见 `blocks-text.md`）

| 题号 | 类型 | 可答 | 事实组（可替代来源数） | 复核要点 |
|---|---|---|---|---|
| v2-q01 | direct | ✓ | f1×1 | 补考 60 分 |
| v2-q02 | direct | ✓ | f1×3 | 审批链三处等价（R1 补 2） |
| v2-q03 | direct | ✓ | f1×1 | 都江堰受理部门 |
| v2-q04 | direct | ✓ | f1×2 | 成绩以教务系统为准（R1 补 docx） |
| v2-q05 | paraphrase | ✓ | f1×2 | 缓考定义；两版逐字同句均有效（R1 撤 twin） |
| v2-q06 | paraphrase | ✓ | f1×1 | 重修规定 |
| v2-q07 | paraphrase | ✓ | f1×1 | 作弊取消资格 |
| v2-q08 | low_keyword | ✓ | f1×3 | 备案（R1 补 fd 两源） |
| v2-q09 | low_keyword | ✓ | f1×1 | 三分之一 |
| v2-q10 | multi_evidence | ✓ | f1×2 + f2×2 | **R2**：限定 2024 级；f2 仅医院证明 2 源（书面说明不并组） |
| v2-q11 | multi_evidence | ✓ | f1×1 + f2×1 | 2025 级时限 AND 成绩记录 |
| v2-q12 | multi_evidence | ✓ | f1×1 + f2×1 | **题面限定虚构 2024 版**（R1 消歧）；v2 版 3 日口径冲突不计 |
| v2-q13 | distractor | ✓ | f1×1 | 研究生限定（本科资料不适用，非等价） |
| v2-q14 | distractor | ✓ | f1×1 | 不得代办 |
| v2-q15 | distractor | ✓ | f1×3 | 复核期限三源等价（R1 补 docx 句+表行） |
| v2-q16 | filtered | ✓ | f1×1 | **R2**：g-year-defer(2024)；来源系列=按年级办法，完整规定=「考前提交」 |
| v2-q17 | filtered | ✓ | f1×1 | **R2**：g-year-defer(2025)；完整规定=「考前 3 个工作日」，宽泛「考前」不替代 |
| v2-q18 | filtered | ✓ | f1×2 | g-campus-defer(成都)；途径两源（R1 补正文句） |
| v2-q19 | filtered | ✓ | f1×1 | g-campus-defer(都江堰) |
| v2-q20 | filtered | ✓ | f1×1 | g-time-defer(2026-10)；**题面限渠道维度**（R1 消歧） |
| v2-q21 | unanswerable | ✗ | — | g-time-defer(2025-10)；缺线上/纸质说明（R1 同步消歧） |
| v2-q22 | unanswerable | ✗ | — | 学校奖学金≠国家奖学金（不等价） |
| v2-q23 | unanswerable | ✗ | — | 无宿舍资料 |
| v2-q24 | unanswerable | ✗ | — | 陷阱：提及线上系统无网址 |

## 4. 人工复核清单（Astra 抽查用，v2.0）

1. **修订正确性**：对照 `gold-revisions.md` 抽查 11 题修订——等价判定是否成立（q05 逐字同句、q15 同期限三源、q10 材料组收录范围）、排除项理由是否充分（fd-yjy 受理窗口、cmp 审批时限句、pdf 代办句）。
2. **消歧题**（q12/q20/q21）：版本/渠道限定是否写进题面（非 rationale 偷藏）；q12 失分是否被如实报告（evaluation-report 案例 4）。
3. **事实组结构**：抽查 fact_id 分组（组内 OR、组间 AND），确认重复来源未稀释分母（q10 分母 2 非 8）。
4. **引句回溯**（41 条跨度）：对照 `blocks-text.md` 核对 quote/跨度/哈希（`dataset-hashes.json` 冻结值）。
5. **同题筛选对**：q16/q17、q18/q19、q20/q21 仅 conditions 不同；准入断言与 gold 归属正确。
6. **不足四题**：missing 语义；q21 渠道维度下确无作答来源。
7. **独立性**：确认修订未按检索结果定向（修订清单先于重算冻结；检索结果仅事后核验影响）。
8. **旧 8 题兼容**：rev1 行为不变（测试 + 重跑 summary 逐项一致）。

## 5. 题目规模

24 题不变（20 可答 + 4 不足）；41 条来源跨度归入 23 个必要事实组。未为凑数或提分增删题目；q12/q20/q21 仅为题面消歧（干扰资料保留）。
