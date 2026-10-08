# T035 真实资料论文与答辩交付包更新 — 实施报告（report.md，submission_revision=1）

身份：task_id=T035、task_revision=v1、**submission_revision=1、status=ready_for_review、external_model_calls=0、planner_live_verified=false**。本轮为**文档收尾**：未新增功能、未重跑实验/浏览器/模型；不改产品代码、模板、语料、gold、历史实验与 Astra 文件；零外部调用、无下载/安装、未 commit/push。

## 归档与更新范围

- **归档**：T028 阶段原六件 → `docs/delivery/archive-t028-delivery/`（6/6 SHA-256 字节核验一致）；旧 `docs/delivery/rev1/` 保留只读。
- **更新六件**：`docs/delivery/` 下 README、system-design、thesis-outline、evidence-matrix、defense-script、windows-runbook——同步 T029—T034 已验收成果（真实首批 20/1182 文件与保守排除、2026 版转专业模板 1.2 已接入、T031 指定文件与 T033 关键词/来源入口已验证、RAGFlow/TinyAgent 仍为 reference、T025 规划 partial/planner_live_verified=false）。
- **新增两件**：`experiment-index.md`（E0 合成—E3 重叠消融的身份/输入/指标/局限，数值取机器产物）；`human-review-pending.md`（用户/导师待复核清单，不代签）。
- **勘误**：`T034-doc-errata.md`（T034-R1 四项非阻断说明：边界案例实际窗口、q10/q11 回退不归因 top5 重复、兼容范围限定、旧元字段与 v1.3 区别），实验章引用；**未覆盖 T034 原始数据/冻结/历史提交**。

## 内容要点（按任务书七项）

1. **状态表**：真实 20/1182 文件、未知范围/日期保守排除；模板 1.2（13 步 20 引用）已接入；T031/T033 已验证；RAGFlow/TinyAgent=reference；T025 partial、planner_live_verified=false。
2. **系统流程**：文件选择∩四条件求交（先准入后 TopK、不放宽）、原文证据、问答→模板的来源约束与快照链接（document_id 不进办事参数）、手动保存个人待办（localStorage）；架构图只更新实际模块（source_selection、模板元数据），无虚构 DB/登录/推送；DeepSeek 出站范围照实。
3. **实验章分表**：表 6-1 T027 合成（历史对照）｜表 6-2 T030 v1.3 真实基线｜表 6-3 T031 文件选择对照（**非纯算法提升**）｜表 6-4 T034 重叠消融（**默认不采用**）；每表标 K/分母/数据与方案身份；R/H/M≠整题答对率、空检索率≠拒答率；gold 模型辅助、人工未复核、已见开发集局限全保留。
4. **T034 勘误**写入 `T034-doc-errata.md` 并被 thesis-outline/evidence-matrix/experiment-index 引用。
5. **答辩主线**（8—10 分钟）：首页能力→指定 2023/2026 检索与出处→2026 入口/2023 不推荐对照→办事草稿与个人保存→依据核对/日期排除→实验取舍；备选（真实生成/语音/规划）逐项标证据层级；未实跑步骤标 `[本轮未实跑]` 不称「浏览器已验证」；T014 为历史冒烟不写成现场实时。
6. **Windows 手册**：新增 2a 真实包+模板**可复制、含空格路径单引号**启动命令（port 8010）；向量/ASR/生成器独立可选不隐式开启；语料/模型不在 Git（克隆≠可运行）；实验复现命令会写新产物、日常演示不跑评测/prepare/assemble。
7. **人工待复核清单**：24 题 gold 与模板路径、完整事实/可替代证据/适用范围核对方法、「未确认/需修订」记录位置、论文格式/答辩时长等待用户项；后续优先级仅建议未授权。

## 真实验证（详见 verification.md）

文档链接 10/10 存在；serve-corpus/chunk CLI `--help` 与手册参数一致；API 字段（document_id/source_document_ids/related_keywords/source_selection）与源码一致；机器指标与文档表格逐值核对通过（T030/T031/T034 精确值）；主流程抽查 3 项（source_selection 求交、ask 目录驱动入口、chunk overlap 默认兼容）一致。引用已保存的 Astra 浏览器评审（T031-R2/T033-R1）作历史证据，本轮未重跑。

完成后停止，等待 Astra 验收。T036 未发布。
