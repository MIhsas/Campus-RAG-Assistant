# T014 验证记录（A 阶段本地准备）

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。按任务只做相关本地验证；未重复 441 项全量、JS、依赖或 embedding 评测。所有命令本轮真实运行；未运行项明确标注。

## 1. 工作区状态

```bash
cd "F:\Collage Paper" && git status
# fatal: not a git repository (or any of the parent directories): .git
```

退出码：128（git 本身）。非 Git 仓库，如实记录后继续。

## 2. 冒烟脚本与适配器相关测试（15 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_live_smoke_script.py tests/test_deepseek_provider.py -q -p no:cacheprovider --basetemp .cache/t014-iter3 --tb=short -rs
# 15 passed, 2 warnings in 8.39s
# 退出码：0
```

- `test_live_smoke_script.py`（3 项，loopback mock）：
  - 成功记录/退出 0：outcome=generated、`generation_meta` 完整（model/request_id/usage/finish_reason 未截断）、`answer_preview` 按 10 字符截短带 truncated 标志、完整回答经 `--full-answers-out` 另存且注明“不代表模型截断”、`live_verified` 恒为 false（脚本不自我认证）。
  - HTTP 500 失败：`exit_ok=false`（进程将退出非零）、outcome=technical_failure（http_success=false）+ 第二题 not_attempted（首次技术失败立即停止）、`ask_requests=1`、`external_http_attempts=1`。
  - dry-run：mode=dry-run、零 ask/零外部尝试、目标地址与 model 审查字段存在、每题 `within_char_budget=true`。
- `test_deepseek_provider.py`（12 项）：适配器契约回归全过（CountingProvider 透传 provider_id/generate 不影响既有契约）。

首轮（.cache/t014-iter1）曾 1 failed：断言 `external_http_attempts==2` 与实测 1 不符——第二题（宿舍门禁）本地检索 **no_hits**、短路未调用生成器。这正是 T013-R1 第 3/4 项要求如实记录的行为；修正测试断言为真实行为（generated + short_circuit_no_evidence、尝试 1 次），非产品缺陷。

## 3. dry-run 实跑（本地检索 + 审查摘要，无网络）

```bash
./.venv\Scripts\python.exe scripts\live-smoke-deepseek.py > .cache/t014-dryrun.json
# 退出码：0（stderr：dry-run 完成：仅本地检索与审查摘要，未发送任何请求。）
```

摘要（完整输出在命令结果中，密钥未打印）：

| 项 | 值 |
|---|---|
| target / model / max_tokens | https://api.deepseek.com/chat/completions / deepseek-flash / 1500 |
| counters | local_retrieval_calls=2、ask_requests=0、external_http_attempts=0 |
| external_model_calls / live_verified | 0 / false |
| smoke-01-answerable（年级 2023） | state=ok；E1(63)+E2(63)+E3(88)=214 字符，≤6000 |
| smoke-02-insufficient（不限） | state=no_hits；0 条证据（live 时将本地短路，HTTP 记 0，不谎称验证模型拒答） |
| max_external_http_attempts / retries | 2 / 0（首次技术失败立即停止） |

## 4. 参数硬限（1—2000）

```bash
./.venv\Scripts\python.exe scripts\live-smoke-deepseek.py --answer-preview-chars 2001
# error: --answer-preview-chars 必须在 1—2000 之间（仅限制答案预览长度，不是 token/费用限制）
# 退出码：2
./.venv\Scripts\python.exe scripts\live-smoke-deepseek.py --answer-preview-chars 0
# 同上
# 退出码：2
```

## 5. 未验证项（如实标注）

1. **真实官方调用：未执行**（live_verified=false、external_model_calls=0）。唯一剩余条件：用户明确提供调用授权 + 本地密钥配置（见 report.md“剩余授权条件”）。B（--live）与 C（逐条人工核对、live-results.json、人工核对记录）均待授权后进行。
2. 模型对“材料不足”的真实行为：第二题当前 no_hits 本地短路，未观察到生成器对无关候选的拒答行为；C 阶段如实记录。
3. 按任务未跑：全量 pytest、JS 检查、pip check、embedding 评测（无相关变更）。
