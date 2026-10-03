# T014 B/C 阶段执行报告（submission_revision=4，重试成功）

日期：2026-09-27。task_id=T014、task_revision=v1、submission_revision=4、**status=ready_for_review**。
**external_model_calls=1（本轮成功调用）、live_verified=false（由 Astra 验收认定）。**

## 授权与执行序列

1. **首轮（rev3，已存档）**：授权内一次调用，`生成服务连接失败`（网络层），退出码 1；按约定停止、未重试、证据存档（`live-results.rev3.json` 等）。
2. **诊断探针（不计费）**：定位根因——本机系统代理截断 httpx(trust_env=True) 对 api.deepseek.com 的 TLS（SSL UNEXPECTED_EOF）；直连正常（HTTP 401=可达）。**未改任何代码**，用 `NO_PROXY=api.deepseek.com` 环境变量使 provider 现有传输路径直连，全部前置门（语料合成检查、配置官方值核对、退出码语义）保持原样生效。
3. **重试（用户授权“重试测试”，本轮）**：同一 CLI、同参数，成功，退出码 0。

## B 阶段实际运行（本轮）

```bash
# cwd=F:\Collage Paper\step2_code\backend（密钥由 env.local 注入，不进命令记录）
set -a && . ./env.local >/dev/null 2>&1 && set +a
NO_PROXY=api.deepseek.com no_proxy=api.deepseek.com \
  ./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py --live --answer-preview-chars 400 \
  --full-answers-out "<T014>/live-answers-full.json" > "<T014>/live-results.json" 2> .cache/t014-live2-stderr.txt
# 退出码：0
```

调用前审查通过（endpoint/model/max_tokens=官方值）后发出请求。实际结果（完整审计见 `live-results.json`）：

| 项 | 实际值 |
|---|---|
| Q1（可回答题） | `generated`：回答“缓考申请须经所在学院批准，报教务处备案后方可生效。”引用 E1；`http_success=true`、`generation_success=true` |
| Q2（材料不足题） | `short_circuit_no_evidence`：本地 `no_hits`、0 证据、“无可用证据，未调用生成器。”（HTTP 0 次） |
| 计数 | ask_requests=2、external_http_attempts=**1**（Q2 短路不计模型调用）、无重试 |
| 真实审计 | request_id=52f8d636-6ab2-44e4-8632-4bebebe6e68a；usage 370/37/407；latency 984ms；finish_reason=stop；model=deepseek-flash |
| 证据 | Q1 E1(63)+E2(63)+E3(88)=214 字符 ≤6000；Q2 0 字符 |
| 退出码 | 0 |

## C 阶段核对（详见 `live-review-notes.md`）

- Q1 表述**合格**：学院批准 + 教务处备案齐备，回答句即 E1 原文末句；引用 ⊆ 本次实发证据且原文逐字支持；**无任何附加要求/部门/条件**（未加“医院证明”等）。
- Q2 **合格**：本地短路如实记录、**无门禁时间编造**；明确标注“不是模型拒答验证”。
- 接口成功 / 生成成功 / 答案核对已分别记录。结论：**本次真实问答链路验证通过**；仅为链路与个别行为证据，不构成校园准确率或可靠拒答指标。

## 交付文件

- 实际证据：`live-results.json`、`live-answers-full.json`、`live-review-notes.md`
- 更新：`report.md`、`verification.md`、`submission.json`、`changed-files.json`（本修订零代码变更，清单同 rev2/rev3）
- 历史副本：`*.rev1.*`、`*.rev2.*`、`*.rev3.*`（含首轮失败证据）全部保留

## 已知限制与环境注记

- 本轮依赖 `NO_PROXY=api.deepseek.com` 直连（系统代理截断该域 TLS；探针证据见 verification）。常态化运行需在未来任务为 provider 增加代理配置项——本修订未改已验收代码。
- 累计外部 HTTP 尝试 2 次（首轮连接失败 1 + 本轮成功 1），各自在授权内；模型别名非固定权重 revision。
- 答案质量仅两题合成样本人工核对；真实语料表现、拒答可靠性未评价。

完成后停止，等待 Astra 验收（`live_verified` 由其认定）。T015 未发布。
