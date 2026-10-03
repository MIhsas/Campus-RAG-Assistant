# T024 v1：DeepSeek 结构化规划适配与离线联调

日期：2026-09-27。执行：MiMo v2.6 Pro；验收：Astra。

## 目标

在 T023 两工具执行层上实现可配置的 DeepSeekPlanner，让模型根据工具观察选择下一动作。完成真实 HTTP 协议适配代码、正常入口装配、页面模式表达和本地模拟服务联调。本任务不授权外部模型请求；交付仍为 planner_live_verified=false，不得称已验证真实 Agent。

先读 STATUS、PROTOCOL、PROJECT_CONTEXT、T023-R2。TinyAgent 维持 reference；不引其代码或依赖。

## 实施范围

1. **适配器**：实现现有 Planner 契约；沿用 T013/T014 已验证的 DeepSeek 连接参数与错误处理惯例（可读官方文档核对）。严格结构化 JSON 动作 call/finish/awaiting_input；动作类型、工具、参数在执行前验证。不要解析自由文本 ReAct，也不索取或保存 Thought。规划器只决策，不能生成政策答案替代工具证据。
2. **有效观察**：目前 observations 只有工具名/status，不足以支持下一决策。加入有界、必要的真实结果摘要：检索命中数及少量证据/来源标识，草稿 saveable/待核实项/实际 procedure_id。保留用户条件快照，语料文本明确作为数据。不要把全库、历史记录、密钥发送给规划器。定义清晰字符预算与截断标记。提示词包含当前两工具声明与配置事项列表，禁止凭空猜事项 ID。
3. **生命周期和完成语义**：每次运行独立。≤4 轮、≤6 工具、每轮至多一次规划 HTTP、零自动重试；单次超时及单调总时限，超时后不再调度。工具/规划异常转换成可解释失败或 partial，保留已完成结果；计数区分 HTTP 尝试与工具执行。finish 不能把先前失败或未完成任务伪装成全部成功；awaiting_input 指明缺什么。同步模型调用放在线程池，不阻塞 async 路由；如实承认在途调用无法强制撤销。
4. **条件和结果身份**：用户筛选不允许模型改写。工具仍仅 search_policy/build_checklist_draft，不开放生成问答、保存/删除、文件、Shell、任意 URL。当前用户已选事项不得被规划器悄悄换成另一个；若需换事项，返回待确认提示。本轮不做自动保存。所有草稿交接以实际结果身份与快照一致为前提。
5. **正常入口**：serve-corpus.py 加独立显式规划开关（例如 --planner deepseek），默认关闭，与 --generator 独立；本地环境密钥配置复用现有方式，不打印或读取密钥做盘点。启动/status/固定流程零规划请求。状态区分 off/simulated/deepseek、已配置与已联调验证；demo-campus 始终显式模拟，不因环境配置切到真实服务。
6. **页面**：workflow 按实际模式显示固定/模拟/DeepSeek 规划按钮与提示，用户显式点击才执行。保持快照、严格年份、失败清空旧结果、手动办理交接；呈现实际工具事件、部分完成和缺输入，不虚构实时进度或模型思考。仅改必要 UI，不做全面重设计。

允许路径：backend 的 agent、api/agent.py、main.py、serve-corpus.py、workflow.html、必要状态/入口说明、对应聚焦测试与脚本、README/env.example、submissions/T024。若抽取少量共享 HTTP 组件，保持现有问答协议且补对应回归。无需安装依赖或下载模型，不改语料/gold/已验收模板规则、不动 Astra 状态任务文档。

## 聚焦验收

- 本地 loopback mock 串通真正适配器：搜索→观察→草稿→finish；第二轮输入确含第一轮实际观察，结果/引用对照直接 service。模拟输出明确标注，mock 不进入正式启动默认路径。
- 同一 app 两次运行独立，第二次条件不串；模型试图放宽条件或改用户事项被拒，原条件不丢。
- 一次成功工具后规划失败，保留部分结果且不报 completed；finish/缺输入明确。覆盖非法 JSON/截断和一个 HTTP 失败即可，不建立重复大矩阵。
- 启动、status、固定流程不调用规划器；仅显式规划请求触发，最大尝试预算及无重试用计数验证。测试用 loopback、trust_env=False，不能访问官方模型服务。
- 页面正常模式、模拟模式、失败/partial 的少量行为检查及 JS 语法；只跑改动影响到的回归，不跑全量/ASR/embedding。

## 交付

submissions/T024/ 四件（report.md、verification.md、submission.json、changed-files.json），另附 mock-planner-trace.json、demo-notes.md、live-smoke-plan.md。轨迹要区分适配器 HTTP mock 与脚本规划器，记录轮次、实际动作、结果状态、attempts、模型审计字段（缺失写 null）。密钥不得落盘到报告。

live-smoke-plan 仅准备下一步真实冒烟：合成资料、预期最多轮次/调用数/max_tokens、故障即停、费用口径；写清还未获得调用授权，不运行。无需因此停止本轮本地开发。

submission_revision=1、status=ready_for_review、tinyagent_integration_kind=reference、planner_live_verified=false、external_model_calls=0。提交后停止，等 Astra 验收，不推进 T025。
