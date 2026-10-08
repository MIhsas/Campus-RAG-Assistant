# T031 执行进度（continuation-progress.md）

## T031-R1 返工（submission_revision=2，当前阶段，2026-10-07）

授权：docs/collaboration/reviews/T031-R1.md（两项 P1 页面修复 + 测试桩语义 + demo-notes 校正；不改后端/实验/数据）。

1. [完成] P1-1 跨页恢复：两页 init 停止提前写原生 select；URL 参数进 `restorePending` 快照；选项/目录就绪后 `tryApplyRestoreFilters/tryApplyRestoreDocument` 一次性应用；缺失选项 ghost 保留+提示；状态失败路径同样应用；恢复未完成/目录延迟时提交被明确阻止。
2. [完成] P1-2 失效 ID：原始 ID 保留为明确不可用选项（已失效/目录未确认标注），提交携带原值由服务端 422（绝不转 null 全库）；仅显式「全部资料」撤销；「指定文件」空选阻止提交；ask 页 422/502/503 message 统一展示（附带修复）。
3. [完成] 测试桩：`SelectElement` 原生 select 语义（不存在 option 赋值得 ''、innerHTML 重置选中）；两根因在桩中可复现。
4. [完成] 因果链覆盖：search/ask 各 4 场景（跨页保留+显式提交携带原条件两方向、失效 ID 保留+422、目录延迟阻止、空选阻止+显式切回）。
5. [完成] 验证：check-js-syntax 9 文件 exit 0；search 行为 21 场景 exit 0；ask 行为 33 场景 exit 0。未重跑向量实验/全量测试；数据哈希复核未改（selection-map 42d63bc4…、experiment 57b22f93…、T030 questions 5fde70a3…）。
6. [完成] demo-notes 第 8 项前提修正（未启用生成器按钮禁用；该链由行为测试覆盖；本地模拟路径 scripts/demo-deepseek-mock.py）；fix-report.md；四件更新（submission_revision=2、responds_to=T031-R1）；revision 1 九件归档 rev1/（9/9 核验）。
7. **无真实浏览器工具——P1 两链浏览器复验留待 Astra，不代签。提交后停止。**

## T031 revision 1（已完成，历史记录）

## 起点盘点（已确认）

- T030 revision 3 / dataset v1.3 已验收（T030-R3）；只读输入：questions.json `5fde70a332744b64…`、freeze.json `fd2f2476c1f917ee…`、manifest `34e182f18178c8a8…`。实验输出独立目录 `data/evaluations/sicau-rag-source-selection-v1/`。
- 代码结构：`src/campus_assistant/api/{search,ask}.py`、`retrieval/service.py`、`static/{search,ask}.html`；既有行为脚本 `scripts/check-{search,ask}-behavior.cjs`。
- 工作区既有用户/Astra 未提交改动（CLAUDE/STATUS/README/compare.html 等）非本任务成果，不触碰。
- 并入的 T030 非阻断勘误（T030-doc-errata.md）：q05 手算 rank2 表述、O3 口径（18题 vs 22题×3）、「显著」措辞、O2 指标名。

## 待办队列

1. [完成] 后端契约：
   - 新增 `retrieval/source_selection.py`（normalize/resolve/catalog/intersect/build_source_selection；单文件、不自动推断）。
   - `SearchRequest.document_id: str | None`（AskRequest 继承）：None=全部；空串/非法类型→422；未知 ID→422 SOURCE_DOCUMENT_NOT_FOUND（search/ask 一致，不静默放宽）。
   - `GET /api/v1/search/documents`：解析成功文档目录（title/version_label/policy_group_id/published_at/effective_from/to/is_synthetic），document_id 稳定排序，无路径/全文/密钥；unconfigured/failed 返回 available=false 空目录。
   - `execute_search` 增加 document_id：与四条件**求交后先准入再 TopK**（intersect_allowed）；空交集不回退；BM25 全库 IDF 保持（df/N 建库固定）。filter_summary 保持四条件口径，新增 source_selection（allowed_before/after_selection 区分两段计数）。
   - qa/evidence.py 空态最小扩展：所选文件被条件排除→no_admissible_docs（与文件内无命中 no_hits 区分）。
