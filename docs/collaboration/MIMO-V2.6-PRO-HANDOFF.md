# MiMo v2.6 Pro 新对话交接

交接日期：2026-09-22。仓库：`F:\Collage Paper`。不依赖旧聊天记录；未来如与 STATUS.md 冲突，以更新后的 STATUS.md 和最新任务/验收为准。

## 2026-09-22 后续更新

T011 revision 2 已通过，见 reviews/T011-R2.md。当前唯一任务为 tasks/T012-引用式问答接口与证据整理.md；下文 T011 初始交接与提示词保留为历史，不再执行。启动新对话时先读取 STATUS.md 和 T012，直接执行 T012 v1，提交 revision 1 后停止。模型 API/预算未确认，不调用外部生成模型，不把离线证据摘录或 fake 测试当成真实自动问答。

## 初始交接：角色与当时工作

用户在 VS Code / Claude Code 中使用 MiMo v2.6 Pro 编码；Astra 在另一对话中安排任务、独立验收、发布下一单。换模型不意味着重做项目、重写技术路线或自动推进所有阶段。

T001—T010 已验收；最新结论见 [T010-R1](./reviews/T010-R1.md)。**当前唯一授权：执行 [T011 适用条件筛选与检索收尾](./tasks/T011-适用条件筛选与检索收尾.md)，交付后停止。** 旧的 T008/T009 返工记录均为历史，不能根据它们再次启动返工。

首次按顺序读：根目录 CLAUDE.md → STATUS.md → PROTOCOL.md → PROJECT_CONTEXT.md → 本交接 → T010-R1 → T011。系统方案 docs/01、02、04 只按当前任务需要查阅；无需逐字重读所有历史提交。

## 用户条件与执行偏好

- 四川农业大学；语料为教务网及学校公开文档，由用户之后提供；导师不限定技术方法。
- 纯 Windows。采用统一 Python/FastAPI，RAGFlow 仅参考，TinyAgent 未集成且未最终选仓库。不安装 WSL/Docker，不切换双后端。
- 用户明确要求加速：合并业务闭环，不堆冗余安全/边界测试。主路径、数据正确性、已复现问题与一次必要回归必须有真实证据。
- MiMo v2.6 Pro 是用户的开发工具模型，不是系统运行时问答模型。问答 API 供应商/预算未定；不能复用 Claude Code 的凭据为产品发请求。
- 真实学校政策、真实问题集、语音、办事清单、待办、正式双端仍待后续任务。不要将方案中的功能当成已经实现。

## 已有代码与关键约定

后端根目录：`step2_code/backend`。Python：`.venv/Scripts/python.exe`。源码：`src/campus_assistant`。测试：`tests`。当前本地权重目录：`models/bge-small-zh-v1.5`。模型已存在，先检查，不重新下载。

| 位置 | 已有功能 / 必须保留的约定 |
|---|---|
| corpus/models.py、validate.py、parse.py | 清单校验、TXT/DOCX 解析；来源哈希、block 定位；坏文档隔离 |
| corpus/chunk.py | 500 字符块内切分，表格行保留；来源区间为半开区间 |
| retrieval/bm25.py、tokenize.py | 中文 bigram / ASCII 分词，稳定排序、正分候选 |
| retrieval/embedding.py、dense.py、hybrid.py | 本地 BGE CPU、归一化点积、RRF k=60；需要 T011 补齐运行信息 |
| main.py、api/search.py | create_app 可选 manifest/corpus/model；默认 BM25；未配置 dense 时明确 503 |
| static/search.html、preview.html | 三模式证据搜索、原文定位；不是真正的自动问答 |
| evaluation/models.py、run.py、metrics.py | gold 全部来源验证后才检索；不可回答题不纳入可回答题宏平均 |
| examples/parse-corpus、evaluation | 2 份合成文件、17 块，8 题，dataset_version=1.2；禁止为提高分数改 gold |

