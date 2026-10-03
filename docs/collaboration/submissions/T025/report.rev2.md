# T025 规划器真实冒烟准备 — A 阶段实施报告

身份：task_id=T025、task_revision=v1、**submission_revision=2、responds_to=T025-R1**、**status=partial、stage=A_ready_for_review**、external_model_calls=0、planner_live_verified=false、tinyagent_integration_kind=reference。rev1 已归档 `*.rev1.*`；返工修复说明见 `fix-report.md`。

**status=partial 表示 B 阶段（真实调用）待用户授权，不代表 A 未做完**——A 阶段任务书各项已完整实施并本地验证。`--mode live` 不因本交付存在而获得授权。

## 概述

把 T024 的文字冒烟计划变为**可复现、可核对的单次 CLI 运行**（沿用 T014 `live-smoke-deepseek.py` 的设计惯例：dry-run 默认、前置校验先于任何调用、结构化 JSON 输出、exit_ok 映射）。新增 `scripts/live-smoke-planner.py` + mock 示例生成器 + 聚焦测试；复用真实执行层（`run_planner_loop` + `DeepSeekPlanner`），不另造 Agent 框架或扩展工具；不启用答案生成器。

## 功能交付（对照任务书 A）

1. **默认 dry-run**（`--mode dry-run`）：零网络、无需密钥。输出配置计划、资料身份/合成标记（manifest/模板 SHA-256 + 逐文档哈希与 is_synthetic）、预算（≤4 次规划 HTTP、max_tokens=300、零重试、单次 20s/总 30s）、预期核对表。**核对表实测列一律「待实际运行核对」（pass=null），不用任何脚本/模拟结果冒充真实模型**。固定合成题编译进脚本（「查找缓考依据并整理办理草稿」/proc-apply-defer/年级 2023），不接受改写。

2. **调用前配置核对（任何请求之前，不符则零请求非零退出）**：
   - live：配置端点必须是官方 `https://api.deepseek.com`、模型 `deepseek-flash`、max_tokens=300；**任意 `DEEPSEEK_BASE_URL` 不当作已授权官方地址**（实测拒绝）；密钥仅经现有环境变量加载，**只记录存在性布尔**；
   - 语料解析成功、非空、**全部 is_synthetic=true**；模板含固定事项；
   - mock：`--mock-base-url` 用**标准 URL 解析**严格校验（T025-R1）：完整主机名必须恰为 `127.0.0.1`/`localhost`/`::1`，拒绝 userinfo、畸形端口、前缀伪装（`http://127.0.0.1.example.invalid`、`http://localhost@example.invalid` 实测拒绝、零请求非零退出）；全程标注「mock 联调（模拟服务，非真实冒烟）」，**不静默作为 live 的降级分支**。

3. **实际 HTTP 计数**：`CountingHTTPClient` 在**发送处**计数（`http_observed_at_send`），与循环内 `planner_http_attempts` 交叉核对；不按 plan_rounds 推算；零重试（实测失败即停、请求数不再增长）。

4. **完整审计（T025-R1 加强）**：输入快照、语料/模板哈希、实际配置（不含密钥）、preflight 各行、run 状态与 stop_reason、服务端结论文案、实际动作与观察摘要、工具结果/引用、逐轮 provider 审计（request_id/usage/finish_reason 等，**缺失写 null**）。**失败轮已获得的安全审计字段经异常元数据保留进运行记录**（截断/解析失败不丢 id/model/usage/finish_reason；白名单字段，不传播 headers/密钥/原始正文）。仅合成资料内容（测试断言输出无密钥值）。

5. **失败非零退出**：非 completed、技术失败、前置失败 → exit 1；argparse 用法错误 → 2；dry-run 成功 → 0。缺产物按 T024-R1 服务端判定原样记录 partial/stopped（模型结束语仅记录、不作主结论），**不靠补工具凑成功**。`--live` 只运行一次 planner loop（≤4 HTTP、max_tokens=300、20s/30s、零重试、故障即停、不自动再跑一题）；答案生成器不启用。

