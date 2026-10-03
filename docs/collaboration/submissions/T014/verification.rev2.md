# T014 验证记录（submission_revision=2，responds_to=T014-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。按返工单只做相关本地验证；未重复全量 pytest、JS、依赖或 embedding 评测。**全程无外部模型调用（external_model_calls=0）。** revision 1 的完整验证记录见 `verification.rev1.md`。

## 1. 相关测试（21 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_live_smoke_script.py tests/test_deepseek_provider.py -q -p no:cacheprovider --basetemp .cache/t014r2-iter2 --tb=short -rs
# 21 passed, 2 warnings in 8.62s
# 退出码：0
```

- `test_live_smoke_script.py` 9 项：沿用成功/HTTP 失败/dry-run 3 项（含 `ask_http_status_code` 口径断言）；新增 6 项前置用例——非合成语料不触发 provider 且非零退出、无效/空语料（含 dry-run）非零退出、缺配置非零退出、审查摘要含实际配置且先于首次 generate、官方配置门拒绝不符（0 调用）、官方配置门放行相符值。
- `test_deepseek_provider.py` 12 项：适配器契约回归（只读 base_url 属性不影响既有行为）。

## 2. 三条因果链 CLI 实证

### 链 1：非合成语料不触发 provider（且非零退出）

```bash
# 构造 is_synthetic=false 的最小夹具于 .cache/t014r2-fake-realish
./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py --corpus .cache/t014r2-fake-realish
# 退出码：1
# errors: ["拒绝调用：语料包含未标记 is_synthetic=true 的文档，本任务仅允许合成资料"]
# external_model_calls=0，local_retrieval_calls=0（调用前即退出）
```

### 链 2：缺配置退出非零

```bash
CAMPUS_GENERATOR=deepseek ./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py --live
# 退出码：1
# errors: ["生成器未配置：需要 CAMPUS_GENERATOR=deepseek 且 DEEPSEEK_API_KEY 非空；本次未调用任何模型"]
# external_model_calls=0
```

### 链 3：审查配置与实际 provider 一致、调用前产生；配置不符先拒绝

```bash
CAMPUS_GENERATOR=deepseek DEEPSEEK_API_KEY=sk-test-placeholder DEEPSEEK_BASE_URL=http://127.0.0.1:9 DEEPSEEK_MODEL=local-test-model \
  ./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py --live
# 退出码：1
# errors: ["已拒绝调用：endpoint 不是本任务授权的官方地址（已解析：http://127.0.0.1:9/chat/completions）；model 不是 deepseek-flash（已解析：local-test-model）"]
# config_resolved: {endpoint: http://127.0.0.1:9/chat/completions, model: local-test-model, max_tokens: 1500, ...}
# external_model_calls=0（拒绝发生在任何请求之前；即 Astra 探针场景，原 exit_ok=true 已修复）
```

“摘要先于调用”的顺序由测试 `test_review_summary_shows_actual_config_before_calls` 用事件序列证明（emit review_summary 事件下标 < 首次 generate 事件下标）；`config_resolved` 取自实际注入 provider（local-test-model/777）而非计划值。

## 3. 正常 dry-run（无网络、无密钥）

```bash
./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py > .cache/t014r2-dryrun-out.json 2> .cache/t014r2-dryrun-err.txt
# 退出码：0
```

- stdout 单一结果 JSON：exit_ok=true、`config_planned.model=deepseek-flash`、`config_resolved=null`（注明 dry-run 未构造 provider）、`review_summary` 含 planned/resolved/corpus/questions/max_tokens。
- stderr 审查摘要先行 flush（含 review_summary 事件与计划配置）；两题检索：Q1 E1(63)+E2(63)+E3(88)=214 字符、Q2 no_hits（短路分支保持，未改题集）。
- 附带修复：stderr 亦包 UTF-8（此前 GBK 写出影响审查存档可读性）。

## 4. 未验证项（如实标注）

1. **真实官方调用未执行**（live_verified=false、external_model_calls=0）；B/C 待用户授权（条件见 report.md）。
2. 按返工单未跑：全量 pytest、JS 检查、embedding 评测、模型下载。
3. 供应商原始 HTTP 状态不可得（适配器映射错误），记录中仅 `ask_http_status_code`（本地口径），不猜测供应商状态。
