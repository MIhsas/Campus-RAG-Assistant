# T014 真实问答冒烟准备与验收 — 实施报告（A 阶段）

身份：task_id=T014、task_revision=v1、submission_revision=1、**status=partial**（A 阶段本地准备已完成；B—C 等待授权）。
**live_verified=false、external_model_calls=0。本任务发布时真实请求未授权，本轮未执行 --live、未发送任何外部请求。**

## 概述

修正 T013-R1 指出的冒烟脚本四个记录问题，并准备两道有明确目的的合成问题（可回答 / 材料不足）。本地准备（含 dry-run 审查摘要与 loopback 记录/退出码验证）已完成；真实官方调用的**唯一剩余条件**见下文“剩余授权条件”。

## T013-R1 四项修正（`scripts/live-smoke-deepseek.py` 重写）

1. **失败非零退出**：technical_failure → `exit_ok=false` → 进程退出码 1；每条记录单独标明 `http_success` / `generation_success` / outcome_kind（generated | insufficient_evidence | short_circuit_no_evidence | technical_failure | not_attempted）。
2. **审计完整保留，仅预览截短**：结构化记录完整保存 status、generation_meta（model、request_id、usage、finish_reason、latency_ms、max_tokens）与实际调用记录；只有 `answer_preview.text` 按上限截短并带 `truncated` 标志；`--full-answers-out` 可将完整回答另存独立本地 JSON（注明“预览截断≠模型截断”）。`--answer-preview-chars` 硬限 1—2000（越界 exit 2），并明确它只是预览限制、**不是 token/费用限制**。
3. **双计数**：`ask_requests`（generated /ask 次数）与 `external_http_attempts`（经 CountingProvider 在 provider.generate 实际发生时计数）分开记录，不通过 /ask 条数推断；无证据短路不调用生成器、不计模型调用。无重试，外部尝试最多 2 次，**首次技术失败立即停止**（后续问题记录为 not_attempted）。
4. **两道合成问题**（mode=bm25、max_tokens=1500、证据字符 ≤6000；原 gold 未动）：
   - 可回答：“缓考申请须由谁批准，之后还需要向哪个部门备案？”（年级 2023）——预期核对 TXT 第二条“所在学院批准、教务处备案”。
   - 材料不足：“宿舍门禁时间是几点？”（不限）——语料无此事实。dry-run 实测该题 **no_hits**：live 时将本地短路、真实 HTTP 次数记 0，**不谎称验证了模型拒答**（任务预设分支）。

dry-run 先做本地检索并输出审查摘要：官方目的地址 `https://api.deepseek.com/chat/completions`、model=deepseek-flash、两题的条件与实际证据 ID/字符数（214 / 0）、预计最多调用数 2、max_tokens=1500。无密钥可准备，密钥不打印，dry-run 不联网。结构化结果与答案预览分离；报告不预填成功或模拟 usage。

## 验证摘要（仅相关本地验证，未重复全量/JS/依赖/embedding 评测）

- `tests/test_live_smoke_script.py` 3 项 + `tests/test_deepseek_provider.py` 12 项回归：**15 passed**（loopback：一个成功记录/退出 0、一个 HTTP 500 失败记录/退出非零并停止、dry-run 纯本地）。
- dry-run 实跑退出 0；`--answer-preview-chars 0/2001` 均 exit 2（硬限生效）。
- 首轮测试曾断言外部尝试=2 失败——实测第二题 no_hits 短路仅 1 次，这正是第 3/4 项要如实记录的行为；修正测试断言与真实行为一致（非产品缺陷）。

## 修改与新增文件

- 修改：`scripts/live-smoke-deepseek.py`（重写）、`README.md`（冒烟说明与授权注记）
- 新增：`tests/test_live_smoke_script.py`
- 完整清单见 `changed-files.json`

未修改：检索、模型适配器、页面、gold、Astra 文件。

## 剩余授权条件（B 阶段，缺一不可）

由用户明确提供后方可执行 `scripts/live-smoke-deepseek.py --live`：

1. **调用授权**：批准向 DeepSeek 官方 `https://api.deepseek.com`（model=deepseek-flash）以上述两道合成问题发送**最多两次 HTTP 尝试**（每次 max_tokens=1500、无重试、首次技术失败即停）。
2. **本地密钥配置**：`CAMPUS_GENERATOR=deepseek` + `DEEPSEEK_API_KEY`（本地环境变量；不贴聊天/报告）。用户可另设费用上限，实际执行不得超出最新授权。

授权后的 C 阶段：逐段人工核对（数字/部门/条件是否与原文一致、引用是否支持主张、材料不足有无编造），新增 `live-results.json` 与人工核对记录；不合格如实报告。两次冒烟仅证明链路与个别行为，不是校园准确率或可靠拒答指标。

## 已知限制

- 真实官方调用未执行、未验证（live_verified=false、external_model_calls=0）。
- 第二题当前 no_hits 短路：模型对“材料不足”的真实行为将在有无关候选时才可观察（C 阶段如实记录）。
- HTTP 30 秒 timeout 为 httpx 操作超时配置（T013-R1 注记），非严格墙钟上限。

完成后停止，等待 Astra 验收。T015 未发布。
