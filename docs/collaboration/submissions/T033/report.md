# T033 真实问答与办事入口联动 — 实施报告（report.md，submission_revision=1）

身份：task_id=T033、task_revision=v1、**submission_revision=1、status=ready_for_review、external_model_calls=0、planner_live_verified=false**。零外部模型调用、无下载/安装、未 commit/push、未修改 Astra 文件/STATUS/CLAUDE。原语料包、T030 gold/冻结、T031/T032 实验与归档全部只读；T032 归档与模板历史快照保留（`archive-v1.0/`、`archive-v1.1/`、`submissions/T032/`）。

## 概述

把 ask 页「相关事项入口」从**硬编码两个合成事项 ID** 改为**读取当前配置模板的明确关键词与来源文档集合**的确定性匹配，真实转专业问答结果可进入对应办理指南：

- **模板入口元数据**：procedure 支持可选 `related_keywords`（无此字段的历史模板正常加载；类型/空白校验）。真实模板 `sicau-transfer-2026` 配置「转专业」并递增版本 1.1→**1.2**（仅加入口元数据，政策正文与 20 条引用未改，引用哈希核对 20/20 通过）；合成模板显式配置「缓考」「复核」（正文/引用未改）。
- **API**：`GET /api/v1/procedures` 增加 `related_keywords` 与 `source_document_ids`（**从模板自身引用去重推导**，不接受模型猜测 ID；仅身份字段，无路径/全文）。
- **入口判定**（确定性主题匹配，**非 Agent 推理/自动版本判断/资格判定**）：按**本次结果快照 query**∩配置关键词确定候选，多个匹配全部列出不擅自选一；**来源约束**——结果指定 document_id 时只给来源集合含该 ID 的入口，**指定 2023 来源不推荐 2026 模板**（提示「当前已配置指南的依据与本次指定文件不同」，不给入口、不自动取消文件条件）；未指定文件时显示版本/适用范围（标题/摘要）与「关键词匹配，办理依据将在办事页重新核对」，不称对用户适用。
- **快照与联动边界**：链接携带该结果的四条件快照与 procedure_id（历史结果用历史快照；后续控件编辑不改旧链接）；**document_id 不进入办事参数**（所选文件仅界定本次问答范围）；进入办事页**只预选事项与恢复四条件，不自动草稿/保存/调用模型**（既有 procedures 页行为）；模板目录异步加载后入口自动出现，**不重复问答请求**；无模板/加载失败/无关键词匹配均无死链接（保留「未配置对应指南」说明）。
- **保留既有行为**：T031 条件恢复/失效文件/重试/转摘录快照行为全保留；合成演示入口行为保留（删除仅依赖固定 ID 的逻辑）；检索/生成/Planner/ASR/资格自查未改。

## 聚焦验证（详见 verification.md）

- 后端：`tests/test_procedures.py` **16 passed**（含入口元数据 2 项）；引用哈希核对 20/20 ok（模板引用未变）。
- 页面：JS 语法 9 页、`check-procedures-behavior` 11 场景、`check-ask-behavior` **38 场景**（T033 五条因果链：2026 正确版本入口/2023 不误导/无来源版本提示/目录晚到不重复请求/无关键词无死链），均 exit 0；桩保持原生 select 语义。
- 本地证据 `entry-api-demo.json`：2026→matched、2023→source_mismatch、无来源→matched、无关→无入口。
- **无真实浏览器工具**：短清单交 Astra（demo-notes.md，serve-corpus 端口 8010），stub/API 不冒充浏览器。

**口径**：这是「关键词+来源集合」的确定性入口，**不宣称用户符合政策、完成审批或真实 Agent 验证**。

完成后停止，等待 Astra 验收。T034 未发布。
