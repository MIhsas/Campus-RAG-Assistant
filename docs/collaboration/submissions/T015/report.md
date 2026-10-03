# T015 问答页体验与本机历史 — 实施报告

身份：task_id=T015、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**（仅本地开发与模拟，未发起任何外部模型请求，未重放 T014 付费调用）。

## 概述

在既有 /ask 页面与 API 上串联答辩可用的问答流程：模式表达、引用定位与原文、失败转摘录、可选本机历史。复用现有 ask.html、/api/v1/ask 与 T012 引用契约；**零后端代码变更**（API 未调整，无需兼容性说明）；不引入框架/数据库/Agent/语音/新检索算法。

## 功能交付（对照任务书）

1. **问答模式表达**：按钮区新增说明（「整理依据」只整理摘录不调模型；「生成答案」生成+引用，需配置生成器）；清理过时文案（“需用户之后提供供应商、模型与预算” → “本次运行未启用生成器（本地配置 DEEPSEEK_API_KEY 后可用）”）；等待态区分“整理中…/生成中…”，`busy` 防重复提交（按钮+输入禁用、Enter 拦截）；状态刷新只更新状态区、不触发任何问答请求；保留 query/mode/filters/answer_mode 提交快照（快照行显示方式）与 T011-R1 筛选保留规则（未动）。
2. **引用交互**：生成段落的 E 编号点击 → 滚动定位并高亮对应证据卡（.highlight）；卡片保留“查看原文”跳转、标题、适用范围（标注“资料准入信息，非资格认证”）与可用日期；复制内容含答案/摘录、E 编号与来源（复用既有 plainTextOf，未重复实现）。
3. **生成失败转摘录**：失败态标签“生成失败 / 未返回答案”，提供“查看本次问题的原文依据”——用失败请求的 query/mode/filters 快照发 extractive 请求（实测 filters 不因控件事后编辑被丢弃），不调用模型；生成失败 / 材料不足 / 纯摘录三种结果标签明确区分。
4. **本机历史（默认关闭）**：勾选“在本机保存历史”才写 localStorage（`campus_ask_history_v1`，最多 20 条、新替旧）；保存成功的 generated/evidence_only/insufficient_evidence 结果 + 保存时间 + 提交快照 + 来源（不保存密钥/原始异常）；列表支持查看（纯本地渲染、零请求）、删除单条、清空；恢复视图带“历史结果，资料可能已更新（保存于 …）”横幅；取消勾选提示“已停止保存新结果；已保存的 N 条记录仍保留…”并可清空；存储不可用时提示且不影响问答。页面明示“仅保存在此浏览器本机，不是学校账户记录”。未做云同步/导出/迁移。
5. **Windows 运行说明**（README + env.example 注释）：已验证的 DeepSeek 环境配置指引 + 可选 `$env:NO_PROXY='api.deepseek.com'`（仅当前进程、针对代理路径 TLS 连接失败；不改系统代理/全局环境，未建代理配置模块）；密钥不进文档与页面。

## 验证摘要（相关验证，未重跑全量）

- `check-js-syntax.cjs` 3 页通过；`check-ask-behavior.cjs` **13 场景**通过（原 9 + 新 4：引用高亮定位、失败转摘录保快照且不调模型、历史保存/恢复零请求/删除/清空/开关提示、存储不可用容错）。
- 本地 mock 演示入口实跑（`demo-ask-page-mock.py`，模拟生成器输出带【模拟输出】标记）：/ask 200、status 暴露 mock 身份、模拟生成（E1 引用+标记）、模拟失败（→“可改用原文摘录”）、无证据短路三条路径实测；服务由本会话启动并停止。fake 仅存在于该脚本入口，不进产品启动路径。
- 无后端变更 → 按任务未重跑全量 pytest/embedding/评测。
- **无浏览器工具**：真实浏览器闭环（提问→模拟生成→引用/原文→复制→历史恢复、失败转摘录）未由本会话执行，已提供 [demo-notes.md](./demo-notes.md) 供 Astra 本地核验；stub 证据不冒充真实浏览器证据。

## 修改与新增文件

- 修改：`src/campus_assistant/static/ask.html`（主体）、`scripts/check-ask-behavior.cjs`（+4 场景与 stub 扩展）、`README.md`（/ask 体验与历史、NO_PROXY）、`env.example`（NO_PROXY 注释）
- 新增：`scripts/demo-ask-page-mock.py`（本地演示入口，模拟标记）
- 清单见 `changed-files.json`；未修改：Astra 文档、旧题集/gold、T014 原始证据、后端 Python 源码。

## 已知限制

- 浏览器真实操作未验证（无浏览器工具）；stub 与 mock 属不同证据层级，已在 demo-notes 标明。
- 模拟生成器输出仅为演示标记文本，**不能**作为真实 DeepSeek 证据。
- 历史仅限单浏览器 localStorage；换浏览器/清数据即失效（设计如此）。
- 本任务未新增外部调用；真实生成演示需另行授权（README 有可选命令）。

完成后停止，等待 Astra 验收。T016 未发布。
