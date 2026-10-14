# T038 元数据补正与未核实资料候选查看 — 实施报告（report.md，submission_revision=1）

身份：task_id=T038、task_revision=v1、**submission_revision=1、status=ready_for_review、external_model_calls=0、planner_live_verified=false、human_review_status=user_review_received_with_open_items（109/3/2 保留）**。旧语料/gold/模板/冻结实验/用户意见只读；零外部模型调用、无下载/安装、未 commit/push；未改 Astra 文件。合并实施一次交付，无新数据库/模型/工具框架。

## 1. 新语料包 v1.2（日期补正，详见 [metadata-crosscheck.md](metadata-crosscheck.md)）

- `data/corpora/sicau-rag-pilot-v1.2/`：20 份原件与 v1.1 **逐字节相同**（块 ID 1031 个不变）；**manifest 唯一差异 = bed3ac `published_at/effective_from: null→2019-11-07`**。
- 证据（真实解析切片）：落款「四川农业大学 2019年11月7日」（f3cdb912）、印发「…2019年11月7日印」（a3536032，**末字解析为「印」不补写「发」**）、生效条款「本办法自发文之日起执行…」（c641f172[135:206]）。
- 复用 prepare-real-corpus.py 构建/核验（均 exit 0）；83eb scope 保留未知、db05e0 日期保持未知。
- 准入变化（现有筛选服务）：as_of=2026-10-03 由 **4/20→5/20**（bed3ac 准入、db05e0 仍排除）；无筛选集合不变。**日期区间核查≠现行有效认证**；历史实验输入仍 v1.1，u03/u04 gold 未改。

## 2. 独立只读候选 API（`POST /api/v1/search/candidates`）

- 复用 SearchRequest 全契约（query/mode/top_k/filters/document_id，未知 ID 422）+ `uncertainty_dimensions`（仅 date/student_type；空/非法/重复/无对应筛选→中文 422）。
- **独立逐文档复核**（不挑 scope_unknown 优先级）：已知 scope 不匹配、未选维度的未知 scope、已知未生效/已失效、effective_from 未知但 effective_to 早于查询日均排除；campus/admission_year 严格保留；双未知须两项均选；候选排除严格已准入集合；document_id 求交不回退。
- 响应含提交快照/维度/candidate_summary/每 hit 真实 unknown_dimensions 与说明；恒标「未通过所选日期或学生类型条件核实，仅供原文核对，不作为已确认适用的答案依据」。候选**不进入** ask evidence、生成 messages、Agent 工具、事项推荐、模板保存；不调用 AnswerProvider/Planner/ASR。
- 实现：`filters.py` 新增独立候选函数（严格函数语义未改）；`service.py` 抽取 `_search_mode` 共用检索（严格/候选同一套 mode 分派与索引，不重建文档索引）；`api/search.py` 新路由。

## 3. 两页显式候选查看（search/ask）

正式成功结果后出现独立区「查看未核实资料」：两个默认未勾选项（日期未核实/学生类型未核实，仅结果快照对应筛选非空才可选）；**仅点击「查看候选原文」才请求**（加载/提交/状态刷新/历史恢复均不自动请求）；请求绑定**结果快照**（query/mode/filters/document_id）；候选不混入正式排名/证据 E 编号/复制/历史；新请求/历史切换/失败清空旧候选（请求序号防串）；空态「当前条件下没有这些未核实候选资料」、失败「候选加载失败」可按候选快照重试；u04 类来源卡标「来源适用范围：未标注（含本科与否未核实）」。

## 4. 生成表达优化（实际 SYSTEM_PROMPT / PROMPT_TEMPLATE）

新增规则：简洁政策含义、不拿「将…修改为」修订决定措辞当回答（引文逐字保留）；不同前提分别说明（主体/条件/数字/例外），不同前提不判版本冲突；同前提冲突无裁定依据时并列提示，不按年份断言版本有效性。**不硬编码 q08/q10 答案、不发送 gold/人工 review、不后处理替换 quote**；JSON 输出/引用校验/HTTP 契约不变。本地检查 build_messages 实际含新规则（mock 只证明传参，不宣称生成质量改善）。

## 验证摘要（详见 verification.md）

真实 API：v1.2 构建/核验 exit 0、准入 4→5、候选三类演示 + 契约 422×4 + 严格无泄漏（candidate-api-demo.json）；后端 11 新 + 85 既有 passed；页面行为 search 23 / ask 40 场景（候选快照/显式请求/旧响应不串）、JS 语法 9 页；旧数据/实验/用户意见 SHA 全部未变。**无真实浏览器证据**（Astra 短清单见 demo-notes）；未实测真实生成质量。

完成后停止，等待 Astra 验收。T039 未发布。
