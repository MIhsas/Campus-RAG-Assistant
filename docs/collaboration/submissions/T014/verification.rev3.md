# T014 验证记录（submission_revision=3，B/C 执行）

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。本修订为真实外部调用执行记录；未重跑全量 pytest/JS/embedding。revision 1/2 的验证记录见 `verification.rev1.md`、`verification.rev2.md`。

## 1. 执行前就绪检查（不输出密钥）

```bash
./.venv/Scripts/python.exe -c "<读 env.local 校验，仅打印布尔>"
# CAMPUS_GENERATOR ok: True
# key filled (not placeholder): True
# base_url: https://api.deepseek.com
# model: deepseek-flash
# key length: 35 | key never printed
# 退出码：0
```

## 2. live 冒烟（授权范围内一次，无重试）

```bash
set -a && . ./env.local >/dev/null 2>&1 && set +a
./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py --live --answer-preview-chars 400 \
  --full-answers-out "F:/Collage Paper/docs/collaboration/submissions/T014/live-answers-full.json" \
  > "F:/Collage Paper/docs/collaboration/submissions/T014/live-results.json" 2> .cache/t014-live-stderr.txt
# 退出码：1
```

实际结果（完整见 live-results.json）：

- `config_resolved`：endpoint=https://api.deepseek.com/chat/completions、model=deepseek-flash、max_tokens=1500（调用前审查与授权一致才发出请求）。
- Q1：outcome=`technical_failure`，error=`生成服务连接失败；可改用原文摘录（answer_mode=extractive）。`，`http_success=false`，`generation_meta=null`，`ask_http_status_code=502`（本地口径，非供应商状态）。
- Q2：outcome=`not_attempted`（首次技术失败立即停止）；本地检索 evidence_state=`no_hits`、0 字符。
- 计数：local_retrieval_calls=2、ask_requests=1、external_http_attempts=1、external_model_calls=1。
- `exit_ok=false` → 进程退出码 1（失败非零语义生效）。

## 3. 失败处理边界（如实记录）

按约定：**未重试、未修复后重跑、未追加诊断请求**。供应商响应不存在（usage/request_id/finish_reason 为 null，未伪造）。连接失败确切原因未诊断；已知环境事实：本机系统代理在 T013 已实测会拦截 httpx(trust_env=True) 连接（记录为背景，非本次结论）。

## 4. 密钥泄漏检查

```bash
./.venv/Scripts/python.exe -c "<比对 env.local 密钥是否出现在提交目录/stderr 捕获>"
# key leaked into submissions: NONE
# key in stderr capture: False
# 退出码：0
```

密钥未进入命令记录、报告、日志或任何提交文件。

## 5. C 阶段人工核对

见 `live-review-notes.md`（逐项表格）。摘要：无生成回答 → 表述/引用/编造类核对不适用且无编造产物；Q2 无门禁时间编造；接口成功、生成失败、答案核对不适用；**不宣称真实问答验收通过**。

## 6. 未验证项（如实标注）

1. 真实生成问答未成功完成（连接失败）——live_verified 待 Astra 认定，当前 false。
2. 答案内容核对（Q1 审批/备案表述、引用支撑）待一次成功生成后补做。
3. 未重跑全量 pytest、JS、embedding（本修订无代码变更）。
4. 连接失败根因未诊断（无诊断请求授权）。
