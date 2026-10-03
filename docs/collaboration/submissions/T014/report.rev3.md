# T014 B/C 阶段执行报告（submission_revision=3）

日期：2026-09-27。task_id=T014、task_revision=v1、submission_revision=3、**status=partial（B 阶段真实调用失败）**。
**external_model_calls=1（实际）、live_verified=false（由 Astra 验收认定）。**

## 授权与前提（执行前确认）

- 用户明确授权（2026-09-27）：官方 deepseek-flash、两道合成题、最多 2 次 HTTP、max_tokens=1500、无重试。
- 本地密钥经 `step2_code/backend/env.local` 配置（本地文件，不进提交/日志）；执行前就绪检查通过（仅输出布尔，未显示密钥）。授权范围已记录，密钥未记录。

## B 阶段执行（一次，未重试）

命令（cwd=`F:\Collage Paper\step2_code\backend`，密钥由 env.local 注入命令环境，不进命令记录）：

```bash
set -a && . ./env.local >/dev/null 2>&1 && set +a
./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py --live --answer-preview-chars 400 \
  --full-answers-out "<T014>/live-answers-full.json" > "<T014>/live-results.json" 2> .cache/t014-live-stderr.txt
# 退出码：1
```

调用前审查通过后才发出请求：实际解析 endpoint=`https://api.deepseek.com/chat/completions`、model=`deepseek-flash`、max_tokens=1500，与授权一致。

**结果：技术失败（退出码 1）。完整审计见 `live-results.json`：**

| 项 | 实际值 |
|---|---|
| Q1（可回答题） | `technical_failure`：“生成服务连接失败”（网络层失败，请求未到达 DeepSeek；本地 /ask 记 502 为本地口径）；generation_meta=null（无响应、不伪造 usage/request_id） |
| Q2（材料不足题） | `not_attempted`（首次技术失败立即停止策略）；本地检索 `no_hits`、0 证据已如实记录 |
| ask_requests / external_http_attempts | 1 / 1（≤2 上限；无重试） |
| 证据 | Q1 E1—E3 共 214 字符（≤6000）；Q2 0 字符 |
| 退出码 | 1（失败非零，符合修正后的语义） |

按约定**未自行重试、未修复后重跑、未追加诊断请求**。已知环境事实（非本次诊断结论）：本机系统代理曾拦截 httpx(trust_env=True) 连接（T013 实测），连接失败确切原因未诊断。

## C 阶段核对

见 `live-review-notes.md`。要点：无生成回答 → 答案表述/引用支撑/编造类核对项均不适用（也**无任何编造产物**）；Q2 无门禁时间编造；接口链路成功、生成失败、答案核对不适用。**不能宣称真实问答验收通过。**

## 交付文件

- 新增：`live-results.json`（完整审计）、`live-answers-full.json`（空集标记，本次无生成回答）、`live-review-notes.md`（逐条核对记录）
- 更新：`report.md`、`verification.md`、`submission.json`、`changed-files.json`（本修订未改任何代码文件，清单与 revision 2 相同）
- 历史副本：revision 1（`*.rev1.*`）与 revision 2（`*.rev2.*`）均保留

## 剩余条件与建议

B 阶段未完成（失败如实记录，不美化）。后续重试属新一次外部调用，需用户另行授权；建议先排查执行环境对 api.deepseek.com 的可达性（含系统代理）。C 阶段答案核对待一次成功生成后补做。

完成后停止，等待 Astra 验收。T015 未发布。
