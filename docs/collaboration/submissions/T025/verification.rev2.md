# T025 A 阶段验证记录（submission_revision=2，responds_to=T025-R1）

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