2. [完成] 前台闭环（search.html/ask.html）：
   - 「资料范围：全部资料 / 指定文件」选择器 + 目录（标题+版本标签，重名短 ID 区分；无版本如实显示）+ 清除选择；提示「仅在所选文件内检索；不代表该版本现行有效」；控件编辑/状态刷新不自动搜索、不清空选择（目录重建保留/挂失效 ghost）。
   - 提交快照含 document_id；结果行显示「来源：…」快照，控件后续变化不篡改旧结果；重试/生成失败转摘录均用提交快照。
   - 空态三分：所选文件被条件排除 / 所选文件内无命中 /（无选择时）原筛选口径；均不宣称学校无规定。
   - 历史：entry 存 document_id；恢复零请求；旧记录缺字段按未选择并标注「旧记录未含来源选择」；来源不在当前目录保留失效提示，不默认为全部。
   - /search↔/ask 互跳链接携带 query/filters/document_id（两侧预填）；办事入口明确「资料范围选择不属于办事模板规则；办理依据将在办事页重新核对」，不携带 document_id。
3. [完成] 聚焦验证：tests/test_source_selection.py 20 项；check-search-behavior.cjs 17 场景（含 T031 快照/空态/重试）；check-ask-behavior.cjs 29 场景（含转摘录快照/历史零请求/旧记录标签）；check-js-syntax.cjs 9 文件全过。
2. [ ] 前台闭环：search/ask 资料范围选择器、快照、重试/摘录/历史恢复、互跳携带、空态区分。
3. [ ] 聚焦测试 tests/test_source_selection.py + 计数桩（不重复 encode）+ 页面行为脚本更新。
4. [完成] 本地 API 演示：scripts/demo-source-selection.py（exit 0）→ api-demo.json。真实包同题 2023（d1fe991c…）vs 2026（5cb2ac21…）三模式命中与 preview 全落所选文件；文件+日期（as_of=2020-01-01）排除→hits=[] 无回退；未知 ID 422；/ask extractive 证据=所选文件。demo-notes.md：**本环境无真实浏览器工具，如实记录不代签**；附 serve-source-selection.py 启动命令（port 8010）+ 11 项短检查表。
5. [完成] 对照实验：selection-map.json **跑前冻结**（42d63bc4…；题面文号/文件名→manifest 目录人工唯一匹配 10/10，无歧义项、不从 gold/排名反推）；scripts/evaluate-source-selection.py（exit 0）→ experiment.json + freeze.json（映射+实现+模型身份；T030 冻结未改）。
   - baseline 与 T030 存储排名 **30/30 逐项一致**（未选分支=旧行为实证）。
   - 汇总（K=5,n=10，逐题重算）：baseline BM25 0.550/0.600/0.350、Dense 0.500/0.500/0.233、Hybrid 0.400/0.400/0.283；selection 三模式 R/H=0.900、MRR 0.500–0.548。
   - **q19 全模式不改善（0→0）**：选中文件正确但 gold 块在文件内未进 top5（文件内排序问题，不调优），如实入 experiment-report §5。口径=「增加用户文件选择条件后的辅助检索对照」，不宣称算法提升。
6. [完成] T030-doc-errata.md（R3 并入 4 项：q05 rank2 表述、O3 两轮口径、「显著」措辞、O2 指标名；T030 数据不改）。四件+实验报告+演示材料齐：report、verification、submission（submission_revision=1、responds_to=T031）、changed-files、experiment-report、api-demo、demo-notes。
   - 收尾核验：T030 questions/freeze 哈希复核未变（5fde70a3…/fd2f2476…）；聚焦测试 107 passed；行为 17+29 场景、JS 语法 9 文件、演示与实验均 exit 0。

**执行完毕，停止，等待 Astra 验收。T032 未推进。**

## 当前步骤

第 1 项：读后端现有实现（api/search.py、api/ask.py、retrieval/service.py、retrieval/filters.py）。