6. **逐条结果核对表**（6 项）：是否实际搜索 / 草稿存在且事项条件正确 / 引用与直接 service 相同（本地重算 `build_draft` 逐条对照）/ 是否需人工核实（**程序化摘要口径**，不代表人工核对已通过）/ 是否有失败或提前 finish / 是否零自动保存（**静态实现判断**，非运行时监控）。**按实际动作生成，不预写通过结论**（第 6 行静态项 dry-run 即标注 ✓，并非所有行都待运行）；模板见 `checklist-template.md`。

7. **本地 mock 示例**（`smoke-mock-sample.py` → `mock-run.json`）：loopback 显式联调的完整示例输出（full-chain 默认；另有 early-finish 场景可选）。

## 验证摘要（聚焦，真实命令见 verification.md / fix-report.md）

- `tests/test_live_smoke_planner.py + tests/test_deepseek_planner.py` **34 passed**（含 T025-R1 新增 2 项）：dry-run 零网络/核对表不预写结论；**loopback 完整链 发送处计数 = 服务端接收 = 循环计数（3=3=3）**；提前 finish/HTTP 500 → exit 1 保留部分证据零重试；**前缀绕过两例（127.0.0.1.example.invalid、localhost@example.invalid）标准 URL 解析拒绝、零请求非零退出**，正常 loopback 仍接受；**带审计信封的截断响应 → 一次请求 exit 1，plan_error.audit 保留 id/model/usage/finish_reason=length**；无密钥/非官方 base_url 零请求；argparse=2。
- 实跑产出（R1 后重生成）：`dry-run.json`（7/7 前置、exit 0）、`mock-run.json`（8/8、completed、http 3=3=3、核对表全过、exit 0）。

## 修改与新增文件

- 新增：`scripts/live-smoke-planner.py`、`scripts/smoke-mock-sample.py`、`tests/test_live_smoke_planner.py`
- 修改：`README.md`（T025 运行说明与 Windows 命令）
- **T025-R1 触碰**：`scripts/live-smoke-planner.py`（URL 校验/核对表措辞）、`src/campus_assistant/agent/deepseek_planner.py`（失败轮审计）、`src/campus_assistant/agent/workflow.py`（plan_error 审计传递）、`tests/test_live_smoke_planner.py`、`tests/test_deepseek_planner.py`
- 提交另附：`dry-run.json`、`mock-run.json`、`checklist-template.md`、`fix-report.md`；清单见 `changed-files.json`
- 未修改：语料/gold/产品模板/前端、`qa/deepseek.py` 问答协议、Astra 文档

## 简明 Windows 命令

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
# dry-run（默认，零网络）
& .\.venv\Scripts\python.exe scripts\live-smoke-planner.py --mode dry-run --out 'F:\Collage Paper\docs\collaboration\submissions\T025\dry-run.json'
# 本地 mock 示例（loopback，非真实冒烟）
& .\.venv\Scripts\python.exe scripts\smoke-mock-sample.py --out 'F:\Collage Paper\docs\collaboration\submissions\T025\mock-run.json'
# --mode live（B 阶段授权 + 本地 DEEPSEEK_API_KEY 配置后才可执行一次）：
# & .\.venv\Scripts\python.exe scripts\live-smoke-planner.py --mode live --out smoke-result.json
```

## 费用与代理口径（说明，不执行）

- max_tokens=300 只约束输出，不是总费用上限；提示长度不是 token 硬上限；连接失败也不能保证供应商未处理/未计费。
- 如遇系统代理导致 api.deepseek.com TLS 失败，可按既有经验仅对本进程设 `NO_PROXY=api.deepseek.com`（见 env.example 注释）；**不擅自修改系统代理**。A 阶段未查询余额、未发任何探测请求。

## 已知限制

- **B 阶段未授权、未执行**：`--mode live` 真实冒烟待用户明确批准范围（固定一题、官方端点/模型、≤4 次 HTTP、max_tokens=300、零重试）并确认密钥已配置后运行一次；本任务书/历史 T014 授权/本地配置存在均不构成 B 授权。
- mock 示例为 loopback 模拟服务输出（标注模拟），不代表真实模型规划能力；planner_live_verified=false 保持不变。
- 核对表第 4 行为程序化摘要口径（非人工核对结论）、第 6 行为静态实现判断（非运行时监控）；真实运行核对表待 B 实际执行后按实测填写。

完成后停止，等待 Astra 验收 A 阶段。B 未授权，不推进 T026。
