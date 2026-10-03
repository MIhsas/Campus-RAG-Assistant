# T013 DeepSeek 生成适配与本地联调 — 实施报告

身份：task_id=T013、task_revision=v1、submission_revision=1、status=ready_for_review。
**live_verified=false，external_model_calls=0（本轮未向任何外部生成接口发送请求）。**

## 概述

实现可配置的 DeepSeek HTTP AnswerProvider（T012 协议），使 /ask generated 模式经过真实序列化、HTTP 响应解析与引用校验的完整链路；用本地 loopback 模拟服务完成一次全链路联调，并准备独立 live 冒烟脚本（默认 dry-run，本轮不执行）。**模拟 HTTP 结果不是 DeepSeek 真实回答，已在输出中标注。** 未读取开发工具凭据，未新增依赖（复用 httpx 0.28.1）。

## 官方依据（2026-09-22 经 curl 核对官方页面）

- 发布页：V4.1 Flash 模型名 `deepseek-flash`（`deepseek-v4-flash` 兼容路由）。
- JSON Output：`response_format={"type":"json_object"}`；提示词须含 "json" 字样与结构示例；max_tokens 要足够；`finish_reason="length"` 表示内容截断。
- API 参考：`POST /chat/completions`；`thinking={"type":"disabled"}` 关闭思考（默认开启；`reasoning_effort:"none"` 亦可）。
- 实施仅核对上述参数，未做额外模型选型。

## 1. Provider 与配置（`qa/deepseek.py`）

- `DeepSeekAnswerProvider`：query/filters/实际 evidence 清晰结构序列化（system 含两种 JSON 结构示例与短说明，要求每段 evidence_ids、保留条件/数字、不足则说明不足、摘录内容不作指令）；只有本次装入的原文进上下文，无 gold。
- 非流式（`stream=false`）、非思考（`thinking={"type":"disabled"}`，配置记录在请求体与测试断言）、max_tokens=1500、超时 30 秒、无自动重试、无“修 JSON”循环。
- 路径单一规则：`base_url.rstrip('/') + '/chat/completions'`（不重复 /v1）；本地 mock URL 仅由测试/脚本注入，不经用户问答请求指定。
- 成功返回解析 `message.content` 为 JSON 后交 `validate_generation`；空内容、非法 JSON、`finish_reason=length` 截断均为生成失败（502），不展示为完整答案；HTTP 401/429/5xx、超时、连接失败统一映射为安全中文 `user_message`，不输出 Authorization、服务原始异常内容或密钥，不误报为“无相关材料”。
- 配置：`CAMPUS_GENERATOR=deepseek` + `DEEPSEEK_API_KEY`（必需）+ 可选 `DEEPSEEK_BASE_URL`/`DEEPSEEK_MODEL`；默认不启用，显式启用且配置齐全才注入（`provider_from_env`）；启动无探测请求；`env.example` 仅占位值。status 的 `generator_configured` 只代表本地配置完整；`generator_identity=deepseek:deepseek-flash`（alias 非固定权重 revision）。/health/ready 未改。
- 同步 HTTP 经 `starlette.concurrency.run_in_threadpool` 调用，不阻塞事件循环（最小改动，保留既有测试契约）。

## 2. 用户体验与审计信息

- 复用 /ask 既有生成操作与段落引用渲染；真实配置未启用时“生成答案”禁用（T012 页面行为，本轮未改页面）。生成失败用户可明确点击“整理依据”；无自动摘录顶替。提交快照/筛选/重试规则保留（本轮全量回归保持通过）。
- `generation_meta`（可选 metadata 扩展，fake 契约兼容）：实际响应 model、供应商 request id、usage、耗时、配置 max_tokens、finish_reason；供应商未返回字段为 null，不伪造费用/用量；每次调用本地构造，不落共享全局状态。T012 的 RecordingProvider（无 metadata）测试保持通过。

## 3. 验证与证据区别（详见 verification.md）

- loopback mock 全链路演示（`mock-integration.json`）：/ask → provider → HTTP → JSON → 引用 → 响应，7 项内联检查全过（含请求 model/json 模式约束、引用⊆实发证据、服务端解析引用、审计字段、单次调用）。模拟回答带“【模拟输出，非真实 DeepSeek 回答】”标记。
- 12 项新测试：有效答案全链路、材料不足、坏 JSON、非法引用、截断、空内容、HTTP 500（且无重试）、超时映射、配置关闭时摘录可用、显式启用配置、URL 拼接规则。全量既有 pytest 一次：441 passed、1 skipped。
- 本轮未变更任何页面文件，按任务“变更页面才做相关 JS 检查”未跑 JS 检查。
- 本机环境发现：系统代理会拦截 loopback（httpx trust_env=True 经 urllib.getproxies 读注册表代理），mock 联调用 `trust_env=False` 直连；真实调用默认保留系统/环境代理支持。
- live smoke：脚本已备（默认 dry-run 已实跑，无网络、密钥仅 `(redacted)`）；**未执行任何外部调用**。

## 修改与新增文件

完整清单见 `changed-files.json`（相对 `step2_code/backend/`；`..\README.md` 为 `step2_code/README.md`）。

- 新增：`qa/deepseek.py`、`env.example`、`scripts/demo-deepseek-mock.py`、`scripts/live-smoke-deepseek.py`、`tests/test_deepseek_provider.py`
- 修改：`api/ask.py`（线程池 + 安全错误消息 + generation_meta）、`qa/providers.py`（metadata 约定文档）、`main.py`/`demo.py`（env 注入接线）、两份 README

未修改：Astra 文件、gold、旧提交、页面 static/*、health/ready、检索与评测逻辑。

## 已知限制与未验证项

- **live_verified=false**：未对 DeepSeek 官方服务发过任何请求（external_model_calls=0）；mock 结果不是真实回答。live 冒烟按 `live-smoke-plan.md` 待用户确认密钥配置方式、费用上限与少量调用授权后执行。
- 模型名为 alias，未来供应商侧可能路由到新权重；报告不宣称版本永远不变。
- 真实回答质量、拒答可靠性、校园准确率均未评价。
- Windows 系统代理环境下 loopback 需 trust_env=False（演示/测试已内置）；若真实调用需特定代理，请用系统/环境代理配置。
- 工作区非 Git 仓库（git status 报 fatal），如实记录，未初始化、未重置。

完成后停止，等待 Astra 验收。T014 未发布。
