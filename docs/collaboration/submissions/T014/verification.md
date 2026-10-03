# T014 验证记录（submission_revision=4，重试成功轮）

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。历史记录：`verification.rev1.md`、`verification.rev2.md`、`verification.rev3.md`（首轮失败轮）。

## 1. 首轮失败与诊断（不计费探针）

- 首轮（rev3）：`--live` 退出码 1，`生成服务连接失败`，external_http_attempts=1，证据存档于 `live-results.rev3.json`；按约定未重试。
- 诊断探针（GET https://api.deepseek.com/，无模型调用、零费用）：

```bash
./.venv/Scripts/python.exe -c "<httpx 对照探针>"
# httpx trust_env=True: ConnectError: [SSL: UNEXPECTED_EOF_WHILE_READING] …（系统代理截断 TLS）
# httpx trust_env=False: HTTP 401（直连可达，仅缺鉴权）
# curl https://api.deepseek.com/: HTTP 401
# 退出码：0

NO_PROXY=api.deepseek.com ./.venv/Scripts/python.exe -c "<同探针>"
# trust_env=True + NO_PROXY=api.deepseek.com: HTTP 401（provider 现有传输路径经 NO_PROXY 直连可达）
# 退出码：0
```

结论：失败根因为**本机系统代理截断该域 TLS**；`NO_PROXY=api.deepseek.com` 可让现有代码路径直连——**零代码改动**，前置门（合成语料、配置官方值、退出码）全部保持。

## 2. 重试运行（用户授权，同一 CLI）

```bash
set -a && . ./env.local >/dev/null 2>&1 && set +a
NO_PROXY=api.deepseek.com no_proxy=api.deepseek.com \
  ./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py --live --answer-preview-chars 400 \
  --full-answers-out "F:/Collage Paper/docs/collaboration/submissions/T014/live-answers-full.json" \
  > "F:/Collage Paper/docs/collaboration/submissions/T014/live-results.json" 2> .cache/t014-live2-stderr.txt
# 退出码：0
```

实际输出（完整见 `live-results.json`）：

- 调用前审查：config_resolved=官方 endpoint / deepseek-flash / max_tokens 1500。
- Q1：outcome=`generated`、`http_success=true`、`generation_success=true`；回答“缓考申请须经所在学院批准，报教务处备案后方可生效。”引用 E1。
- Q2：outcome=`short_circuit_no_evidence`；本地 `no_hits`、0 字符；`insufficient_reason=无可用证据，未调用生成器。`
- 计数：local_retrieval_calls=2、ask_requests=2、external_http_attempts=1、external_model_calls=1、retries=0。
- 真实审计：request_id=`52f8d636-6ab2-44e4-8632-4bebebe6e68a`；usage prompt=370/completion=37/total=407；latency_ms=984；finish_reason=stop；model=deepseek-flash。
- `exit_ok=true` → 进程退出码 0。

## 3. C 阶段人工核对

见 `live-review-notes.md`。五项逐条：Q1 表述合格（学院批准+教务处备案，回答句=E1 原文末句）；引用 ⊆ 实发证据且原文逐字支持；无附加要求/部门/条件；Q2 本地短路如实记录、无门禁时间编造；接口/生成/核对分别记录。证据原文（同 filters 本地重放）：E1=`第二条 学生因病或其他特殊原因不能参加期末考试的，应当在考试前提出缓考申请。缓考申请须经所在学院批准，报教务处备案后方可生效。`（syn-parse-txt-001/9df6bfbd98df733e/[0,63)）。

## 4. 密钥泄漏检查

```bash
./.venv/Scripts/python.exe -c "<比对密钥是否出现在提交目录/stderr>"
# key leaked: NONE
# key in stderr: False
# 退出码：0
```

## 5. 未验证项 / 边界（如实标注）

1. `live_verified` 由 Astra 验收认定，本记录不自行宣称。
2. 答案质量仅为两题合成样本；真实语料、拒答可靠性、校园准确率未评价（Q2 短路≠模型拒答验证）。
3. 常态化运行依赖 `NO_PROXY`（系统代理问题）；代理适配需未来任务（本修订零代码变更，未重跑全量 pytest/JS/embedding）。
4. 累计外部 HTTP 尝试 2 次（首轮失败 1 + 本轮成功 1），各自在单轮 ≤2 授权内。
