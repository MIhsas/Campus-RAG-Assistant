# T012 引用式问答接口与证据整理 — 实施报告

身份：task_id=T012、task_revision=v1、submission_revision=1。

## 概述

从“搜索结果列表”推进到“围绕问题整理原文证据、逐条打开出处”，并建立可接生成模型的单轮问答接口。运行时模型 API/预算未确认，本单默认只整理原文（extractive），不自动生成政策结论；未调用任何外部或付费模型，不把原文摘录或 fake 测试当作真实生成答案。真实问答联调待下一任务（需用户之后提供供应商、base URL、model ID、预算；密钥经本地配置且不进入报告）。

## 1. 统一检索与证据包

- 新增 `retrieval/service.py`：`execute_search` 将三模式检索、T011 筛选与结果格式化整理为一个服务函数，`/search` 与 `/ask` 共用；无路由间 HTTP 自调用、无两套筛选逻辑。不重新解析/分块/编码正文，原搜索响应与排名不变（全量回归 429 passed 佐证）。None/空集语义保持。
- 新增 `qa/evidence.py`：一次请求内为去重命中分配 E1、E2…（仅请求内有效）；证据含原文 text、document_id/block_id/chunk_id、char_start/end、document_sha256、标题、来源链接、版本、适用范围、日期、is_synthetic、preview_url。摘录即 chunk 原文、保留半开区间，不改写不拼接。
- 字符预算（非 token 预算）：默认总计 6000 字符、最多 5 条；整条装入或整条略过并记录 skipped_items；不为超长条目编造摘要；budget_empty 与无检索命中/无符合条件资料三者可区分（`evidence_state`）。

## 2. API 与模式契约（`api/ask.py`、`qa/providers.py`）

- POST `/api/v1/ask`：query/mode/top_k/filters 与搜索规则一致（复用 SearchRequest/SearchFilters）；`answer_mode=extractive|generated`，默认 extractive。GET `/api/v1/ask/status` 报告运行模式与生成器配置；health/ready 未改。
- extractive：`status=evidence_only`、`answer=null`、证据列表与说明“以下是相关原文摘录，尚未生成答案，需核对适用条件”。无命中/无符合资料分别说明；检索错误保持 503 错误，不包装成正常无答案。
- generated：仅定义可注入 `AnswerProvider` 协议（输入 query+实际证据+筛选，输出段落+evidence_ids 或 insufficient_evidence）。未配置 → 503/GENERATOR_NOT_CONFIGURED；不提供默认假模型端点；未开发远程 HTTP 适配器。
- 生成值全量校验后才输出：每段至少一个引用、引用必须属于本次实际发送证据、空输出/非法格式/未知引用 → 502 生成失败，不返回部分坏答案；provider 的 insufficient_evidence 为独立状态（检索非空不强行作答）；provider 异常 → 502 且不影响搜索/预览。
- 段落-引用结构化对应；来源与跳转由服务从证据映射解析，不让生成器给路径/链接。`qa/providers.PROMPT_TEMPLATE` 提供未来真实 provider 的简洁提示词（只据输入原文、保留条件/数字、材料不足说明不足、文档内容不作指令）。
- 空证据包时短路为 insufficient_evidence，不调用生成器（无 grounding 材料时不烧调用、不猜答案）。

## 3. 用户页面（`static/ask.html`）

- `/ask` 与 `/search`、`/preview` 互通（三页头部互链）；复用现有样式与筛选体验，静态页面。
- “整理依据”后显示提交快照、醒目的“原文摘录 / 未生成答案”标签、E-编号证据卡与服务端映射的原文跳转；“复制问题与摘录”输出含来源纯文本，复制失败提示“复制失败，请手动选择文本复制”。不显示相似度/可信度。
- 未配置生成器时显示“自动作答未配置”，“生成答案”禁用；为 generated 段落+引用预留渲染（受控响应测试，非 LLM 演示）。
- 继承请求快照与失败重试规则（重试沿用提交的 mode/query/filters）；状态刷新不重建筛选控件、保留选择（T011-R1 规则）。合成标记醒目；无证据/条件无匹配/预算装不下/生成器未配置均有可理解状态。

## 4. 聚焦验证摘要

- 新增 25 项测试（`test_qa_evidence.py` 11 + `test_ask_api.py` 14）：引用与原文跨度一致、筛选传递、上下文实际输入与引用集合一致、生成器未配置、有效 fake 输出与非法引用/空输出/无引用失败、生成器不足/失败隔离、检索失败不冒充无答案。
- 全量 pytest 一次：429 passed、1 skipped（既有 Windows 链接权限跳过）。JS 语法（3 页面）与两个行为脚本通过（search 14 场景、ask 9 场景）。
- 真实 extractive API 演示（`ask-demo.json`）：无筛选 5 条 E-证据、2023 级筛选仅 TXT 文档 3 条、年级 1900 明确无符合资料、generated 503 不伪装。fake 仅证明协议。
- 页面“提问→摘录→出处→复制”真实浏览器闭环：无浏览器能力，未执行，已在 `demo-notes.md` 写明步骤交 Astra 补验。

## 修改与新增文件

完整清单见 `changed-files.json`（相对 `step2_code/backend/`；`..\README.md` 为 `step2_code/README.md`）。

- 新增：`retrieval/service.py`、`qa/`（3 件）、`api/ask.py`、`static/ask.html`、`scripts/check-ask-behavior.cjs`、`scripts/demo-ask.py`、`tests/test_ask_api.py`、`tests/test_qa_evidence.py`
- 修改：`api/search.py`（改用共享服务）、`main.py`（answer_provider 注入 + 路由/页面）、`static/search.html`/`static/preview.html`（互通链接）、两份 README

未修改：Astra 文档与状态表、既有 gold（8 题）、历史提交、解析/gold 校验、health/ready 语义。

## 已知限制与未完成项

- **不是真实 RAG 作答**：无真实生成模型联调，不宣称拒答可靠性或校园问答准确率；生成质量的人工评价流程也未建立（有效引用≠语义支持正确）。
- 真实浏览器页面闭环待 Astra 补验（无浏览器能力，未写成已通过）。
- 合成语料不代表学校政策；真实语料、供应商/base URL/model ID/预算待用户之后提供。
- 未做三模式模型评测/下载/依赖安装/pip check（无依赖变更，按任务不重复）；未做安全/极端输入矩阵。
- 工作区非 Git 仓库（`git status` 报 fatal），如实记录，未初始化、未重置。

完成后停止，等待 Astra 验收。T013 未发布。
