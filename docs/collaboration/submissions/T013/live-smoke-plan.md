# T013 live smoke 计划（未执行）

**当前状态：未执行。live_verified=false，external_model_calls=0。** 脚本存在不等于联调通过；`scripts/live-smoke-deepseek.py` 默认 dry-run（无网络 I/O）。

## 执行前提（缺一不可，由用户确认）

1. 密钥配置方式：本地环境变量 `DEEPSEEK_API_KEY`（推荐）或其他本地未跟踪方式；密钥不进入报告、日志或提交。
2. 费用上限：明确本轮可接受的调用次数与 token 上限（脚本硬限最多 2 次请求、输出 2000 字符截断、无自动重试）。
3. 少量调用授权：用户明确批准向 DeepSeek 官方服务发送该数量的请求。

## 命令

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'

# 1) dry-run：打印无密钥的配置摘要与计划调用数（无网络）
& .\.venv\Scripts\python.exe scripts\live-smoke-deepseek.py

# 2) 用户确认以上三项后，显式 live（默认 1 次请求，硬上限 2）
$env:CAMPUS_GENERATOR = 'deepseek'
$env:DEEPSEEK_API_KEY = 'sk-REPLACE-WITH-LOCAL-KEY'
& .\.venv\Scripts\python.exe scripts\live-smoke-deepseek.py --live --max-requests 1
```

## 约束与记录

- 请求材料仅限合成语料（脚本自检 `is_synthetic`，不满足即中止不发请求）；查询为“缓考申请需要什么材料”（filter-demo/parse-corpus 合成夹具）。
- 运行前打印配置摘要（model=deepseek-flash、base URL、max_tokens=1500、超时 30s、计划调用数、key_configured 布尔）；密钥只显示 `(redacted)`。
- 成功记录：响应 model、request id、usage、耗时（generation_meta）；失败记录映射后的中文错误。输出截断至 `--max-output-chars`。
- 结果只能证明链路可调用；答案质量需人工评价，不能据此宣称校园问答准确率。
- 真实回答与 mock 证据严格区分：mock-integration.json 是 loopback 模拟，不是 DeepSeek 真实回答。

## 执行后

将 live 输出（脱敏）与人工评价记录另存 submissions 后续任务目录，由 Astra 验收后安排 T014。
