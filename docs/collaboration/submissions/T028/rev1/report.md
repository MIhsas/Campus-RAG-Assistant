# T028 论文系统设计与答辩交付包 — 实施报告

身份：task_id=T028、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0、planner_live_verified=false**、tinyagent_integration_kind=reference。本轮为文档任务：**零外部模型调用、无下载、无安装**；未改产品代码、语料、gold、docs/01—04、历史实验原始文件；未重跑全量测试/模型实验。

## 概述

依据**当前实际代码**（截至 T027 revision 3）与已验收证据，在 `docs/delivery/` 完成六件交付：交付索引、系统设计（含 Mermaid 架构/时序图）、论文结构与关键正文底稿、证据矩阵、8—10 分钟答辩脚本、Windows 运行说明。旧方案 docs/01—04 视为规划文档，冲突处以实现为准；PROJECT_CONTEXT 旧状态（TinyAgent 待选、真实调用未发生）已按 T023—T026 现状核对更正（TinyAgent=reference 接口参考的自研受限编排；真实调用已发生 2 次受控冒烟）。

## 交付内容（对照任务书六个文件）

1. **[README.md](../../delivery/README.md)**：文件索引、一页完成状态表（能力×证据层级）、**T027 v2.1 最终指标**、历史真实调用口径（T025 partial 明示）、T027-R3 勘误声明、**待用户提供的材料清单**（真实资料/人工 gold/答辩安排/格式要求/调用授权）、使用顺序建议。
2. **[system-design.md](../../delivery/system-design.md)**：需求与用户流程；Mermaid 总体架构图 + 检索/问答/规划三张时序图；模块表（11 组代码路径）；**关键 API→代码映射**（抽查级）；**数据存储与生命周期**（磁盘语料包/进程内索引/浏览器 localStorage/环境变量密钥——无数据库、无账户、无部署虚构）；可替换层（Planner 契约、Provider 协议、检索分发、TinyAgent=reference、RAGFlow=调研参考）。
3. **[thesis-outline.md](../../delivery/thesis-outline.md)**：建议题目与摘要草稿；8 章逐章写作内容 + **可直接改写段落**（引用块）+ 证据位置 + 待补内容；第 6 章采用 **T027 数据版本 2.1 最终指标**（K=5：0.950/0.950/0.925、0.900/0.900/0.705833、0.950/0.950/0.891667）；观察/假设分离；真实资料五步接入路线（不杜撰参考文献/调查/显著性/审核结论）。
4. **[evidence-matrix.md](../../delivery/evidence-matrix.md)**：8 组主张逐条标注**实现/验证层级/证据/局限**（合成实验、模拟、历史真实调用、未验证四类分开）；第 8 节“明确未验证”清单（真实校园效果、planner_live_verified=false、可靠拒答、统计显著性等）；第 9 节 **T027-R3 两项文字勘误声明**（Dense「R 升、H 不变」；“医院证明或学院书面说明”为析取/备选表述；标注为模型辅助）。
5. **[defense-script.md](../../delivery/defense-script.md)**：8—10 分钟分段脚本（每步：输入/点击/预期可见/讲解要点/证据层级）；基于 demo-campus；模拟生成与模拟规划**标注必讲**；失败/不足呈现单列（诚实性）；实验用 2.1 指标；**T025 partial 不包装为成功**；10 条答辩问答。
6. **[windows-runbook.md](../../delivery/windows-runbook.md)**：启动命令经**真实 `--help` 核对**（serve-corpus/demo-campus/evaluation run/live-smoke-planner/register-corpus）；含空格路径 PowerShell 可复制；默认演示零收费；密钥仅占位符；**状态口径速查（配置≠验证）**；常见故障定位（含 NO_PROXY 进程级口径）。

## 重点要求落实

1. **与实际实现一致**：架构/接口/数据流按源码核对（`main.py` 显式装配、`execute_search` 同口径、`build_draft` 四道引用核对、`_finish_verdict` 服务端判定、越权参数拒绝等）；不虚构数据库/账户/部署。
2. **四类证据分开**：证据矩阵逐条标注；答辩脚本开场即声明；论文底稿实验章含“模型辅助标注、全合成、不外推”诚实声明段。
3. **T027 v2.1 指标 + T025 partial 口径**：主表采用 2.1 最终值；T025 在 README/thesis/defense 三处均写“整体 partial、完整流程未通过、planner_live_verified=false”。
4. **真实资料路线**：thesis-outline 第 8 章 + README 材料清单（五步：登记→人工核对→真实 gold→小规模三模式→另行授权评测）。
5. **核查范围克制**：仅核对文档链接/代码映射/启动参数/指标一致性 + 三条文档→实现抽查（问答/办事/规划），未重跑全量/模型实验。

## 验证摘要（真实命令见 verification.md）

- 交付包 6 文件存在；README 相对链接 0 断链；**15 条关键代码路径抽查存在**。
- **指标一致性**：`results/aggregate.json` 机器值与文档主表逐位一致（0.95/0.95/0.925、0.9/0.9/0.705833、0.95/0.95/0.891667）。
- **启动参数**：serve-corpus.py 实际 10 个参数与 runbook 一致（`--help` 实录）。
- **三条文档→实现抽查**：问答（`api/ask.py::answer_mode` + `qa/deepseek.py::generate`）、办事（`procedures/service.py::build_draft/_check_citation/saveable`）、规划（`agent/workflow.py::_finish_verdict/run_planner_loop` + `tools.py` forbidden）全部命中。

## 修改与新增文件

- 新增：`docs/delivery/` 六件（上表）
- 修改：`step2_code/backend/README.md`（仅新增“论文与答辩交付包”入口一节）
- 提交：`docs/collaboration/submissions/T028/` 四件；清单见 `changed-files.json`
- 未修改：产品代码、语料、gold、docs/01—04、历史实验原始文件（T027-R3 勘误在新交付包内声明，不改历史产出）

## 本轮真实核查 / 未运行项

- **真实核查**：文档链接与代码路径存在性、启动参数 `--help` 一致性、指标与 T027 机器结果一致性、三条文档→实现抽查、T027-R3 勘误落实。
- **未运行**（按任务范围）：全量测试、UI/ASR/检索实验、真实模型冒烟；**浏览器演示脚本未在本轮实操**（无浏览器能力；defense-script 为预期操作单，实操证据归属 T016—T023 各任务验收记录，不冒充当前新测）。

## 待用户提供（详见 README 清单）

真实四川农业大学公开文档（原件+来源 URL+适用信息）、真实题集人工标注、答辩安排、学校论文格式要求、（如需）生成/规划质量评测的调用授权。

完成后停止，等待 Astra 验收。T029 未发布。
