# T031 指定文件/版本检索与页面闭环 — 实施报告（report.md，submission_revision=1）

身份：task_id=T031、task_revision=v1、**submission_revision=1、status=ready_for_review、external_model_calls=0、planner_live_verified=false**。零外部模型调用（本地 BGE 为既有模型，无下载/安装）、未 commit/push、未修改 Astra 文件/STATUS/CLAUDE、T030 v1.3 题集/gold/冻结/历史结果与真实包 v1.1 全程只读（收尾核验哈希 `5fde70a3…`/`fd2f2476…` 未变）。

## 概述

实现**用户显式选择单份政策文件**作为独立可选检索条件：与现有四项适用条件（校区/学生类型/入学年份/查询日期）**求交，交集先准入后 TopK**；贯通 search/ask 页面（选择器、提交快照、重试/转摘录/复制/历史恢复、互跳、空态区分）。**未选择时行为兼容**（实测：baseline 命中序列与 T030 存储排名 30/30 逐项一致）；**条件冲突不自动放宽**（所选文件被排除→无准入、无回退）。来源选择只来自用户，不从查询或答案自动推断版本。

## 交付物

| 文件 | 内容 |
|---|---|
| [experiment-report.md](experiment-report.md) | 10 题×3 模式对照（无选择 vs 明确文件选择）；**「增加用户文件选择条件后的辅助检索对照」口径**，不宣称算法提升 |
| [api-demo.json](api-demo.json) | 真实包本地 API 演示：2023 vs 2026 转专业同题对照、文件+日期排除、未知 ID 422、/ask 证据范围 |
| [demo-notes.md](demo-notes.md) | 无真实浏览器工具如实声明 + Astra 可运行命令/端口/11 项短检查表 |
| [T030-doc-errata.md](T030-doc-errata.md) | T030-R3 并入的 4 项非阻断文案勘误（不改 T030 已验收数据） |
| [verification.md](verification.md) | 命令/退出码、聚焦验证、一致性 |
| [continuation-progress.md](continuation-progress.md) | 分步执行轨迹 |
| 数据 | `data/evaluations/sicau-rag-source-selection-v1/`：selection-map.json（跑前冻结）、freeze.json（映射+实现+模型身份）、experiment.json（逐题输出） |

## 实现要点

- **后端**：`SearchRequest.document_id: str | None`（AskRequest 继承）；None=全部，空串/非法类型/未知 ID→**422**（不静默改全部）；`GET /api/v1/search/documents` 目录（身份/元数据字段，无路径/全文/密钥，稳定排序，未配置返回清晰不可用状态）；新增 `retrieval/source_selection.py`，`execute_search` 统一求交（BM25 全库 IDF 保持；空交集不回退）；`source_selection` 摘要（id/title/version、选择前/最终可准入数）与 `filter_summary` 四条件口径**分开计数**；search/ask 共用同一实现。不重建索引/不重编码文档；历史无 document_id 调用不受影响。
- **前台**：「资料范围：全部资料 / 指定文件」（标题+版本标签、重名短 ID、默认全部、可清除；「仅在所选文件内检索；不代表该版本现行有效」）；提交快照含 document_id，结果行显示实际来源范围，控件后续变化不篡改旧结果；重试/生成失败转摘录/复制/历史恢复均用该结果快照；旧历史缺字段按未选择并标注；来源失效保留提示不默认为全部；/search↔/ask 互跳携带 query/filters/document_id；办事入口明确「资料范围选择不属于办事模板规则；办理依据将在办事页重新核对」；空态区分「所选文件被条件排除/无准入」与「文件内未检索到命中」，均不宣称学校无规定。
- **验证**：新增 `tests/test_source_selection.py` 20 项（含 encode_documents 计数桩=1、generated mock 证据范围、真实模型调用 0）；既有 search/ask/filters/evidence 共 87 项回归全过；页面行为 search 17 场景 / ask 29 场景（快照保留、空态区分、重试/转摘录原快照、历史恢复零请求）；JS 语法 9 文件全过。

## 实验摘要（详见 experiment-report.md）

10 道指定版本题、映射跑前冻结（10/10 题面文号→目录唯一匹配）：无选择 baseline R/H/M=BM25 0.550/0.600/0.350、Dense 0.500/0.500/0.233、Hybrid 0.400/0.400/0.283；**增加用户文件选择条件后** 三模式 R/H 均 0.900、MRR 0.500–0.548。**q19 全模式不改善（0→0）**（文件内排序问题，如实记录）；差异归因于用户额外条件收窄候选，**不是算法提升**；未选择时混排仍可能存在（已知限制）。

完成后停止，等待 Astra 验收。T032 未发布。
