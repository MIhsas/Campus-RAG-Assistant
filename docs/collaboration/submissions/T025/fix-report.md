# T025-R1 定向返工 — 修复报告（fix-report）

身份：task_id=T025、task_revision=v1、**submission_revision=2、responds_to=T025-R1**、status=partial、stage=A_ready_for_review、planner_live_verified=false、external_model_calls=0。rev1 四件及 dry-run/mock/核对表模板已归档 `*.rev1.*` 保留。仅改 URL 前置校验、失败轮审计传递及直接相关测试/说明；未执行 `--mode live`、未重跑全量/ASR/页面、未安装、未下载。**status=partial 仍表示 B 待授权，A 各项完整。**

## 修复 1（P1）：mock loopback 限定被前缀绕过 → 标准 URL 解析校验

**问题**（Astra 探针复现）：`host_ok` 用 `startswith`，`http://127.0.0.1.example.invalid`、`http://localhost@example.invalid` 均通过前置检查而实际主机非本地，随后脚本会向外部目标发送合成问题与观察——破坏 A 阶段「仅本地 mock、零外部调用」边界。

**修复**（`scripts/live-smoke-planner.py` 新增 `_is_loopback_url()`）：用标准 URL 解析（`urllib.parse.urlsplit`）校验——

- scheme 限 `http/https`；**完整主机名**必须恰为 `127.0.0.1` / `localhost` / `::1`（准确解析 IPv6、剥离方括号，非前缀匹配）；
- **拒绝 userinfo**（`parts.username/password` 非空即拒——`localhost@example.invalid` 的真主机是 example.invalid）；
- 端口经 `parts.port` 解析校验（畸形/越界端口 ValueError 即拒）；无主机/空主机拒绝；
- **纯解析，不做 DNS 探测**。拒绝时保持**零发送、非零退出**（preflight 先于任何请求构造）。

**回归**（`test_prefix_bypass_urls_rejected_zero_requests`，不扩矩阵）：上述两例 → exit 1、`run=null`（零请求）、preflight loopback 行 FAIL；正常 loopback（`http://127.0.0.1:18080`、`http://localhost:18080`）仍接受（既有完整链/失败用例继续通过）。

## 修复 2（P2）：失败轮已获取审计被丢弃 → 异常元数据保留

**问题**：`deepseek_planner.py` 在解析响应后才建 audit，length/空内容/非法 JSON/非法动作直接抛出；workflow 的 plan_error 固定 `audit=None`——「失败轮保留」不成立。截断响应也可能已计费，已返回字段不得当作未提供。

**修复**（最小异常元数据机制，不重构问答 provider）：

- `deepseek_planner.py`：审计从请求发出即累积（`id/model/usage/finish_reason/latency_ms/max_tokens`，缺失写 null）；每个规划异常经 `fail()` 挂上**截至此刻已获得**的 `e.audit`；信封字段（id/model/usage/finish_reason）一经解析即入审计，**即便随后截断/空/非法也保留**。不传播 headers、密钥、原始响应正文（仅安全字段白名单）。
- `agent/workflow.py`：plan_error 事件的 `audit` 改为 `getattr(e, "audit", None)`——失败轮审计进入最终运行记录。
- 各 Planner*Error 声明 `audit` 属性（默认 None），未收到字段仍为 null。

**回归**：

- `test_truncated_response_keeps_audit_single_request`（冒烟 CLI 级）：带 `id/model/usage/finish_reason=length` 信封的截断响应 → **一次请求、无重试、exit 1**；plan_error 事件审计含 `request_id=mock-1`、`model=mock-planner（模拟…）`、`usage={…}`、`finish_reason=length`、`max_tokens=300`、`latency_ms` 非空；输出无 Authorization/密钥值。
- `test_truncated_raises`（适配器级）扩展断言 `e.value.audit` 保留 stub-1/model/finish_reason=length/max_tokens=300。

## 随单说明整理（非阻断，已统一）

1. **dry-run「零自动保存」是静态实现判断**，不是运行时监控证据——核对表第 6 行实测改为「静态实现判断（非运行时监控）…」；模板补证据层级说明（并非所有行都待运行，第 6 行 dry-run 即 ✓）。
2. **「人工核实已如实标注」为程序化摘要**，不等于人工核对已通过——核对表第 4 行预期/实测明确标注「程序化摘要，不代表人工核对已通过」。
3. **CLI 真实参数统一为 `--mode live`**（不再用 `--live` 简称指代参数）。

## 验证（聚焦，真实退出码）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_live_smoke_planner.py tests/test_deepseek_planner.py -q -p no:cacheprovider --basetemp .cache/t025r1 --tb=short -rs
# 34 passed（冒烟 11 + planner 23，含新增 2 与扩展断言），退出码 0

./.venv/Scripts/python.exe scripts/live-smoke-planner.py --mode dry-run --out .../dry-run.json
# 前置 7/7，exit_ok=True，退出码 0（重生成，措辞更新）

./.venv/Scripts/python.exe scripts/smoke-mock-sample.py --out .../mock-run.json
# completed、http 3=3=3、核对表全过、exit 0（loopback 模拟服务）
```

按返工单未执行 `--mode live`、未重跑全量/ASR/embedding/页面、未安装依赖、未下载模型。

## 未验证项

1. `--mode live` 真实冒烟未执行（B 未授权）；真实运行核对表待 B 填写。
2. 真实模型规划能力未验证（planner_live_verified=false）。
