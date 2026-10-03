# T011 验证记录

执行环境：Windows 11，工作目录 `F:\Collage Paper\step2_code\backend`（另有注明者除外）。执行工具为 Git Bash；PowerShell 等价启动/演示命令见 backend/README.md。所有命令本轮真实运行，退出码如实记录。

## 1. 工作区状态

```bash
cd "F:\Collage Paper" && git status
# fatal: not a git repository (or any of the parent directories): .git
```

退出码：128（git 本身）。非 Git 仓库，如实记录后继续；未初始化、未重置、未覆盖用户修改。

## 2. 新增筛选测试（30 项）

```bash
cd "F:\Collage Paper\step2_code\backend"
./.venv/Scripts/python.exe -m pytest tests/test_search_filters.py -q -p no:cacheprovider --basetemp .cache/t011-iter2 --tb=short -rs
# 30 passed, 2 warnings in 0.93s
```

退出码：0。覆盖：筛选语义（空 scope=未知、AND、日期两端包含、五类排除原因互斥计数、未标注截止注记、筛选选项提取）、三模式准入在截断前（全库第 6 名合法候选不漏、被排除资料不返回、None/空集区分）、API 回显/计数口径/无匹配不取消条件/status 选项/6 组 422。

## 3. 一次全量回归

```bash
cd "F:\Collage Paper\step2_code\backend"
testTemp=".cache/t011-full-<timestamp>"
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp "$testTemp" --tb=short -rs
# 404 passed, 1 skipped, 2 warnings in 26.25s
# SKIPPED [1] tests\test_corpus_validate.py:551 （Windows 链接权限 OSError winerror=1314，既有跳过）
```

退出码：0。较 T010 基线（374 passed、1 skipped）净增 30 项即本单新增测试，无失败。

```bash
./.venv/Scripts/python.exe -m pip check
# No broken requirements found.
```

退出码：0。

## 4. JS 语法与行为脚本

```bash
node scripts/check-js-syntax.cjs
# preview.html: syntax OK
# search.html: syntax OK
# All 2 HTML files passed syntax check.
```

退出码：0。

```bash
node scripts/check-search-behavior.cjs
# check-search-behavior: 12 scenarios passed
```

退出码：0。（T010-R1 记录的 addEventListener 失败已修复。）12 个场景=旧 2×2+3 重试场景保留 + 新增：mode/query/filters 重试快照、条件快照不被控件改写、清除条件、两种筛选空态+无筛选空态、语义按实际 hits 展示。

## 5. 三模式评测 CLI（完整命令 + 原始输出）

```bash
cd "F:\Collage Paper\step2_code\backend"
./.venv/Scripts/python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --mode bm25 --top-k 5 > "F:/Collage Paper/docs/collaboration/submissions/T011/eval-bm25.json"
# 退出码：0

./.venv/Scripts/python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --mode dense --model-path models/bge-small-zh-v1.5 --top-k 5 > "F:/Collage Paper/docs/collaboration/submissions/T011/eval-dense.json"
# 退出码：0

./.venv/Scripts/python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --mode hybrid --model-path models/bge-small-zh-v1.5 --top-k 5 > "F:/Collage Paper/docs/collaboration/submissions/T011/eval-hybrid.json"
# 退出码：0
```

无省略号，输出即存档原始 JSON（8 题 gold 未改，dataset_version=1.2）。三模式 summary 一致：

| 模式 | evidence_recall | hit | mrr | empty_result_rate | embedding_model_id | revision | truncated |
|---|---|---|---|---|---|---|---|
| bm25 | 1.0 | 1.0 | 0.9166666666666666 | 0.0 | null | null | null |
| dense | 1.0 | 1.0 | 0.9166666666666666 | 0.0 | bge-small-zh-v1.5 | 7999e1d3359715c523056ef9478215996d62a620 | 0 |
| hybrid | 1.0 | 1.0 | 0.9166666666666666 | 0.0 | bge-small-zh-v1.5 | 7999e1d3359715c523056ef9478215996d62a620 | 0 |

dense/hybrid 输出另含 `truncation_note`（长块可能仅部分参与向量计算，原文与 chunk 不被截短）。与 T010-R1 独立实测同指标，无筛选默认路径可比。

## 6. 筛选演示夹具与真实模型 API 演示

```bash
./.venv/Scripts/python.exe -m campus_assistant.corpus.validate --manifest examples/filter-demo/manifest.json --corpus-root examples/filter-demo
# {"valid": true, "document_count": 5, "errors": []}
# 退出码：0

./.venv/Scripts/python.exe scripts/demo-filter-search.py --model-path models/bge-small-zh-v1.5 --corpus examples/filter-demo > "F:/Collage Paper/docs/collaboration/submissions/T011/filter-demo.json"
# 退出码：0（stderr 有既有 fastapi testclient 弃用警告与权重加载进度条，不影响输出）
```

关键结果（完整 JSON 见 `filter-demo.json`，解读见 `filter-demo-notes.md`）：

- `encode_documents_calls=1`，重复查询后仍为 1：正文不重编码。
- status：available_modes 三模式；embedding_model=`bge-small-zh-v1.5`（无路径）；revision=`7999e1d3359715c523056ef9478215996d62a620`；max_seq_length=512；truncated_chunk_count=0；embedding_error=null。
- 同题“缓考申请”：无筛选命中 5 文档；year=2024 → fd-2024+fd-yjy；year=2025 → fd-2025+fd-yjy；as_of=2024-10-01 → fd-2024+fd-yjy（注 1 份未标注截止）；as_of=2025-09-10 → fd-2025+fd-yjy（注 2 份未标注截止，fd-2024 已失效被排除）。
- campus=成都校区+year=2024+as_of=2025-09-10 → hits 空、allowed_count=0，filters 原样回显，不取消条件。

## 7. 加载失败与身份核对（内联脚本，create_app+TestClient + EmbeddingService）

```bash
./.venv/Scripts/python.exe -c "<见下方要点，完整脚本为一次性内联>"
```

退出码：0。结果：

- 不存在模型目录：available_modes=['bm25']，embedding_error=`模型目录不存在：not-a-model-dir`（仅目录名，无本机路径），bm25 搜索 200 且有命中。
- Hub ID `BAAI/bge-small-zh-v1.5`（非本地目录）被拒绝，ValueError 同上形式。
- 真实模型身份：model_name=`bge-small-zh-v1.5`，revision=`7999e1d3…`（与下载元数据一致），max_seq_length=512。
- `count_truncated([短文本, 400×“缓考申请”, 短文本])=1`；encode 仍成功（dim=512）；输入文本长度 2000 字符原样保留，未截短。

## 8. 未验证项

1. **真实浏览器闭环（页面筛选→搜索→查看原文→清除条件，及一次错误重试）**：本轮无浏览器能力，未执行、不写成通过。请 Astra 补验。建议步骤：启动 `uvicorn campus_assistant.demo:app --port 8001`（设 `CAMPUS_EMBEDDING_MODEL_DIR=models\bge-small-zh-v1.5`）→ http://127.0.0.1:8001/search → 选校区/年级+日期搜索 → 核对条件行与结果数 → 点“查看原文”核对定位 → 编辑控件核对条件行不变 → “清除条件”核对控件复位 → 断网或停服务后点重试核对沿用上次 mode/query/filters。stub 级行为（check-search-behavior.cjs 12 场景）已覆盖上述逻辑。
2. 模型加载中断/损坏等罕见故障形态未逐一模拟（已覆盖“目录不存在”“非本地目录”）。
3. 未做性能计时、未做安全/极端输入矩阵（按加速要求省略）。
