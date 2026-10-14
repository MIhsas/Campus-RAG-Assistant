# T041 当前交付包与真实生成案例收尾 — 实施报告（report.md）

身份：task_id=T041、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**、planner_live_verified=false。
范围：仅文档——docs/delivery 八件统一到 T038/T039/T040 已验收状态 + 新增 generation-casebook.md。**零外部调用**（不读密钥/环境、不运行 live/模型探测、不重跑 mock/全量/UI/ASR/向量/检索实验）；不改产品/脚本/语料/模板/gold/冻结/实验/用户记录/docs01—04；无 commit/push、无安装下载。T040 原授权已用满 4/4 并结束，本轮未延续。

## 1. 保全（先于一切修改）

当前八件按原字节归档 `docs/delivery/archive-pre-t041-20261011/`（8 件，改后复核归档哈希与改前记录逐一致；此前 archive-t028/archive-t035-rev1/rev1 只读未动）。

## 2. 八件定向修改（只改状态/数字/证据变化处）

| 文件 | 主要修改 |
|---|---|
| README.md | 当前状态表更新至 T038/T039/**T040**（v1.2 首批 20/1182、v2.0 基线 n=21、T040 四题冒烟与 live_verified 历史限定、人工 109/3/2+33 确认/新项不代签）；文件索引加 casebook；历史快照保留不冒充当前 |
| system-design.md | 头部时间线；边界补 T038 候选独立不进生成；§8 生成不足可靠性补 T040 n=4 非可靠性证据、q10 P3 推断待核 |
| thesis-outline.md | 摘要数字换当前基线（n=21）与 v2.0 身份、加 T040 已存样本表述；第 6 章加**表 6-5 当前基线**、表 6-2 标历史、分析/诚实声明段更新人工意见口径；第 7 章真实调用记录加 T040 准确表述（live_verified 限定）；第 8 章展望更新 |
| evidence-matrix.md | 层级图例加 [历史已存真实结果]；§3 加 T040 四题行；§7 加 T039 当前基线行、T030 标历史；§8 人工审定/生成质量/浏览器行按当前口径 |
| defense-script.md | 演示前提改 v1.2；时间表保持 560 秒（480—600 内）；§6 加当前基线、T030 标历史；备选演示加 **T040 案例只读展示**行（不点实时生成）；开场/问答口径更新 |
| windows-runbook.md | §2a 主线命令改 **v1.2**（`--help` 只读复核参数一致）；§4 加 T040 live 冒烟「历史已执行、禁止无授权例行重跑」；§6 加 live_verified=true 历史限定行；旧实验覆盖冻结警示保留 |
| experiment-index.md | 新增 **E4 当前基线**（T039 v2.0，aggregate 逐值）；E0—E3 标历史分表；实验间关系更新 |
| human-review-pending.md | 人工状态口径加 **T040 新答案待定向复核**（q10 P3 推断重点）；§3 加 T040 答案行；§5 优先级合并 T039 新四项+T040 新答案 |

## 3. 新增 generation-casebook.md

四题真实生成案例（原 query/条件、完整答案或不足理由**照录**、关键 E 来源/页码/跨度、①E 支持性 ②gold 覆盖 ③用户确认三层分列）；链接 T040 完整材料与 T040-R4 评审，不复制全库、不润色答案、不新增「示例释义」。q10 P3 标**推断待用户核实**、q08 f1 缺口保持（合理不足≠答对 gold）、u04 不足≠学校无规定。

## 验证摘要（详见 verification.md）

归档字节 8/8 一致；28 个文档链接与关键路径全部解析；指标表对 aggregate 逐值一致；四题原文本对 live-answers-full.json 逐字一致；token 算术 6080+388=6468；主线 560 秒在预算内；serve-corpus `--help` 只读核对参数一致。本轮实测/历史引用/未验证范围在 verification.md 分层写明；未代填浏览器/用户确认。

## 未验证与边界

- 真实答案质量、学校政策现行性、用户确认（109/3/2 之外新项）均**未验证**；`live_verified=true` 仅 T040 历史四题链路/存档核查（T040-R4 认定），**非本轮 live 验证**。
- 本轮无浏览器实操、无现场计时实测；mock/历史调用/离线核查/浏览器各层未混写。

完成后停止，等待 Astra 验收；不推进 T042。
