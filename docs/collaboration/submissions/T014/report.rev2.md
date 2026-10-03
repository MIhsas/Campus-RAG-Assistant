# T014 A 阶段定向修复报告（submission_revision=2）

日期：2026-09-26。responds_to=T014-R1。task_revision 保持 v1。**status=partial、live_verified=false、external_model_calls=0。** 本返工单不是 --live 授权；B/C 仍未授权、未执行。

## T014-R1 三项修复（限冒烟脚本、必要只读属性、少量测试）

### 1. 恢复真实调用前的材料与配置核对

- **合成语料门**（`validate_corpus`，任何请求之前执行）：语料须解析有效、非空且所有文档 `is_synthetic=true`；无效、空或非合成语料 → 中文原因 + 退出非零，**不触发 provider**（Astra 探针 `non_synthetic_fake_generate_calls=1` 的场景现已 0 次调用并 exit 1）。
- **实际配置审查**：摘要区分「计划配置」（本任务授权官方值）与「已解析配置」（从实际 provider 的只读属性 `base_url`/`model`/`max_tokens` 解析出 endpoint 等），不再用计划值冒充实际配置（探针中注入 loopback/local-test-model 却显示官方地址的问题已修复）。`qa/deepseek.py` 为适配器补充只读 `base_url` 属性。
- **调用前输出**：审查摘要经 `emit` 在**首次 HTTP 之前**输出并 flush（CLI 写 stderr，结果 JSON 仍为 stdout 单文档；测试注入 recorder 验证顺序）。dry-run 不构造 provider、不读密钥值、不联网，`config_resolved=null` 并注明。
- **CLI --live 官方核对**：解析出的 endpoint/model/max_tokens 与本任务授权值（https://api.deepseek.com/chat/completions、deepseek-flash、1500）不符即**先拒绝**，不向未授权地址发请求（实测 loopback+local-test-model 被拒、0 次调用）。显式测试注入仅跳过官方数值核对，语料门与退出码规则照常。不做通用 URL 安全框架。

### 2. 前置失败非零退出

- 生成器未配置（`--live` 且 factory 返回 None）：记录中文原因“生成器未配置…本次未调用任何模型”，`exit_ok=false` → 进程退出码 1（探针 `missing_provider_exit_ok=true` 已修复）。
- 无效/空语料（含 dry-run）：`exit_ok=false`（探针 `invalid_corpus_dryrun_exit_ok=true` 已修复）。
- 字段口径：原 `http_status_code`（实为本地 /ask 状态）改名 `ask_http_status_code` 并附口径说明——非供应商原始 HTTP 状态，未知供应商状态不猜测。

### 3. 保留项（未动）

预览/完整审计分离、`--answer-preview-chars` 1—2000 硬限（非 token/费用限制）、无重试、首次技术失败立即停止、两道题与第二题 no_hits 本地短路逻辑、题集与 gold 未改。

## 验证（仅相关本地验证，无外部调用）

- 相关测试 **21 passed**（`test_live_smoke_script.py` 9 项含三条因果链 + `test_deepseek_provider.py` 12 项契约回归）；未重跑全量/JS/embedding/下载模型。
- 三条因果链 CLI 实证（完整命令与输出见 verification.md）：
  1. 非合成语料（`is_synthetic=false` 夹具）→ 退出码 1、0 次 provider 调用、0 次本地检索；
  2. `--live` 缺密钥 → 退出码 1、“生成器未配置…本次未调用任何模型”；
  3. `--live` 配置不符（loopback+local-test-model，即探针场景）→ 退出码 1、“已拒绝调用”并展示已解析配置，0 次外部调用。
- 正常 dry-run 退出码 0：审查摘要（含 planned/resolved 分离）于 stderr 先行 flush，Q1 证据 E1—E3 共 214 字符、Q2 no_hits。
- 现有成功/HTTP 失败测试沿用通过（生成成功/失败记录与退出码行为未回归）。

## 修改与新增文件

- 修改：`scripts/live-smoke-deepseek.py`（前置检查/配置审查/退出码/字段口径）、`tests/test_live_smoke_script.py`（+6 项前置用例）、`src/campus_assistant/qa/deepseek.py`（只读 base_url）、`README.md`（前置检查说明）
- 完整清单见 `changed-files.json`；revision 1 历史副本：`report.rev1.md`、`verification.rev1.md`、`submission.rev1.json`、`changed-files.rev1.json`、`smoke-plan.rev1.json`

## 剩余授权条件（B/C，未变）

1. **调用授权**：批准向 `https://api.deepseek.com`（model=deepseek-flash）以两道合成问题发最多两次 HTTP 尝试（max_tokens=1500、无重试、首次技术失败即停）。
2. **本地密钥配置**：`CAMPUS_GENERATOR=deepseek` + `DEEPSEEK_API_KEY`（本地环境变量，不进聊天/报告；可另设费用上限）。

两项齐备后方可 `--live`（届时新增 `live-results.json` 与 C 阶段人工核对记录）。完成后停止，等待 Astra 验收 A 阶段。T015 未发布。
