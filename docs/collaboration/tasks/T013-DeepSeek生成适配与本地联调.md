# T013 DeepSeek 生成适配与本地联调

日期：2026-09-22。发布 Astra。执行 MiMo v2.6 Pro。task_revision=v1。前置 T012-R1 通过。用户指定运行时模型 DeepSeek V4.1 Flash；开发执行模型仍为 MiMo，两者不是同一用途。

## 目标与授权

实现可配置的 DeepSeek HTTP AnswerProvider，使现有 /ask generated 模式能经过真实序列化、HTTP 响应解析和引用校验工作；本轮用本地模拟服务验证完整接口，后续用户提供密钥与预算后再做官方服务冒烟。不得把模拟 HTTP 结果写成 DeepSeek 真实回答。

允许修改 step2_code/backend/、step2_code/README.md、docs/collaboration/submissions/T013/。复用现有 httpx，尽量不新增依赖。不修改 Astra 文件、gold、旧提交，不引入 Agent、工具调用、多轮、流式或大范围重构。不读取开发工具凭据。本轮不授权向官方或第三方生成接口发送请求；仅允许本地测试 HTTP。不要因为模型已指定就自行扣费、读取现有未知密钥或测试账号。

## 官方依据与实现选择

2026-09-22 核对：[官方发布页](https://api-docs.deepseek.com/zh-cn/news/news260910/)：V4.1 Flash 使用 `deepseek-flash`；[JSON Output](https://api-docs.deepseek.com/guides/json_mode/)：base URL https://api.deepseek.com，Chat Completions 的 response_format 为 json_object，提示词要包含 json 和结构示例，空内容可能发生。实施前只核对相关官方参数说明，不做额外模型选型。

使用 Chat Completions 非流式接口。正式默认 base URL 为 https://api.deepseek.com，model=deepseek-flash；路径拼接按单一明确规则形成 /chat/completions，避免重复 /v1。本地 mock 的 URL 由测试注入，不通过用户问答请求指定供应商 URL。

## 1. Provider 与配置

- 实现 DeepSeekAnswerProvider 对接 T012 协议。query、filters、实际 evidence 以清晰结构序列化；只有本次实际装入的原文作为模型证据，不把评测 gold 放进上下文。
- system 指令给出 T012 的 answer/insufficient_evidence 两种 JSON 结构及短示例，要求每段 evidence_ids，只据原文保留条件/数字，不足则说明不足。JSON 格式有效不等于证据支持有效，沿用服务引用校验。
- 显式关闭流式；按官方支持参数选择非思考模式并记录配置，避免不必要生成成本。合理设置 max_tokens（建议 1500）和超时（建议 30 秒）。不做自动重试或“再让模型修 JSON”循环。
- 对 HTTP 成功返回解析 message.content 为 JSON，再交 validate_generation；空内容、非法 JSON、finish_reason=length 等截断不展示成完整答案。HTTP 401/429/5xx、超时统一映射为可理解的生成错误；不输出 Authorization、服务原始异常内容或密钥，不误报为“无相关材料”。
- 配置使用本地环境变量或明确忽略的本地文件，示例配置只放占位值。建议 CAMPUS_GENERATOR=deepseek、DEEPSEEK_API_KEY、DEEPSEEK_BASE_URL、DEEPSEEK_MODEL；默认不启用，只有明确启用且必需配置齐全才注入 provider。启动不发送探测请求；搜索/摘录一直可用。不要打印环境变量全表。
- status 的 generator_configured 只代表本地配置完整，不能声称服务已验证；展示简洁模型身份。不要更改 /health/ready 的既有整体就绪语义。
- 同步 HTTP 不得直接阻塞 FastAPI 事件循环：用现有框架的线程池调用同步 generate，或合理统一异步协议；选择最小改动并保留既有测试契约。无需做复杂并发系统。

## 2. 用户体验与审计信息

复用 /ask 的生成答案操作和段落引用渲染，真实配置未启用时禁用生成。生成失败允许用户明确点击“整理依据”，不能自动拿摘录伪装成生成答案。提交快照、筛选、重试仍保留。

记录非敏感的实际响应 model、供应商 request ID（如有）、usage、耗时、配置的 max_tokens，供后续实验使用。供应商未返回字段为 null，不伪造费用/用量；不得在共享全局 last_response 上存请求结果造成并发串写。若需扩展 provider 返回结构，用可选 metadata 并保持既有 fake 契约兼容。模型 alias 不是固定权重 revision，报告不宣称版本永远不变。

## 3. 本轮验证边界

使用 loopback 模拟 HTTP 服务做一次 /ask → provider → HTTP → JSON → 引用 → 响应的完整集成演示。模拟服务只在 tests/scripts 的显式测试入口，不混进默认产品运行，不提供给用户假模型开关。使用占位测试密钥。

少量测试覆盖有效答案、材料不足、一个非法引用或坏 JSON、截断、超时/HTTP 失败、配置关闭时摘录可用；检查 request 的 model、JSON 格式约束和实际证据。不要枚举全部状态码和极端输入。最后全量既有 pytest 一次，变更页面才做相关 JS 检查；无依赖变化不重复安装/pip/embedding 评测。

准备独立的 live smoke 脚本，但本单不执行外部调用。脚本默认 dry-run，真正调用必须显式 live 参数，设置最多请求数和输出长度，不自动重试；请求限合成资料。运行前打印无密钥的配置摘要和调用数量。README 说明需用户确认密钥配置方式、费用上限及少量调用授权后再执行，不把脚本存在写成联调通过。

## 4. 提交

submissions/T013/：report.md、verification.md、submission.json、changed-files.json、mock-integration.json、live-smoke-plan.md。身份 task_id=T013、task_revision=v1、submission_revision=1。本任务范围内完成可报 ready_for_review，必须另列 live_verified=false、external_model_calls=0。

报告说明代码、完整命令/cwd/退出码、mock 与真实服务证据区别及未验证项。包含可复制的 Windows 配置/启动方式，密钥用占位值。完成后停止等待 Astra 验收，不自行发起付费请求或推进 T014。
