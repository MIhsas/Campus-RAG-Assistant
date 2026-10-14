# T042 八项定向补充复核包 — 实施报告（report.md）

身份：task_id=T042、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**、**human_review_status=unreviewed**、planner_live_verified=false。
范围：离线小型补充复核页工具（8 项）；**零外部调用**（不读密钥/环境、不调用 ASR/向量/Planner/模型）；不改产品 API/前台、旧 T036 脚本/HTML/包、gold/冻结/指标/模板/历史输出/用户原记录；无下载安装/commit/push。旧模型授权已结束，本轮未使用。**工具完成不等于人工复核完成**——8 项新意见待用户填写，本任务只交工具与待填内容。

## 1. 交付物

| 文件 | 说明 |
|---|---|
| `step2_code/backend/scripts/build-targeted-review-pack.py` | 只读构建脚本：解析真实块核验全部嵌入引用（SHA/块/跨度/quote 逐字），失败不出包；输出目录非空拒覆盖 |
| `step2_code/backend/scripts/targeted-review-pack.html` | 自包含离线页面模板（内联 CSS/JS/数据；无 fetch/localStorage/外链；无全选通过/自动保存/筛选矩阵） |
| `step2_code/backend/tests/test_targeted_review_pack.py` | 构建聚焦测试 6 项 |
| `step2_code/backend/scripts/check-targeted-review-pack.cjs` | JS 行为检查（DOM/桩级）24 项 |
| `.cache/human-review/T042-v1/{review.html,pack.json,README.md}` | 正式输出（含本机打开路径与可复制构建命令） |
| `submissions/T042/` | report/verification/submission/changed-files + demo-notes + 模拟导出样例 |

## 2. 8 项与关键口径

- **稳定分域 ID**：`revision:q08/q10/u03/u04` 与 `answer:q08/q10/u03/u04`——同题不同阶段**意见状态互不共享**；仅 8 条顶层意见（每卡一行），不加逐引用意见。
- **分区一 T039 修订**：原意见只读（历史 109/3/2 之一，不预填）、处置、新题面/条件/事实组或不足范围、gold 原文与待确认点（自 review-supplement 解析并与冻结题集/真实块三方核对一致）。
- **分区二 T040 结果**：历史原 query/条件、完整原答案或不足理由**逐字照录**（含 q10 P3）、该次实发 E（20 条，逐字核验）、辅助核对与用户状态（=未确认，不代签）。
- **关键分隔**：q08 修订 gold 与 T040 未检出该 gold 分区显示（gold 不补成实发 E，测试断言互不包含）；q10 两前提分列+P3 推断黄框突出、不宣告 2016 废止；u03 日期已核实≠现行性认证；u04 未核实候选（83eb）标「未核实范围/非本次模型依据」且未混入实发 E。
- **导出**：新 JSON 含 review_scope、8 项（id/对象类型/题号/意见/说明）、输入版本与 SHA、导出时间；复核人/复核日期**留空由用户填、不预填**；统计只计 8 项、不与历史合并。

## 3. 验证摘要（详见 verification.md / demo-notes.md）

构建：40 条引用（17 gold+3 候选+20 实发 E）逐字/跨度/SHA 核对通过、8 卡齐备、全未复核、源输入前后 SHA 一致、非空拒覆盖 exit 1。测试：pytest **6 passed**（exit 0）；JS 桩 **24 项通过**（含独立模拟：仅 answer:q10 需修订+P3 说明→导出，revision:q10 与其余 6 项保持未复核、身份正确；模拟样例独立标注「模拟操作测试」、不进默认包）。**无真实浏览器**：本窗口如实桩级，demo-notes 给出用户/Astra 短检查表（打开→展开 q10→改 1 项→导出），不冒充浏览器实测。

## 4. 边界与未验证

- 8 项新意见=全未复核，待用户填写；处置落档属后续任务。语义正确性/政策现行有效性未验证；程序化核对≠语义审定。
- 未跑产品套件/实验/模型/旧 114 项测试；未改任何只读输入（测试断言前后 SHA 一致）。
- T040 `live_verified=true` 历史限定、`planner_live_verified=false`、原授权结束均不变。

完成后停止，等待 Astra 验收；不标 accepted；用户填写与下一步落档另行处理；不推进 T043。
