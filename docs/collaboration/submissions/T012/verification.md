# T012 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`（另有注明者除外）。执行工具为 Git Bash；PowerShell 等价命令见 backend/README.md。所有命令本轮真实运行。

## 1. 工作区状态

```bash
cd "F:\Collage Paper" && git status
# fatal: not a git repository (or any of the parent directories): .git
```

退出码：128（git 本身）。非 Git 仓库，如实记录后继续；未初始化、未重置。

## 2. 新增聚焦测试（25 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_qa_evidence.py tests/test_ask_api.py -q -p no:cacheprovider --basetemp .cache/t012-iter1 --tb=short -rs
# 25 passed, 2 warnings in 2.05s
```

退出码：0。覆盖任务列出的各项：引用与原文跨度一致（对 parse 原块切片逐段核对）、筛选传递、上下文实际输入与引用集合一致（RecordingProvider 记录输入）、生成器未配置 503、一个有效 fake 输出、非法引用/空输出/无引用/未知类型失败（502 且无部分坏答案泄漏）、生成器 insufficient_evidence 独立状态、生成器异常隔离且搜索不受影响、检索失败（未配置语料）返回 503 而非无答案。fake 仅证明协议，不是模型效果。

## 3. 一次全量回归（共享检索代码被抽取）

```bash
testTemp=".cache/t012-full-<timestamp>"
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp "$testTemp" --tb=short -rs
# 429 passed, 1 skipped, 2 warnings in 64.63s
# SKIPPED [1] tests\test_corpus_validate.py:551（Windows 链接权限 OSError winerror=1314，既有跳过）
```

退出码：0。429 = T011 基线 404 + 本单 25；原搜索/筛选/评测测试全部通过（响应与排名未变）。无依赖修改，按任务未重复 pip check。

## 4. 变更页面语法与行为检查（一次）

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# ask.html: syntax OK
# preview.html: syntax OK
# search.html: syntax OK
# All 3 HTML files passed syntax check.
# 退出码：0

"D:/nodejs/node.exe" scripts/check-search-behavior.cjs
# check-search-behavior: 14 scenarios passed
# 退出码：0（search 页仅加导航链接，既有回归保持通过）

"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 9 scenarios passed
# 退出码：0
```

ask 行为 9 场景：提交快照+E-证据卡+标签、状态刷新不清筛选且再次请求保留条件、失败重试沿用 mode/query/filters、复制纯文本（含来源）与复制失败提示、三种空态（无符合资料/无命中/预算装不下）、生成器未配置禁用生成、受控 generated 响应的段落+引用渲染（协议演示，非真实 LLM）。

## 5. 真实 extractive API 演示

```bash
./.venv/Scripts/python.exe scripts/demo-ask.py --corpus examples/parse-corpus > "F:/Collage Paper/docs/collaboration/submissions/T012/ask-demo.json"
# 退出码：0（未配置生成器，未调用任何外部/付费模型）
```

结果（完整见 ask-demo.json 与 demo-notes.md）：

- ask/status：extractive 默认、generator_configured=false。
- extractive 无筛选：evidence_only、answer=null、E1—E5。
- extractive（成都校区/2023/2026-09-22）：3 条证据均来自 TXT 文档，allowed_count=1；预算 3 条 214 字符、0 略过。
- extractive（年级 1900）：evidence_state=no_admissible_docs + 明确空态消息，answer=null。
- generated：503 GENERATOR_NOT_CONFIGURED。

## 6. 未验证项（如实标注）

1. **真实浏览器页面闭环“提问→摘录→出处→复制”**：本轮无浏览器能力，未执行。步骤见 demo-notes.md，交 Astra 补验。页面逻辑证据为 DOM/fetch/clipboard stub（check-ask-behavior.cjs）。
2. 真实生成模型联调与答案质量人工评价：本任务范围外（模型 API/预算未确认），未执行、不宣称。
3. 未重复三模式模型评测、模型下载、依赖安装、pip check、安全/极端输入矩阵（按任务聚焦要求省略；无依赖变更）。