API：GET /api/v1/search/status，POST /api/v1/search；UI：/search、/preview。health/ready 的问答就绪语义仍未实现，不能因为搜索可用就擅自改成全系统 ready。

Scope 空数组是“未知”，不是适用全体；引用依靠 document_id/block_id/字符区间与文件哈希，不能仅依靠 chunk_id。三模式 score 性质不同，不能相加或称置信度；检索命中不证明足够作答。

## 验收基线与已知事项

T010 Astra 独立实测 374 passed、1 skipped；pip check 与页面语法通过。真实模型三模式 Recall@5=1、Hit@5=1、MRR@5=0.9166666666666666，仅为小型合成集；无答案题 empty_result_rate=0，尚无可靠拒答。

浏览器已验证语义和混合检索与原文跳转。`scripts/check-search-behavior.cjs` 的 stub 没适配 mode-selector，当前会报 addEventListener 错误；它没有通过，不要复制“全部检查通过”。修复及模型本地加载、状态原因、revision/截断统计、完整 CLI 记录已合并进 T011，详见任务。

不要覆盖旧 submissions/T010 来美化记录。Astra 的复现脚本与结果在 reviews/T010-R1-*；计时包含初始化与缓存，不能直接作查询性能比较。没有必要重新运行整个 T001—T010 审计。

## 可用命令

以下在 backend 工作目录运行；node 可用 `D:\nodejs\node.exe`（先确认本机路径）。Windows 临时目录权限可能受限，pytest 使用项目内全新 basetemp：

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
$testTemp = Join-Path (Get-Location) ('.cache/t011-' + [guid]::NewGuid().ToString('N'))
& .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp $testTemp --tb=short -rs
& .\.venv\Scripts\python.exe -m pip check
& 'D:\nodejs\node.exe' scripts/check-js-syntax.cjs
& 'D:\nodejs\node.exe' scripts/check-search-behavior.cjs
```

```powershell
$env:CAMPUS_EMBEDDING_MODEL_DIR = (Resolve-Path models/bge-small-zh-v1.5).Path
& .\.venv\Scripts\python.exe -m uvicorn campus_assistant.demo:app --host 127.0.0.1 --port 8001
```

只停止自己启动的进程，不终止用户其他服务。不开公网。首次检查 Git 状态；若并非 Git 仓库，如实记录并继续，不初始化或重置。保留用户现有修改。不打印 .env、密钥或全量环境变量，不读取开发工具凭据。

## 新对话启动提示词

```text
你是本项目的执行开发者 MiMo v2.6 Pro，Astra 负责安排和验收。工作目录 F:\Collage Paper。

先读取 CLAUDE.md，以及 docs/collaboration/ 下 STATUS.md、PROTOCOL.md、PROJECT_CONTEXT.md、MIMO-V2.6-PRO-HANDOFF.md，再读 reviews/T010-R1.md 和 tasks/T011-适用条件筛选与检索收尾.md。

T001—T010 已通过，不重新盘点或重做。现在直接执行 T011 v1：交付校区/学生类型/入学年份/日期筛选的三模式检索与页面闭环，同时完成任务内列出的 T010 收尾。先简短复述范围和计划，然后实施，不停留在方案，也不要反复请求已授权范围的确认。

遵守任务限定路径；保留现有修改。复用项目 .venv 和本地 BGE，不调用付费模型、不取用 Claude Code 凭据、不安装全局工具。不要擅自改架构、扩展成全系统重构或推进 T012。

按用户加速要求，只验证关键业务路径、数据正确性、已复现问题和一次必要回归。真实运行命令并记录退出码；失败与未验证项如实写出，不能用省略号或旧结果冒充本轮证据。合成资料不代表学校政策。

完成后在 docs/collaboration/submissions/T011/ 提交任务要求的报告、验证记录、submission.json、changed-files.json 和原始结果；身份 submission_revision=1、status=ready_for_review（未完成则如实 partial/blocked）。最后报告改动、验证、已知限制并停止，等待 Astra 验收。不要修改 Astra 的状态或写 accepted。
```
