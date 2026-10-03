# T025 A 阶段验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。按任务书只做三类本地验证 + 前置校验一类；**零外部模型调用、无下载、无安装**；未执行 `--live`。未改 UI 不跑 JS；未改共享核心不跑全量/模型测试。

## 1. 聚焦测试（9 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_live_smoke_planner.py -q -p no:cacheprovider --basetemp .cache/t025b --tb=short -rs
# 9 passed, 2 warnings in 2.63s
# 退出码：0
```

对照任务「三类本地验证」：

- **正常 dry-run 零网络**（`TestDryRun` 2 项）：默认模式 exit 0、`run=null`（未运行 planner）、核对表实测列「待实际运行核对」（pass=null，**不预写通过结论**）；资料身份含 manifest/模板 SHA-256 与逐文档 is_synthetic；无需密钥（delenv 后仍 0）；输出无密钥值。
- **loopback 完整链、attempts 与服务端接收数相同**（`TestLoopbackFullChain`）：真实执行层（run_planner_loop + DeepSeekPlanner）× MockChatServer；**`http_observed_at_send`（发送处计数）= 服务端接收 3 = `planner_http_attempts` 3**（不按 plan_rounds 推算）；status=completed、tools=2；逐轮 audit 3 条齐备、结束语仅记录（planner_summary）；核对表 6 项按实际动作给出（搜索命中、草稿身份/条件、引用与直接 `build_draft` 逐条一致、失败/提前 finish=无）；标注「mock 联调（模拟服务，非真实冒烟）」；输出无假密钥值。
- **提前结束/技术失败非零、保留部分证据**（`TestFailureNonZero` 2 项）：search→finish 缺草稿 → exit **1**、status=partial、**检索结果保留**、核对表标失败项、发送处计数=2；HTTP 500 → exit **1**、stop_reason=planner_error、失败前证据保留、**发送处计数=2=循环计数（零重试）**。
- **前置失败零请求**（`TestPreflightFailsWithoutRequests` 3 项，任务书「配置/资料不符合则非零退出且零请求」）：mock 指向 `https://api.deepseek.com`（非 loopback）→ exit 1、`run=null`（零请求）；`--mode live` 无密钥 → exit 1、零请求、`key_present=false`；live + 非官方 `DEEPSEEK_BASE_URL` → exit 1、零请求（**任意环境地址不当作已授权官方地址**）。
- 用法错误（`TestUsage`）：缺 `--mock-base-url`、错配参数 → SystemExit=2（argparse）。

## 2. 实跑产出（交付物，真实命令）

```bash
./.venv/Scripts/python.exe scripts/live-smoke-planner.py --mode dry-run --out "F:/Collage Paper/docs/collaboration/submissions/T025/dry-run.json"
# 前置校验 7/7 通过；checklist 5 项「待实际运行核对」+ 零自动保存 ✓；exit_ok=True；退出码 0

./.venv/Scripts/python.exe scripts/smoke-mock-sample.py --out "F:/Collage Paper/docs/collaboration/submissions/T025/mock-run.json"
# 前置 8/8；status=completed stop=finished http_send=3 http_loop=3 tools=2
# 核对表全 ✓（搜索命中 1 条、引用 4 条与直接 build_draft 一致、saveable=True/4 项未明确事项如实标注）
# mock 服务端实际接收请求数：3；exit_ok=True；退出码 0
```

`mock-run.json` 为**loopback 模拟服务**输出（marking：mock 联调（本地模拟服务，非真实冒烟）），非真实模型结果。

## 3. 依赖

未安装依赖、未下载模型、requirements 未改。无需 pip check。

## 4. 未验证项

1. **`--live` 真实冒烟未执行**（B 阶段未授权）；真实运行核对表待 B 实际动作填写。
2. 真实模型规划能力未验证（planner_live_verified=false）。
3. 资料语义/真实语料不在本轮范围。
