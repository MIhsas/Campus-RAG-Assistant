# T025 验证记录（submission_revision=3，stage=B_executed）

> B 阶段执行记录见第 6 节；A 阶段（R1）记录保留于下文与 `verification.rev1.md`/`verification.rev2.md`。

## 6. B 真实冒烟执行（2026-09-28，授权一次，实跑）

```powershell
# env.local 静默载入执行进程（不打印内容）；NO_PROXY=api.deepseek.com 仅当前进程（未改系统代理）
& .\.venv\Scripts\python.exe scripts\live-smoke-planner.py --mode live --out 'F:\Collage Paper\docs\collaboration\submissions\T025\live-run.json'
# LIVE_EXIT=1（status=partial/failed_actions 如实记录，非零退出符合约定）
```

- **执行一次**：固定合成题/proc-apply-defer/年级 2023、`https://api.deepseek.com`、`deepseek-flash`、max_tokens=300；**发送处 HTTP 计数 4 = 循环计数 4 = 服务端应答（4 个 URL 均官方 chat/completions）**，零重试，恰达 ≤4 预算。
- **完整审计**（live-run.json 事件流，真实响应）：4 轮 request_id（35868575…、29a920b9…、45c09a26…、1381357b…）、model=deepseek-flash、usage（666/706/978/1124 total tokens）、finish_reason=stop、latency（765/421/844/796ms）、max_tokens=300——无缺失字段，无失败轮审计丢失。
- **实际动作**：轮1 search_policy 带自造 filters → **业务前被拒**（范围锁生效，快照条件未放宽）；轮2 search_policy ok 命中 3 条（第 2 轮提示含第 1 轮真实观察）；轮3 build_checklist_draft ok（saveable=True、4 步骤）；轮4 finish（结束语仅记录）。
- **产物与对照**：草稿 procedure_id=proc-apply-defer、快照条件=年级 2023；4 条引用与本地 `build_draft` 直接结果逐条一致（程序化对照 ✓）。
- **完成判定**：partial/failed_actions（产物齐但期间 1 条被拒，按 T024-R1 不得标 completed）→ exit 1；失败历史保留、未补工具、**未自动修复后重跑**。
- **核对表**（程序化，live-run.json）：5 ✓ / 1 ✗（「是否有失败/提前 finish」如实失败）；人工核对项单列于 `live-review-notes.md`（程序化摘要 ≠ 人工结论）。
- **密钥与安全**：输出仅 `key_present: true`，交付前断言无 `sk-`/Authorization（值零落盘）；未读取/打印 .env 或完整环境变量；未发额外探测请求；未启用答案生成器。
- `external_model_calls=4`（按实际发送数填写）；**planner_live_verified=false 留待 Astra 认定**。

---

# 以下为 A 阶段验证记录（submission_revision=2，responds_to=T025-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。按返工单只跑冒烟脚本聚焦测试与受影响 planner 异常测试；**未执行 `--mode live`、零外部模型调用、无下载、无安装**；未重跑全量/ASR/页面。rev1 记录归档 `verification.rev1.md`。

## 1. 聚焦测试（34 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_live_smoke_planner.py tests/test_deepseek_planner.py -q -p no:cacheprovider --basetemp .cache/t025r1 --tb=short -rs
# 34 passed, 2 warnings in 15.29s
# 退出码：0
```

- 冒烟 CLI（11 项，含 R1 新增 2）：
  - **URL 前缀绕过拒绝**（`test_prefix_bypass_urls_rejected_zero_requests`）：`http://127.0.0.1.example.invalid`、`http://localhost@example.invalid` → **exit 1、`run=null`（零请求）**、preflight loopback 行 FAIL；正常 loopback（127.0.0.1:18080 / localhost:18080）经标准解析仍接受。
  - **失败轮审计保留**（`test_truncated_response_keeps_audit_single_request`）：带 `id/model/usage/finish_reason=length` 信封的截断响应 → **一次请求、无重试、exit 1**；plan_error 事件 `audit` 含 `request_id=mock-1`、`model=mock-planner（模拟…）`、`usage={prompt_tokens:1,…}`、`finish_reason=length`、`max_tokens=300`、`latency_ms` 非空；输出无 Authorization/`sk-` 值。
  - 原 9 项保持全过：dry-run 零网络/核对表不预写结论/无密钥；loopback 完整链发送处计数=服务端接收=循环计数（3=3=3）；提前 finish/HTTP 500 → exit 1 保留部分证据零重试；非官方 base_url/无密钥零请求；argparse=2。
- 受影响 planner 异常测试（23 项）：`test_truncated_raises` 扩展断言 `e.value.audit` 保留（stub-1/model/finish_reason=length/max_tokens=300）；HTTP 500/非法 JSON/未知动作/审计 null 口径等保持全过。

## 2. 实跑产出（重生成，真实命令）

```bash
./.venv/Scripts/python.exe scripts/live-smoke-planner.py --mode dry-run --out "F:/Collage Paper/docs/collaboration/submissions/T025/dry-run.json"
# 前置 7/7；exit_ok=True；退出码 0（措辞更新：第 6 行标注“静态实现判断（非运行时监控）”）

./.venv/Scripts/python.exe scripts/smoke-mock-sample.py --out "F:/Collage Paper/docs/collaboration/submissions/T025/mock-run.json"
# 前置 8/8；completed；http_send=3=http_loop=3（服务端接收 3）；核对表全过；exit_ok=True；退出码 0
```

rev1 产出归档 `dry-run.rev1.json` / `mock-run.rev1.json`。`mock-run.json` 为 loopback 模拟服务输出（标注「mock 联调，非真实冒烟」）。

## 3. 说明口径校正（随单）

- 核对表**第 6 行「零自动保存」为静态实现判断**（非运行时监控证据，dry-run 即 ✓），并非所有行都待运行——模板与实测栏已标注。
- 核对表**第 4 行通过仅表示“人工核实需求已如实标注”的程序化核对**，不等于人工核对已通过——模板与实测栏已标注。
- CLI 真实参数统一为 `--mode live`（不再用 `--live` 简称）。

## 4. 依赖

未安装依赖、未下载模型、requirements 未改。无需 pip check。

## 5. 未验证项

1. **`--mode live` 真实冒烟未执行**（B 阶段未授权）；真实运行核对表待 B 实际动作填写。
2. 真实模型规划能力未验证（planner_live_verified=false）。
