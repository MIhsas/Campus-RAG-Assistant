# T040 验证记录（verification.md，submission_revision=2，responds_to=T040-B）

> 命令真实执行、退出码实测。B 阶段实际外部 HTTP 尝试=**0**（缺密钥前置拒绝）。证据分层：A 阶段验证见 `rev1/verification.md`（原字节归档）；本文档为 B 阶段记录，A/B 不混层。执行环境：Windows 11 / Git Bash；解释器 `F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe`。

## 1. 本地 mock 业务回归（新增脚本）

命令（cwd=`F:\Collage Paper\step2_code\backend`）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' -m pytest tests/test_live_smoke_real_qa.py -q
```

| 轮次 | 结果 | 退出码 |
|---|---|---|
| 首跑 | 2 failed / 2 passed：测试查询未命中合成语料 → 零证据短路，计数断言前提不成立（fixture 问题） | 1 |
| 修正测试查询后 | **4 passed**（未改计数/停止/拒绝逻辑）；脚本补丁后复跑 **4 passed** | **0** |

覆盖：①发送位置计数（HTTP 失败/连接失败各占一次）+ 技术失败即停 + 后续题 not_attempted + 供应商状态已观察值（500 实记/连接错误 null）；②业务 insufficient_evidence 可继续 + answered 记录完整（paragraph→E 映射、citations、generation_meta、本地/供应商双状态）；③前置失败（A 材料缺失）零外部请求（mock client 零调用）+ 非官方 endpoint 官方门拒绝；④零证据本地短路零尝试。全部 mock 注入（FakeClient），零网络。

## 2. dry-run 前置核对与 --live 入口执行（run-1）

命令（cwd=`F:\Collage Paper`；下为可复制 PowerShell 形式）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\live-smoke-real-qa.py'
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\live-smoke-real-qa.py' --live
```

| 项 | dry-run | --live（run-1） |
|---|---|---|
| A 身份核对 | **通过**（材料 SHA 三处一致×4、输入 SHA 未漂移×10、四题 E/messages 与 A 一致，UUID 不作差异） | 同左 |
| 配置核对 | 失败：DEEPSEEK_API_KEY 不存在/为空 → 零请求拒绝 | 同左 |
| external_http_attempts | 0 | **0** |
| 四题 outcome | dry_run_not_sent | **not_attempted×4** |
| 退出码 | 1（前置拒绝，预期） | **1**（前置拒绝，预期） |
| 输出 | 无（dry-run 不写目录） | `.cache/real-qa-smoke/T040-B/live-results.json`（拒绝记录，已复制到本目录） |

## 3. 密钥/环境核查（仅存在性；未读取或输出任何值/全量环境/headers）

| 检查 | 结果 |
|---|---|
| 进程环境变量名（DEEPSEEK*/CAMPUS*，含非沙箱） | 无任何匹配项；`DEEPSEEK_API_KEY` 存在性=false |
| Windows User / Machine 级 `DEEPSEEK_API_KEY` | 两级均不存在 |
| 仓库 .env / 启动脚本 | 无 .env；密钥机制=环境变量（windows-runbook：密钥=环境变量，不落日志/报告） |

结论：密钥在本机任何可合法读取的位置均不存在；按工单缺密钥→零请求非零退出、如实提交，**不向用户索取密钥文本**（密钥不得进入聊天/报告/日志）。

## 4. A/B 材料保全核对

| 项 | 结果 |
|---|---|
| A 九件归档 | `rev1/` 齐备；dry-run.json 归档哈希 `31babb70…` 与原件一致 |
| A 四件材料原字节 | submissions 原位 == rev1 == `.cache/real-qa-smoke/T040-A/` 三处一致（前置核对项之一） |
| 输入/源文件 SHA | input-hashes.json 记录的 10 项全部未漂移（questions `4e39229e…`/freeze `8c289b2a…`/manifest `b05c3755…` 等） |

## 5. 已知记录瑕疵（如实保留，不伪造）

run-1 的 live-results.json `attempt_accounting.ask_calls=0` 未计入前置 4 次本地 extractive 核对（**external_http_attempts=0 准确**）。脚本计数已修正（ask_calls 含前置 extractive 并注明“非模型次数”）；按原样保留 run-1、换目录重跑记录刷新被执行环境权限分类器持续拦截（瞬时错误后拒绝），按其指引未换途径重试、未手改机器记录。

## 6. 未验证/边界

- **B 真实生成未执行**（stage=B_not_started）：无模型答案/usage/供应商数据；live_verified=false（待 Astra 认定）；不伪造价格/费用。
- 答案忠实性/拒答/现行性均未验证；核对框架见 live-review-notes.md（无评价对象）。
- 未改产品/适配器/提示/gold/冻结/语料/模板/用户意见；未跑全量/UI/ASR/Agent/三模式/向量；零 commit/push、无下载安装。
