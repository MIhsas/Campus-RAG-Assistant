# T013 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`（另有注明者除外）。执行工具为 Git Bash。所有命令本轮真实运行；未运行项明确标注。

## 1. 工作区状态

```bash
cd "F:\Collage Paper" && git status
# fatal: not a git repository (or any of the parent directories): .git
```

退出码：128（git 本身）。非 Git 仓库，如实记录后继续。

## 2. 官方参数核对（curl，只读公开文档）

```bash
curl -sS -m 15 -L "https://api-docs.deepseek.com/guides/json_mode/" -o .cache/ds-json.html      # 退出码 0
curl -sS -m 15 -L "https://api-docs.deepseek.com/zh-cn/news/news260910/" -o .cache/ds-news.html  # 退出码 0
curl -sS -m 15 -L "https://api-docs.deepseek.com/api/create-chat-completion/" -o .cache/ds-api.html   # 退出码 0
curl -sS -m 15 -L "https://api-docs.deepseek.com/guides/thinking_mode/" -o .cache/ds-thinking.html    # 退出码 0
```

要点（已写入报告）：`deepseek-flash`；`response_format={"type":"json_object"}` + 提示词含 "json" 与结构示例；`finish_reason=length` 为截断；`POST /chat/completions`；`thinking={"type":"disabled"}` 非思考。未做额外模型选型。

## 3. loopback 环境对照实验（trust_env 发现）

```bash
./.venv/Scripts/python.exe -c "<loopback mock + httpx 对照>"
# trust_env default -> 502
# trust_env False   -> 200
# proxy-ish env keys present: []
# 退出码：0
```

结论：本机系统代理（注册表，httpx trust_env 经 urllib.getproxies 读取）拦截 loopback。mock 联调需 `trust_env=False`（已内置到测试与演示脚本）；真实调用默认保留代理支持。

## 4. 新增测试（12 项）与既有回归

```bash
./.venv/Scripts/python.exe -m pytest tests/test_deepseek_provider.py tests/test_ask_api.py -q -p no:cacheprovider --basetemp .cache/t013-iter7 --tb=short -rs
# 30 passed, 2 warnings in 7.45s（12 项 DeepSeek + 既有 ask 契约回归 18 项）
# 退出码：0
```

12 项覆盖：有效答案全链路（请求 model=deepseek-flash、stream=false、response_format=json_object、thinking=disabled、max_tokens=1500、system 含 json 结构示例、user 只含实发证据；响应引用⊆实发证据、服务端解析、generation_meta 审计字段）、材料不足独立状态、坏 JSON、非法引用 E99、截断（finish_reason=length）、空内容、HTTP 500 映射且仅 1 次请求（无重试）、超时映射、配置默认关闭时摘录可用 + generated 503、显式启用+完整配置注入（alias 深析）、URL 拼接规则。

首轮迭代中 mock 测试曾失败 8 项，根因为测试 mock 漏赋 `self.respond` 与系统代理劫持 loopback（详见第 3 节），修复后全过；非产品缺陷。

## 5. 一次全量回归

```bash
testTemp=".cache/t013-full-<timestamp>"
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp "$testTemp" --tb=short -rs
# 441 passed, 1 skipped, 2 warnings in 37.96s
# SKIPPED [1] tests\test_corpus_validate.py:551（Windows 链接权限 OSError winerror=1314，既有跳过）
# 退出码：0
```

441 = T012 基线 429 + 本单 12。无依赖变化，按任务未重复 pip check / 安装 / embedding 评测。本轮未变更页面文件，按任务未跑 JS 检查。

## 6. loopback mock 全链路集成演示

```bash
./.venv/Scripts/python.exe scripts/demo-deepseek-mock.py --corpus examples/parse-corpus > "F:/Collage Paper/docs/collaboration/submissions/T013/mock-integration.json"
# 退出码：0
```

`mock-integration.json` 内 7 项检查全过：http_status_200、status_generated、citation_within_sent_evidence、citation_resolved_by_service、audit_metadata_present、request_model_json_mode、single_http_call。请求摘要：path=/chat/completions、model=deepseek-flash、stream=false、response_format=json_object、thinking=disabled、max_tokens=1500、Bearer 头存在（密钥为占位值 `sk-test-placeholder`，未输出）。模拟回答带“【模拟输出，非真实 DeepSeek 回答】”标记；`external_model_calls=0`。

## 7. live smoke dry-run（无网络）

```bash
./.venv/Scripts/python.exe scripts/live-smoke-deepseek.py
# 打印无密钥配置摘要（api_key: "(redacted)"、planned_requests: 0、key_configured: false）
# dry-run 完成：未发送任何请求。
# 退出码：0
```

## 8. 未验证项（如实标注）

1. **DeepSeek 官方服务真实调用：未执行**（live_verified=false、external_model_calls=0）。按 live-smoke-plan.md 待用户确认密钥配置方式、费用上限与少量调用授权后执行。
2. 真实回答质量/拒答可靠性/校园准确率：未评价，不宣称。
3. 未枚举全部 HTTP 状态码与极端输入矩阵（按任务聚焦要求）；401/429 映射走同一错误通道（测试以 500/超时覆盖）。
4. 未跑 JS 检查：本轮无页面变更（任务“变更页面才做相关 JS 检查”）。
