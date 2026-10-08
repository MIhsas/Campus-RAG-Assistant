# campus-assistant-backend

四川农业大学校园教务智能问答系统 — 后端服务。当前版本 0.1.0。

## 当前范围

- **健康检查**：`/api/v1/health/live`（200）、`/api/v1/health/ready`（503，知识库尚未配置）。
- **语料登记校验**：离线命令验证 manifest.json 与文件完整性（不解析正文、不联网）。
- **文档正文解析**：将已校验的 TXT/DOCX 转为有来源定位的正文块。不提供 RAG 问答、向量检索或模型调用。
- **语料预览**：`/preview` 页面浏览文档、核对来源、回查正文位置。合成测试资料不代表学校政策。
- **正文分块**：将解析正文块转为检索候选单元。段落按固定字符窗口滑动切分，表格行整行保留。纯离线，不调用模型。
- **BM25 离线检索**：对分块结果建立关键词排序，查询返回匹配证据及原文定位。CJK 二元组 + ASCII 小写分词基线，不调用模型。
- **向量检索**：基于 BAAI/bge-small-zh-v1.5 的本地 CPU 向量检索。仅加载本地模型目录（`local_files_only=True`），归一化嵌入 + 点积排序，查询加检索前缀。
- **混合检索（RRF）**：BM25 和向量各取前 20 候选，按 Reciprocal Rank Fusion 融合排序。
- **适用条件筛选**：搜索可选校区/学生类型/入学年份/查询日期条件，先文档准入后取 Top-K，回显规范化条件与排除原因计数。
- **三模式搜索页**：`/search` 支持关键词/语义/混合模式切换与四项筛选、“清除条件”，显示所用条件与结果数量。
- **证据整理（/ask）**：围绕问题整理原文证据（E1、E2…编号摘录 + 原文跳转），POST `/api/v1/ask` 默认 `answer_mode=extractive` 只返回原文摘录（`status=evidence_only`、`answer=null`）。可注入 AnswerProvider 契约已定义；未配置时 generated 返回 503/GENERATOR_NOT_CONFIGURED。
- **DeepSeek 生成适配（T013）**：`DeepSeekAnswerProvider` 对接 Chat Completions（model=deepseek-flash，JSON 输出模式、非思考、非流式）。已用本地 loopback mock 完成 HTTP 全链路联调；真实服务冒烟脚本已备（`scripts/live-smoke-deepseek.py`，默认 dry-run），**尚未对官方服务发送任何请求**。
- 所有 HTTP 响应包含 `X-Request-ID` 头（中间件统一生成，不信任客户端值）。
- OpenAPI 文档位于 `/docs`。

### 限制

- 无数据库、用户认证或 RAG 问答生成。
- **生成适配已就绪但未联调真实服务**：DeepSeek 适配器经本地 mock 验证（不是真实 DeepSeek 回答）；live_verified=false、external_model_calls=0。真实冒烟需用户确认密钥配置方式、费用上限与少量调用授权后执行 `scripts/live-smoke-deepseek.py --live`。不宣称真实 RAG 作答、拒答可靠性或校园问答准确率。
- 无前端框架（Vue/React）。
- ready 端点 503 是本阶段预期契约，不是服务崩溃。
- 合成测试资料不能用于论文评测或真实校园问答。
- 适用条件筛选是证据检索的资料准入，不是学生资格判断或政策答案。
- 向量检索使用 CPU 推理，大规模语料需考虑 FAISS 替代。

## 环境要求

- Windows 11
- Python 3.12（已验证：D:\Anaconda\python.exe）

## 安装与运行

以下命令在 `step2_code/backend/` 目录内执行（PowerShell）。

### 1. 创建虚拟环境

```powershell
& D:\Anaconda\python.exe -m venv .venv
```

### 2. 安装锁定依赖

```powershell
& .\.venv\Scripts\python.exe -m pip install --cache-dir .cache/pip -r requirements.lock.txt
```

### 3. 安装本项目（可编辑模式，无构建隔离）

```powershell
& .\.venv\Scripts\python.exe -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
```

### 4. 下载嵌入模型（可选，用于向量/混合检索）

```powershell
& .\.venv\Scripts\python.exe scripts/download-embedding-model.py --output-dir models/bge-small-zh-v1.5
```

从 Hugging Face 官方仓库下载 BAAI/bge-small-zh-v1.5 到本地目录。只下载一种权重格式（safetensors，跳过 pytorch_model.bin）；本地已有权重不会被删除或重复下载。不下载则仅 BM25 模式可用。

### 5. 检查依赖一致性

```powershell
& .\.venv\Scripts\python.exe -m pip check
```

### 5. 运行测试

```powershell
& .\.venv\Scripts\python.exe -m pytest -q
```

### 6. 启动开发服务

```powershell
& .\.venv\Scripts\python.exe -m uvicorn campus_assistant.main:app --host 127.0.0.1 --port 8000
```

访问：
- http://127.0.0.1:8000/api/v1/health/live （200）
- http://127.0.0.1:8000/api/v1/health/ready （503）
- http://127.0.0.1:8000/docs （OpenAPI 文档）

### 7. 停止服务

Ctrl+C 或关闭终端窗口。

## 语料登记校验

### 运行示例校验

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.corpus.validate --manifest .\examples\synthetic-corpus\manifest.json --corpus-root .\examples\synthetic-corpus
```

成功输出（退出码 0）：
```json
{"valid": true, "document_count": 2, "errors": []}
```

失败输出（退出码 1）：`valid=false`，errors 数组列出每个问题的 code、document_id、field 和 message。

### Manifest 字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| schema_version | string | 固定 "1.0" |
| documents | array | 登记项列表，至少一项 |
| document_id | string | `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`，全清单唯一 |
| policy_group_id | string | 同上格式，同一政策不同版本可共用 |
| title | string | 去首尾空白后非空 |
| source_url | string | 绝对 http/https URL，有主机，无用户名/密码 |
| source_site | string | 非空来源网站名称 |
| local_path | string | 相对 corpus-root 的文件路径 |
| sha256 | string | 64 位十六进制，与文件内容匹配 |
| version_label | string | 人工填写的版本标签 |
| published_at | string/null | YYYY-MM-DD 或 null |
| effective_from | string/null | YYYY-MM-DD 或 null |
| effective_to | string/null | YYYY-MM-DD 或 null，不得早于 effective_from |
| scope | object | campus（字符串数组）、student_type（字符串数组）、admission_years（整数数组） |
| is_synthetic | bool | 严格布尔值，合成测试资料必须为 true |

**未知字段会被拒绝**，避免拼写错误被静默忽略。scope 空数组表示"尚未标注"，不等于"适用于所有人"。

### 错误码

| 错误码 | 含义 |
|---|---|
| MANIFEST_READ_ERROR | 文件读取失败 |
| MANIFEST_SCHEMA_ERROR | 结构或字段校验失败 |
| DUPLICATE_DOCUMENT_ID | document_id 重复 |
| UNSAFE_LOCAL_PATH | 路径不安全（绝对路径、路径穿越等） |
| FILE_NOT_FOUND | 文件不存在 |
| FILE_READ_ERROR | 文件读取失败 |
| HASH_MISMATCH | SHA-256 不匹配 |

### 用户后续提供文件时如何登记

1. 将文件放入 corpus 目录（如 `examples/synthetic-corpus/` 或专用数据目录）。
2. 计算 SHA-256：
   ```powershell
   # PowerShell
   Get-FileHash -Algorithm SHA256 .\your-file.txt
   ```
3. 在 manifest.json 的 documents 数组中添加新条目，填写所有必需字段。
4. 运行校验命令确认通过。

### 合成测试资料说明

`examples/synthetic-corpus/` 中的文件是合成测试数据，标注 `is_synthetic=true`、`source_site` 包含"合成测试"。**不能用于论文评测或真实校园问答。**

## 文档正文解析

### 运行解析

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.corpus.parse --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus
```

命令输出 UTF-8 JSON（可重定向保存）：

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.corpus.parse --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus > output.json
```

成功时 `valid=true`，documents 数组包含每个文档的 blocks。失败时 `valid=false`，errors 数组列出问题。

### Block 结构

每个 block 包含：

| 字段 | 说明 |
|---|---|
| block_id | 确定性 16 位十六进制 ID（基于 document_id、sha256、解析器版本和定位） |
| ordinal | 本批次内连续序号（从 1 开始，仅计非空块） |
| kind | `paragraph` 或 `table_row` |
| text | 正文文本（表格行以制表符分隔单元格） |
| locator | 定位信息（见下） |
| cells | 仅 table_row：单元格文本数组 |

### 定位回查原文

- **TXT**：`locator.type="lines"`，`line_start`/`line_end` 为原始 1-based 行号
- **DOCX 段落**：`locator.type="paragraph"`，`paragraph_index` 为文档 body 顶层段落序号（空段也占号）
- **DOCX 表格行**：`locator.type="table_row"`，`table_index`/`row_index` 各从 1 开始（空行仍占源行号）

### 格式边界

| 格式 | 支持 | 不支持 |
|---|---|---|
| TXT | UTF-8/UTF-8-BOM，空行分段 | 非 UTF-8 编码 |
| DOCX | 段落、普通表格（交错顺序保留） | 嵌套表格/合并单元格（warnings 提示） |
| — | — | PDF、扫描件、图片提取 |

### 失败与部分成功

- 单个文档解析失败不影响其他文档：`valid=false` 但已成功的文档仍输出
- 空文件 → `EMPTY_DOCUMENT`
- 损坏文档 → `DOCUMENT_PARSE_ERROR`
- 不支持格式 → `UNSUPPORTED_FORMAT`
- 哈希不符时不执行解析

### 注意

- 本模块不提供 RAG 问答、向量检索或 chunk 切分
- 合成示例 `examples/parse-corpus/` 不得用于论文评测

## 语料预览

### 启动示例预览服务

```powershell
& .\.venv\Scripts\python.exe -m uvicorn campus_assistant.demo:app --host 127.0.0.1 --port 8001
```

浏览器访问 http://127.0.0.1:8001/preview 查看合成示例。

### 启动带自定义语料的服务

```python
from campus_assistant.main import create_app
app = create_app(manifest_path=Path("path/to/manifest.json"), corpus_root=Path("path/to/corpus"))
```

```powershell
& .\.venv\Scripts\python.exe -m uvicorn campus_assistant.main:app --host 127.0.0.1 --port 8000
```

`manifest_path` 和 `corpus_root` 必须同时提供或同时省略。不提供时服务以"未配置"状态启动。

### API 端点

| 端点 | 说明 |
|---|---|
| GET /api/v1/corpus/status | 语料加载状态（始终 200） |
| GET /api/v1/corpus/documents | 文档列表（未配置 503） |
| GET /api/v1/corpus/documents/{id} | 文档详情（未配置 503，未知 ID 404） |
| GET /preview | 预览页面 |

### 状态说明

| 状态 | 含义 |
|---|---|
| unconfigured | 未提供 manifest/corpus-root |
| ready | 全部文档解析成功 |
| partial | 部分文档解析失败，成功文档仍可浏览 |
| failed | 无可展示的成功文档 |

### 限制

- 预览页不替代 Vue 管理端或微信小程序
- 通过重启加载新语料，本阶段不做热更新
- `/api/v1/health/ready` 继续返回知识问答未就绪 503
- 合成测试资料不代表学校政策

## 正文分块

### 运行分块

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.corpus.chunk --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus
```

可选参数 `--max-chars N`（默认 500，范围 1—10000）。

输出 UTF-8 JSON，可重定向保存：

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.corpus.chunk --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus > chunks.json
```

### 分块策略

| 块类型 | 策略 | 说明 |
|---|---|---|
| paragraph | 固定字符窗口滑动 | 从 start=0 开始，每段取 max_chars 字符，无重叠，不 trim |
| table_row | 整行一个 chunk | 保留 cells 和 text；超过 max_chars 不拆行，附 TABLE_ROW_EXCEEDS_MAX_CHARS 警告 |

- 字符窗口按 Python 字符串字符计数，不是 token 或字节
- 不跨文档、不跨原文块、不猜政策语义
- chunk_id 由内容和配置确定性生成（SHA-256），同输入稳定
- metadata 为原文档深拷贝，修改输出不影响输入

### 来源映射

每个 chunk 包含 document_id、block_id、char_start/char_end（半开区间）和 locator。可通过 `/preview#<document_id>/<block_id>` 回查原文位置。字符区间供后续细粒度引用。

### 限制

- 当前为块内固定字符窗口工程基线，不是最终论文结构化算法
- 表格行软上限：超过 max_chars 有警告但不拆分，不补表头
- 合成示例不可用于论文准确率
- 本模块不提供检索、问答或模型调用

## BM25 离线检索

### 运行检索

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.retrieval.search --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus --query "缓考申请" --top-k 5
```

可选参数：`--max-chars N`（分块窗口）、`--top-k N`（返回数量，1—100）。

输出 UTF-8 JSON，可重定向保存：

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.retrieval.search --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus --query "缓考申请" > results.json
```

### 分词策略

当前基线：`cjk_bigram_ascii_v1`

- CJK 连续段长度≥2 → 滑动二元组（如"缓考申请"→["缓考","考申","申请"]）
- CJK 单字保留（"考"→["考"]）
- ASCII 字母数字段整体 lowercase（"ABC2024"→["abc2024"]）
- 其他字符作分隔符，不做停用词/同义词/繁简/拼音处理

**已知限制**：单字查询不会命中长词中的二元组；纯关键词匹配不理解语义。这是工程基线，不是最终中文检索优化。

### BM25 公式

```
idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))
contribution(t,d) = idf(t) * tf(t,d)*(k1+1) / (tf(t,d) + k1*(1-b+b*dl(d)/avgdl))
```

默认参数：k1=1.5, b=0.75。查询词去重后按首次出现顺序求和，零词频项不贡献。

### 输出计数

- `chunk_count`：上游分块器产生的总块数（含无词元块）
- `indexed_chunk_count`：实际参与 BM25 统计的有效块数（至少有一个词元）

纯标点或空文本块不参与索引。当 `indexed_chunk_count < chunk_count` 时说明部分块无可检索内容，这不是加载错误。

### 命中结构

每条命中包含：rank、score、chunk（完整独立拷贝）、preview_url、matched_terms（含 term/tf/df/idf/contribution）。

### 无命中示例

```powershell
& .\.venv\Scripts\python.exe -m campus_assistant.retrieval.search --manifest .\examples\parse-corpus\manifest.json --corpus-root .\examples\parse-corpus --query "不存在的查询"
```

输出 `hits: []`，valid=true，exit 0。

### 限制

- 纯关键词检索，不理解语义或同义词
- 不持久化索引、不调用模型、不生成答案
- 真实语料未提供，不报告 Recall/MRR
- Jieba/BGE/FAISS/RRF 主路线后续单独比较

## 证据搜索页面

### 启动服务

```powershell
# 默认服务（未配置语料，搜索返回 503）
& .\.venv\Scripts\python.exe -m uvicorn campus_assistant.main:app --host 127.0.0.1 --port 8000

# 示例服务（加载合成语料）
& .\.venv\Scripts\python.exe -m uvicorn campus_assistant.demo:app --host 127.0.0.1 --port 8001
```

### 浏览地址

- 搜索页：http://127.0.0.1:8001/search
- 预览页：http://127.0.0.1:8001/preview
- API 文档：http://127.0.0.1:8001/docs

### API 端点

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/v1/search/status` | GET | 搜索索引状态（始终 200），含 `available_modes`、`embedding_model`（简洁模型 ID）、`embedding_model_revision`、`truncated_chunk_count`、`embedding_error`、`filter_options` |
| `/api/v1/search` | POST | 搜索 `{"query":"缓考","top_k":5,"mode":"bm25","filters":{...}}` |

`mode` 可选 `bm25`（默认）、`dense`、`hybrid`。未启用模型时 dense/hybrid 返回 503/RETRIEVER_UNAVAILABLE。`filters` 可选，见「适用条件筛选」。

### 三模式检索

| 模式 | 说明 | 依赖 |
|---|---|---|
| bm25 | CJK 二元组 + ASCII 小写分词，BM25 排序 | 无额外依赖 |
| dense | BGE-small-zh-v1.5 本地向量编码，归一化点积排序 | sentence-transformers + 模型文件 |
| hybrid | BM25 + Dense 各取前 20，RRF(k=60) 融合 | 同 dense |

**向量检索说明**：
- 查询加检索前缀 `为这个句子生成表示以用于检索相关文章：`，正文不加
- 使用 `normalize_embeddings=True`，CPU float32 推理
- 模型仅从本地目录加载（`local_files_only=True`），不接受 Hub ID 或远程拉取；加载失败保留 BM25/预览并在 status 给出中文原因
- 模型进程内只加载一次，文档向量一次批量构建；重复查询只编码 query
- 模型 token 上限（max_seq_length）保留不动；超长块在向量计算中可能仅部分参与，构建时统计 `truncated_chunk_count`，原文与 chunk 文本从不被截短覆盖
- dense 的 `matched_terms=[]`（无词级匹配）
- hybrid 可附 bm25_rank/dense_rank/bm25_score/dense_score 供 UI 解释

## 适用条件筛选

POST `/api/v1/search` 的可选 `filters` 对象：`campus`、`student_type`、`admission_year`、`as_of_date`（YYYY-MM-DD）。前三者单值；未填字段不限制。所有已选条件 AND。

```json
{"query": "缓考申请", "top_k": 5, "mode": "hybrid",
 "filters": {"campus": "成都校区", "admission_year": 2024, "as_of_date": "2025-09-01"}}
```

### 筛选语义

- 指定维度必须在文档 `scope` 对应数组中。空数组表示未知，不是适用所有人；该维度被筛选时排除未知并计数。
- 日期筛选采用两端包含区间：`effective_from` 已知且 ≤ 查询日；`effective_to` 已知时要求查询日 ≤ 该值。`effective_to=null` 表示未标注截止，不证明永久有效（结果注明）。`effective_from=null` 时无法确认适用日期，排除并计数。`published_at` 不代替 `effective_from`。
- 不凭标题或 `version_label` 猜“最新版”；同一家族多个匹配版本都保留。
- 各模式使用同一文档准入集合，先准入后取 Top-K（BM25 保持全库 IDF；Hybrid 各路从准入集合取前 20、从 1 排名后 RRF）。无候选直接返回空结果，不回退到不符合条件的文档。
- 未提供任何筛选时，候选与排名与不带筛选的版本完全一致。
- 筛选结果是证据检索的资料准入，不是学生资格结论或政策答案。

### 响应回显与计数口径

响应 `filters` 回显规范化条件；`filter_summary` 给出 `document_total` / `allowed_count` / `excluded_counts`（scope_unknown、scope_mismatch、date_unknown_from、not_yet_effective、expired）及 `counting_rules` 口径说明。每份被排除文档只计入首个命中原因，各原因计数互斥。

### 筛选演示（真实本地模型 + 合成夹具）

```powershell
# 生成/校验筛选演示夹具（examples/filter-demo，5 份合成文档）
& .\.venv\Scripts\python.exe -m campus_assistant.corpus.validate --manifest .\examples\filter-demo\manifest.json --corpus-root .\examples\filter-demo

# 同一问题换年级/日期的筛选 API 演示（输出 JSON）
& .\.venv\Scripts\python.exe scripts\demo-filter-search.py --model-path models\bge-small-zh-v1.5 --corpus examples\filter-demo
```

搜索页提供校区/类型/年级下拉（选项由 status 的 `filter_options` 从已解析语料提取）、查询日期输入和“清除条件”。提交后展示该次查询实际采用的条件与结果数量；之后编辑控件不会改写已展示的条件说明。无结果区分“没有满足所选条件的资料”与“满足条件的资料中没有检索命中”。

## 证据整理与引用式问答（/ask）

围绕问题整理原文证据、逐条打开出处，并为未来生成模型预留可注入契约。**本节功能是离线摘录与协议验证；真实问答联调（供应商/base URL/model ID/预算）待下一任务，由用户之后提供，密钥经本地配置且不进入报告。**

### API

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/v1/ask/status` | GET | 运行模式与生成器配置（`answer_modes_available`、`generator_configured`） |
| `/api/v1/ask` | POST | `{"query":"…","mode":"bm25","filters":{…},"answer_mode":"extractive"}` |

`query`/`mode`/`top_k`/`filters` 与 `/api/v1/search` 规则完全一致（共享同一检索管线 `retrieval/service.py`，含 T011 筛选语义）。`answer_mode` 默认 `extractive`。

**extractive（默认）**：返回 `status=evidence_only`、`answer=null`、编号证据列表与中文说明“以下是相关原文摘录，尚未生成答案，需核对适用条件”。无检索命中 / 无符合条件的资料 / 预算装不下分别以 `evidence_state`（no_hits / no_admissible_docs / budget_empty）说明，不能凭空回答；检索错误依旧是错误（503），不包装成正常无答案。

**generated（契约已定义，未接真实模型）**：由 `create_app(answer_provider=…)` 注入 `qa.providers.AnswerProvider`。未配置时返回 503/GENERATOR_NOT_CONFIGURED，摘录不会伪装成生成答案；产品不附带任何假模型端点。

- 输入：query、实际选取的证据、筛选条件；输出：`{"type":"answer","paragraphs":[{"text","evidence_ids"}]}` 或 `{"type":"insufficient_evidence","reason"}`。
- 校验（全部通过才输出）：每段至少一个引用；引用必须属于本次实际发送的证据编号；空输出/非法格式/未知引用视为生成失败（502），不返回部分坏答案。
- `insufficient_evidence` 是独立状态，检索非空时不强行作答；生成器异常/失败不影响搜索与预览，可改用原文摘录。
- 来源链接与原文跳转一律由服务从证据映射解析，不让生成器提供路径或链接；段落与引用是结构化对应，不从 Markdown 猜引用。
- 有效引用只证明定位有效，不证明语义支持正确；真实答案质量仍需人工评价。

### 证据包与上下文预算

- 一次请求内为去重后的命中分配 `E1`、`E2`…（仅本请求内有效）。摘录即 chunk 原文，保留半开区间，不改写、不拼接假区间。
- 预算是**字符**上限（默认总计 6000 字符、最多 5 条），不是 token 预算：整条装入或整条略过并记录 `skipped_items`，不为超长条目编造摘要。

### 页面 /ask

输入问题、选条件后“整理依据”：显示提交快照、醒目的“原文摘录 / 未生成答案”标签、编号证据卡与“查看原文”跳转，可一键复制问题+条件+带来源摘录的纯文本（复制失败有明确提示）。未配置生成器时“生成答案”按钮禁用并提示“自动作答未配置”，原文整理不受影响。页面与 `/search`、`/preview` 互通。

“生成答案”（需配置生成器）返回的段落带 E 编号引用：点击编号定位并高亮对应证据卡，卡片可打开原文；复制内容含答案/摘录、编号与来源。生成失败时提供“查看本次问题的原文依据”（沿用失败请求的问题/条件快照走原文摘录，不调用模型）。生成失败、材料不足、纯摘录三种结果有明确区分标签。

**本机历史（T015，默认关闭）**：勾选“在本机保存历史”后，成功的问答结果（自动生成/原文摘录/材料不足）连同提交快照与来源保存在**此浏览器 localStorage**（最多 20 条，新的替换最旧的；不保存密钥与异常）。列表支持查看（本地恢复、不发任何请求）、删除单条、清空；恢复的历史标注保存时间与“历史结果，资料可能已更新”。取消勾选即停止保存新结果，已保存记录保留可清空。存储不可用时给出提示且不影响当前问答。页面明确这不是学校账户记录。

本地页面演示（模拟生成器，输出带【模拟输出】标记，**非真实 DeepSeek 回答**，不进产品启动路径；同一服务也提供 /procedures 办事页面）：

```powershell
& .\.venv\Scripts\python.exe scripts\demo-ask-page-mock.py --port 8010
# 打开 http://127.0.0.1:8010/ask；提问含“模拟失败”可演示生成失败转原文依据
# 演示材料不足分支请提问“缓考申请模拟不足”（含可检索词，命中证据后进 mock）
```

## 办事指南与我的待办（T016）

**合成资料功能原型，不是四川农业大学现行办事指南**：事项模板（`examples/procedures/procedures.json`，两个：缓考申请、成绩复核）只从 parse-corpus 实际文本整理，每个步骤绑定原文引用（文档/块/字符跨度/哈希）；原文未说明的项目显示“资料未说明，请向办理部门核实”，不编造材料/部门/截止日期。个人待办不上传学校、不提交申请、不代表学校受理或资格认证。

### API 与页面

| 端点 | 说明 |
|---|---|
| GET `/api/v1/procedures` | 事项列表（模板由工厂显式注入；未配置返回 503） |
| POST `/api/v1/procedures/{id}/draft` | 按与搜索一致的 filters 生成草稿：逐条核对来源（准入/哈希/跨度）；必要来源不符合筛选、缺失或变化时 `saveable=false`（资料不足/依据需更新），不输出冒充完整的可保存清单，不放宽筛选 |
| POST `/api/v1/procedures/{id}/verify` | 核对已保存清单的依据快照与当前模板/语料（unchanged/changed），不改动用户进度 |

页面 `/procedures`：事项卡片 + 四项筛选 → 带引用步骤草稿（原文展开/查看原文/合成标记）→“保存到我的待办”→ 进度勾选、个人备注、个人步骤、个人提醒日期（升序排列、无日期置后、已过期/今日/以后标注）、排序、删除、未完成/已完成筛选、“核对当前依据”。政策步骤（原文引用，不可改写）与个人步骤（本机内容）明确区分。

### Windows 启动（合成模板由演示入口显式启用）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-ask-page-mock.py --port 8010   # 页面演示（含 /ask 与 /procedures）
# 或（配置真实生成器时）：
# & .\.venv\Scripts\python.exe -m uvicorn campus_assistant.demo:app --port 8001
```

### 本机存储与清理

- 待办仅保存在浏览器 localStorage（键 `campus_procedures_todos_v1`），**点击“保存到我的待办”前不写入**；最多 20 份清单，达到上限需先删除，不静默丢弃。
- 清理：页面“删除本清单”，或浏览器开发者工具 → Application/存储 → localStorage 删除该键；关闭保存/删除均不涉及服务器数据（本项目无数据库无账户）。
- “核对当前依据”仅本地比对来源哈希/模板版本/筛选条件；变化时提示复核并保留勾选与备注，不静默覆盖。

## 政策版本对比（T017）

对比同一政策分组下两个版本的**条款文字差异**（新增/删除/修改/未变）。**不判断哪个版本适用于某个学生；日期较新不等于现行有效，旧版本不等于失效版本**；差异不构成资格或政策适用结论。

### API

| 端点 | 说明 |
|---|---|
| GET `/api/v1/comparison/groups` | 政策分组与版本列表（来自当前已加载语料；未配置 503） |
| POST `/api/v1/comparison` | `{"left_document_id","right_document_id"}` → 两侧元数据、四类计数、块级差异条目（两侧原文/跨度/文档身份/哈希/预览链接）。同文档或跨政策组返回 400 |

确定性对齐算法：① 第X条标识优先配对（新增条款不会使后续条款错位）→ ② 未编号正文保持顺序精确匹配 → ③ 未编号剩余相似度配对为修改 → ④ 其余新增/删除。修改条目附句内差异标记，两侧整段原文逐字保留。**当前仅比较段落（paragraph）块，表格块不参与对比——不含表格差异**（用于 DOCX 时勿把未展示的表格变化当作无变化）；重复条号中未参与标识配对的其余同号条款直接归入新增/删除（不做正文匹配）。其余限制（条款重编号/移动）见响应 `algorithm.limitations` 与页面显示。

### 页面与演示

`/compare`：政策分组与左右版本选择、交换左右、对比、四类计数与明确文字标签（不只靠颜色）、默认只看变化/显示全部、两侧原文展开（不截断）与查看原文跳转、复制差异摘要（含版本身份、差异类型、条款原文与来源）。

```powershell
# 页面演示（显式注入合成比较语料 examples/comparison-corpus，虚构政策）
& .\.venv\Scripts\python.exe scripts\demo-comparison-page.py --port 8020
# 打开 http://127.0.0.1:8020/compare

# 本地 API 演示（含手工期望对照表生成）
& .\.venv\Scripts\python.exe scripts\demo-comparison-api.py --out-dir '<submissions/T017>'
```

对比结果只显示**服务器当前已加载**语料：更新语料文件后需重启演示/服务重新加载，不做磁盘实时监控。默认产品启动不注入合成比较语料。

## 条件自查（T019，转专业条件 · 合成演示）

有限规则的**个人条件自查演示**：四项三态（是/否/不确定或未填写）→ 确定性判断 → 逐项满足/不满足/待核实 + 原文引用。**不代表学校审核结果，不受理申请，不构成录取/批准/申请成功**；不收集姓名、学号、违纪详情；填报仅本次请求内处理，不写报告/日志/localStorage。

- 规则配置 `examples/self-check/rule.json`（rule_version 1.0）显式绑定 parse-corpus 第五条各句（文档/块/跨度/哈希），由工厂 `self_check_path` **显式注入**——普通未配置服务返回 503，不自动启用合成规则。
- 判断语义：未知**不计为满足**；任一“否”→“存在未满足项”；无“否”但有未知→“仍有待核实项”；全“是”→“按自填信息满足本演示列出的条件；仍需学校审核”。依据未通过筛选准入/缺失/哈希变化 → “依据不足，无法完成自查”，不利用失效原文算通过（失效引用不携带原文）。排名按自报“是否前 30%”三态，不换算并列/取整；未参加考核记为待核实，与明确未通过区分。
- API：GET `/api/v1/self-check/rule`、POST `/api/v1/self-check`（`filters` 同搜索四项；`answers` 按 item 的 answer_field 三态）。引用链接由服务器绑定，不接受客户端拼接引用。

### 页面与演示场景（Windows）

```powershell
# 统一演示（含自查入口；显式注入合成规则）
Set-Location 'F:\Collage Paper\step2_code\backend'; & .\.venv\Scripts\python.exe scripts\demo-campus.py --port 8030
# 打开 http://127.0.0.1:8030/self-check （或从首页“条件自查”进入）
```

四个可操作场景：**全满足**（四项“是”→按自填信息满足/仍需学校审核）；**缺考核信息**（考核选“不确定/未填写”→仍有待核实项）；**一个不满足**（任一项“否”→存在未满足项）；**依据被筛除**（入学年份填 2022（统一演示下拉可选）→ 依据不足，无法完成自查）。全部为合成资料与确定性规则，不代表真实校园资格准确率。

API 示例与规则原文对照：`docs/collaboration/submissions/T019/selfcheck-api-demo.json` 与 `rule-text-crosscheck.md`。

## 本地语音输入（T020，Windows CPU 离线识别）

ask 页支持“短录音/上传音频 → 本地中文转写 → 编辑确认 → 用户明确填入问题框”闭环。**本地推理（FunASR Paraformer），不接云端 ASR、不调用 DeepSeek、不上传音频**；转写/填入均不自动提问或生成。

- **模型准备（与运行分离）**：`scripts/download-asr-model.py` 下载一份公开模型到 `.cache/asr-models/paraformer-zh`（如遇代理 TLS 劫持可加 `$env:NO_PROXY='modelscope.cn'` 仅对当前进程直连）。服务**仅从本地目录加载，不自动下载**。
- **启用方式**：环境变量 `CAMPUS_ASR=funasr` + `CAMPUS_ASR_MODEL_DIR=<模型目录>`；或统一演示 `demo-campus.py --asr-model-dir .cache\asr-models\paraformer-zh`。未配置时 `/api/v1/asr/status` 明确不可用，文字问答不受影响。
- **API**：`GET /api/v1/asr/status`（provider/model/限额）、`POST /api/v1/asr/transcribe`（原始音频体；WAV 与浏览器 MediaRecorder 实际支持的 WebM/Opus；服务端 5MB / 30 秒硬限；单并发繁忙 409；损坏/空音频与执行错误为清晰提示）。响应含转写文本、实际 provider/model、音频时长与耗时；无可靠置信度即为 null，不伪造。推理走线程池不阻塞事件循环；音频仅请求内处理，结束/失败即清理，不保留音频或转写日志。
- **页面语义**：仅点击录音才请求麦克风；权限被拒/无设备/非安全上下文时提示并保留上传与文字入口；停止后显式“转写音频”；取消与离开释放音轨；识别文本在独立编辑区展示，“使用此文本/替换问题输入”才写入问题框；转写与填入都不自动发起问答——仍需手动点“整理依据/生成答案”。
- 真实转写证据（合成 TTS 音频，标注来源）：`docs/collaboration/submissions/T020/asr-evidence.md`；依赖/模型来源记录：`dependencies-model.md`。

### 提示词模板

`qa/providers.PROMPT_TEMPLATE` 为未来真实 provider 的简洁模板：只据输入原文、保留条件/数字、材料不足时明确说明；文档内容视为资料而非指令。

### 演示命令

```powershell
# 真实 extractive API 演示（本地语料、BM25、不调用任何模型）
& .\.venv\Scripts\python.exe scripts\demo-ask.py --corpus examples\parse-corpus
```

## 文本 PDF 解析与语料接入（T021）

### 文本 PDF 解析（pypdf，无 OCR）

语料管线支持 TXT/DOCX/**文本 PDF**（pypdf 6.19.0 逐页提取，不做 OCR/LLM 补正文）：

- **块定位**：`{"type":"pdf_page","page":N,"part":K}`（1 基页码 + 页内段序）；块 ID 种子用 **PDF 独立解析器版本 `pdf-1.0`**——全局 PARSER_VERSION 保持 1.0，旧 TXT/DOCX 块 ID 与模板/规则引用**不受影响**。
- **提取规范化**：逐行去尾部空白、换行统一 `\n`、连续空行折叠为一个空行（段落分隔）；不改写任何非空白字符。引用跨度相对提取块逐字一致；不宣称与视觉排版/阅读顺序完全等价（复杂表格/多栏仅按提取顺序，不做结构识别）。
- **不可用状态明确**：全篇无文本 → “全篇未提取到文本…需要 OCR/人工核对”，不进索引、不算解析成功；某页无文本（混合文档）→ 明确列出缺失页并整篇暂不入索引（空白页≠扫描件断言）；加密/损坏 → 明确失败，不解密绕过。
- **前台**：preview 显示“PDF 第 N 页 · 段 K”；search 命中与 ask 摘录显示页码，preview_url 跳转对应提取块。
- 演示夹具 `examples/pdf-corpus/`（`scripts/make-pdf-fixtures.py` 本地生成：fpdf2 + 本机 SimHei；两页中文文本 PDF 含数字/否定词 + 无文本 PDF），独立于旧 parse/comparison 语料，gold 未动。

### 本地语料登记 CLI

```powershell
& .\.venv\Scripts\python.exe scripts\register-corpus.py --input <本地文件.txt|docx|pdf> --meta <元数据.json> --out-dir <全新的候选包目录>
```

复制原文（逐字节，不修改输入）+ 计算哈希 + 生成 manifest → 复用既有校验/解析检查输出可读结果与启动命令。缺必填元数据**明确列出、不猜测**标题/日期/适用范围；输出目录非空拒绝覆盖；不下载 source_url。元数据 JSON 字段见脚本头部示例（TXT/DOCX/PDF 同一入口）。

启动候选包（**不加载**合成办事模板/自查规则/mock 生成器）：

```powershell
& .\.venv\Scripts\python.exe scripts\serve-corpus.py --manifest <候选包>\manifest.json --corpus-root <候选包>
```

## 统一运行入口（T022，推荐正常入口）

**正常运行只用这一个入口**：`scripts/serve-corpus.py`（指定语料包 + 按需显式开启功能；全部默认关闭，除指定语料外不隐式加载任何 example/模板/规则/mock）。`demo-campus.py` 保留为**明确的离线模拟演示**入口（合成语料 + 标记 mock 生成器 + 演示问题首页），二者用途不同。

### 配置组合与依赖说明

| 组合 | 命令选项 | 能力 | 额外依赖 |
|---|---|---|---|
| 最小运行 | `--manifest`/`--corpus-root` | BM25 检索、原文摘录、预览 | 核心依赖即可 |
| 检索增强 | + `--embedding-model-dir <本地模型目录>` | 关键词/语义/混合三模式 | torch/sentence-transformers（T010） |
| 语音输入 | + `--asr-model-dir <本地模型目录>` | 录音/上传转写 | funasr + kaldi-native-fbank + av（T020） |
| 办事/自查 | + `--procedures <模板.json>` / `--self-check <规则.json>` | 事项草稿/条件自查 | 无额外 |
| 生成器 | + `--generator deepseek` | 生成答案（用户点击才调用） | httpx（既有）；密钥仅本地环境变量 |
| 规划器（T024） | + `--planner deepseek` | DeepSeek 结构化规划（用户点击才调用；默认关闭，与生成器相互独立） | httpx（既有）；密钥仅本地环境变量 |

配置优先级：显式 CLI 参数；生成器/规划器密钥**仅**来自本地环境变量（`CAMPUS_GENERATOR`/`CAMPUS_PLANNER`/`DEEPSEEK_API_KEY`），不出现在命令行、配置 JSON、状态接口或日志。请求启用但缺配置 → 明确“已降级”提示，不静默当成功；“已配置”与“已验证（模型加载/服务连接/联调）”分开表述，启动不探测模型服务。

规划器说明（T024）：`--planner deepseek` 注入 DeepSeekPlanner（结构化动作 call/finish/awaiting_input，每轮至多一次规划 HTTP、零自动重试、≤4 轮 ≤6 工具）。**启动、状态刷新、固定流程零规划请求**；仅用户显式点击“运行 DeepSeek 规划”触发。状态区分 off/simulated/deepseek，并始终标注 `planner_live_verified=false`（已配置 ≠ 已联调验证）。`demo-campus.py` 始终显式模拟规划，不因环境配置切到真实服务。本地 mock/loopback 联调见 `docs/collaboration/submissions/T024/`。

### 规划器真实冒烟 CLI（T025）

`scripts/live-smoke-planner.py`：单次可复现冒烟（固定合成题「查找缓考依据并整理办理草稿」/proc-apply-defer/年级 2023）。

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
# dry-run（默认，零网络、无需密钥；产出配置计划与核对表模板值）
& .\.venv\Scripts\python.exe scripts\live-smoke-planner.py --mode dry-run --out dry-run.json
# 本地 mock 示例（loopback 显式联调，非真实冒烟）
& .\.venv\Scripts\python.exe scripts\smoke-mock-sample.py --out mock-run.json
# --live：官方端点一次真实冒烟——须用户明确授权（B 阶段）且本地 DEEPSEEK_API_KEY 已配置后才可执行
# & .\.venv\Scripts\python.exe scripts\live-smoke-planner.py --mode live --out smoke-result.json
```

默认 dry-run 零网络；调用前配置核对（官方端点/`deepseek-flash`/max_tokens=300、语料全部 `is_synthetic=true`、固定题/模板）不过则**零请求非零退出**；实际 HTTP 计数在发送处观察、零重试；逐条结果核对表按实际动作生成（不预写通过结论）；`--mode mock` 仅接受 loopback 地址，不静默作为 live 降级分支。B 阶段（`--live`）授权前不得执行。

### 论文与答辩交付包（T028）

系统设计、论文结构底稿、证据矩阵、答辩脚本与 Windows 运行说明见 `docs/delivery/`（项目根目录），入口索引为 `docs/delivery/README.md`。

### 可复制启动命令（Windows PowerShell，含空格路径已引用）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'

# 最小运行
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest 'F:\Collage Paper\step2_code\backend\examples\parse-corpus\manifest.json' `
  --corpus-root 'F:\Collage Paper\step2_code\backend\examples\parse-corpus'

# 完整可选组合（按需删减；全部默认关闭）
# $env:CAMPUS_GENERATOR = 'deepseek'; $env:DEEPSEEK_API_KEY = '<本地密钥占位>'  # 仅环境变量
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest 'F:\Collage Paper\step2_code\backend\examples\parse-corpus\manifest.json' `
  --corpus-root 'F:\Collage Paper\step2_code\backend\examples\parse-corpus' `
  --embedding-model-dir 'F:\Collage Paper\step2_code\backend\models\bge-small-zh-v1.5' `
  --asr-model-dir 'F:\Collage Paper\step2_code\backend\.cache\asr-models\paraformer-zh' `
  --procedures 'F:\Collage Paper\step2_code\backend\examples\procedures\procedures.json' `
  --self-check 'F:\Collage Paper\step2_code\backend\examples\self-check\rule.json' `
  --generator deepseek
```

首页 `/` 为中性“校园助手”，实时展示当前服务能力（语料成功/错误数与资料性质、检索模式、生成器/ASR/模板/规则配置状态、可比较版本），并注明“已配置≠已验证”。合成演示问题只出现在 demo-campus 的演示首页。启动、状态刷新与原文摘录均**零生成请求**；生成器启用后仅用户点击“生成答案”才调用。实测能力对照见 `docs/collaboration/submissions/T022/config-combos.md`。

### 真实资料接入说明

1. **需要的原文**：学校公开文档的本地文件（TXT/DOCX/文本 PDF）+ 来源页面信息（来源网址、站点名）。不爬取网站——由用户自行下载提供。
2. **元数据填写**：`document_id`/`policy_group_id` 自定唯一 ID；`title`/`source_url`/`source_site`/`version_label` 按来源页面如实填写；`published_at`/`effective_from`/`effective_to` 未知写 `null`（不猜测）；`scope` 未知用空数组（**空数组=未知，不等于适用所有人**）；真实资料 `is_synthetic` 必须 `false`（合成演示资料才是 `true`）。
3. **PDF 人工核对**：登记后用 preview 页逐块核对提取文本与页码（对照原文，数字/否定词/条款号），确认无缺页/乱序问题再启动服务；某页“未提取到文本”即需 OCR/人工补资料，不强行入索引。
4. **正常资料库启动**用 `serve-corpus.py`：只加载所给语料，**不得默认加载**合成办事模板、自查规则或 mock 生成器（这些仅由测试/演示显式注入）。

**首批真实语料包（T029，当前版本 v1.1）**：`data/corpora/sicau-rag-pilot-v1.1/`（20 份真实资料，来源=用户提供的 `data/datasets/sicau-rag-v1`，原字节与哈希保留）。

```powershell
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1\manifest.json' `
  --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1'
```

语料包由 `scripts/prepare-real-corpus.py`（--dataset-root/--selection/--out-dir；重复执行进入核验模式，任何输入/边车漂移非零退出且不覆盖）生成；清单适配与版本关系见 `docs/collaboration/submissions/T029/mapping-notes.md`。**未知元数据不猜测**（日期=null、适用范围=空数组）；用户加筛选时空数组=未知会被保守排除，如实说明。

**v1 → v1.1 差异**（T029-R1）：同一批 20 份原字节与文档 ID（逐字节一致）；① `source_site` 改按已选 source_url 主机解析（2 处纠正：d1fe991c rwy→jiaowu、92049a1c jiaowu→jwnews；原来源页面站点完整保留在 provenance）；② 补正 2 份已核实日期（bb8ba97c 发文/生效 2025-11-11、68fb3704 发文 2018-12-20，原文页码/原句见 selection notes）；其余未核实日期继续 null。**v1 包保留**于 `data/corpora/sicau-rag-pilot-v1/`（历史证据，勿覆盖）。

## 统一离线演示入口（T018）

一条命令启动**全部五个功能 + 统一首页**的离线演示服务（问答、证据搜索、办事与待办、版本对比、语料预览）：

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-campus.py --port 8030
# 打开 http://127.0.0.1:8030/ （统一首页）
```

- **组合演示语料**：启动时把 `examples/parse-corpus` 与 `examples/comparison-corpus` 重建组合到 `.cache/demo-campus-corpus/`——保留原文档 ID、内容与哈希，两份原始夹具与 gold 只读不动；文档 ID 冲突显式报错不静默覆盖。夹具更新后**重启服务**重新组合（不监控磁盘）。
- **模拟生成器**：显式注入标记 mock（输出带【模拟输出，非真实 DeepSeek 回答】），**不读取真实生成器配置、不自动调用 DeepSeek**；首页状态实时读取自当前服务。T014 曾有一次限定真实 DeepSeek 冒烟（历史证据），本演示零外部调用。
- **问答→办事联动**：问答结果带“相关事项入口”（显式关键词映射，非 Agent 推理，不代表符合办理条件），点击带入该结果的问题与条件快照进入办事页（URL 参数，不含答案原文/密钥）；办事页显式显示带入条件、等选项加载后恢复值（缺失选项保留并提示），仍需手动生成草稿、不自动保存/调用模型；历史结果使用历史条件。
- 组合语料扩大检索候选：演示可使用清晰筛选条件；不伪造检索结果。
- 答辩 5—8 分钟演示脚本与逐步检查表见 `docs/collaboration/submissions/T018/demo-notes.md`。各独立演示入口（demo-ask-page-mock / demo-comparison-page / demo:app）保持原样可用。

## DeepSeek 生成适配（T013）

`qa/deepseek.py` 提供对接 DeepSeek Chat Completions 的 `DeepSeekAnswerProvider`（T012 协议）：model=`deepseek-flash`，`POST {base}/chat/completions`（单一拼接规则，不重复 /v1），`response_format={"type":"json_object"}`（提示词含 "json" 与结构示例），`thinking={"type":"disabled"}`（非思考模式），`stream=false`，`max_tokens=1500`，超时 30 秒，无自动重试。空内容/非法 JSON/finish_reason=length 截断均视为生成失败，不展示为完整答案；HTTP 401/429/5xx、超时映射为可理解中文错误，不输出密钥或服务原始异常内容。

### Windows 配置（密钥用占位值示例）

```powershell
# 当前会话启用 DeepSeek 生成（默认不启用；搜索/摘录始终可用）
$env:CAMPUS_GENERATOR = 'deepseek'
$env:DEEPSEEK_API_KEY = 'sk-REPLACE-WITH-LOCAL-KEY'   # 真实密钥只放本地，不进报告/提交
$env:DEEPSEEK_BASE_URL = 'https://api.deepseek.com'    # 可省略（默认值）
$env:DEEPSEEK_MODEL    = 'deepseek-flash'              # 可省略（默认值）
```

也可参考 `env.example`（仅占位值）。只有 `CAMPUS_GENERATOR=deepseek` 且 `DEEPSEEK_API_KEY` 非空时才注入 provider；启动不发送探测请求。status 的 `generator_configured` 只代表本地配置完整，不代表服务已验证。

**可选 NO_PROXY（仅当前进程）**：若本机系统代理导致 `api.deepseek.com` 连接失败（代理路径 TLS 连接失败），可在启动前对当前进程设置直连，不修改系统代理或全局环境：

```powershell
$env:NO_PROXY = 'api.deepseek.com'
$env:no_proxy = 'api.deepseek.com'
```

### 启动（含生成配置时）

```powershell
& .\.venv\Scripts\python.exe -m uvicorn campus_assistant.demo:app --host 127.0.0.1 --port 8001
```

响应中的 `generation_meta`（model、供应商 request id、usage、耗时、max_tokens）为非敏感审计字段，供应商未返回的字段为 null。

### mock 联调与 live 冒烟

```powershell
# 本地 loopback mock 全链路演示（不发外部请求；模拟输出不等于真实 DeepSeek 回答）
& .\.venv\Scripts\python.exe scripts\demo-deepseek-mock.py --corpus examples\parse-corpus

# live 冒烟脚本默认 dry-run（本地检索 + 审查摘要，无网络、无需密钥）：
# 两道合成问题（可回答：缓考审批/备案·年级2023；材料不足：宿舍门禁·不限），
# 保留完整审计字段（status/generation_meta/调用记录），仅答案预览截短
# （--answer-preview-chars 限 1—2000，不是 token/费用限制）；失败退出非零；
# ask_requests 与 external_http_attempts 分开计数（无证据短路不算模型调用）。
# 调用前置检查（任何请求之前）：语料须解析有效、非空且全部 is_synthetic=true；
# 缺生成器配置、无效/非合成语料均退出非零；--live 先在 stderr 展示并核对实际
# endpoint/model/max_tokens，与本任务授权的官方值不符即拒绝，不向未授权地址发请求。
& .\.venv\Scripts\python.exe scripts\live-smoke-deepseek.py

# 真实官方调用尚未授权：仅在用户明确提供调用授权 + 本地密钥配置后执行
# （最多两次 HTTP 尝试、max_tokens=1500、无重试、首次技术失败即停）：
# & .\.venv\Scripts\python.exe scripts\live-smoke-deepseek.py --live --full-answers-out live-answers-full.local.json
```

说明：本机若有系统代理，loopback mock 需 `trust_env=False`（已内置到演示/测试）；真实调用默认尊重系统/环境代理。DeepSeek 模型名是别名（alias），不是固定权重 revision。

### 快照语义

- 工厂启动时 parse_manifest → chunk_documents → BM25Index 各调用一次
- 配置模型时额外：EmbeddingService 加载 → 文档编码 → DenseIndex 构建
- 请求只查询索引，不重建；重复请求不重复构建
- 重启服务重新加载语料，本阶段不做热更新
- `/api/v1/health/ready` 继续返回 503（知识问答未就绪）

## 检索评测

### 运行评测

```powershell
# BM25 模式（默认）
& .\.venv\Scripts\python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --top-k 5

# 向量模式
& .\.venv\Scripts\python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --top-k 5 --mode dense --model-path models/bge-small-zh-v1.5

# 混合模式
& .\.venv\Scripts\python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --top-k 5 --mode hybrid --model-path models/bge-small-zh-v1.5
```

可选参数：`--top-k N`（默认 5，范围 1—20）、`--mode bm25|dense|hybrid`、`--model-path <dir>`（dense/hybrid 必需，本地目录）。

输出含 `embedding_model_id` / `embedding_model_revision`（从下载元数据核实，无法核实为 unknown）、`truncated_chunk_count` 与 `truncation_note`（长块可能仅部分参与向量计算，原文与 chunk 不被截短）。评测默认不带筛选，与旧结果可比；筛选验证使用独立夹具（examples/filter-demo），不改 8 题 gold。

### 问题集契约

UTF-8 JSON，顶层必需 `schema_version="1.0"`、`dataset_id`、`dataset_version`、`split`、`is_synthetic`（严格布尔）、`questions`（非空数组）。所有结构拒绝未知字段。

每题必需：`question_id`（全数据集唯一）、`query`（1—500 字符）、`answerable`（严格布尔）、`evidence`（数组）。answerable=true 必须非空 evidence，false 必须空。`split` 固定为 "dev"。题内 evidence_id 唯一，来源区间（document_id+block_id+char_start+char_end）唯一。

每个 evidence 包含：`evidence_id`、`document_id`、`document_sha256`、`parser_version`、`block_id`、`char_start`（≥0）、`char_end`（>char_start）、`quote`（与原块切片逐字符相同）。

### 指标

| 指标 | 定义 | 适用 |
|---|---|---|
| Evidence Recall@K | 完整覆盖的必要证据数 / 该题必要证据总数 | answerable=true |
| Hit@K | Top-K 中是否存在与任一 gold 区间有交集的结果 | answerable=true |
| MRR@K | 第一条相关结果的排名倒数 | answerable=true |

- 三项仅在 answerable=true 的题上宏平均
- answerable=false 不参与分母，单独记录 `empty_result_rate`
- 金标准指向原文块中的字符区间，不绑定 chunk_id

### 示例输出（三模式对比）

合成开发集 8 题（6 可答 + 2 不可答）在 parse-corpus 上的对比：

| 模式 | Evidence Recall | Hit | MRR | 说明 |
|---|---|---|---|---|
| BM25 | 1.0 | 1.0 | 0.917 | CJK 二元组关键词匹配 |
| Dense (bge-small-zh) | 1.0 | 1.0 | 0.917 | 语义向量相似度 |
| Hybrid (RRF) | 1.0 | 1.0 | 0.917 | BM25 + Dense RRF 融合 |

合成数据量小，三种模式均达到完美召回。真实语料规模更大时预期会有差异。

每题详情：q01 mrr=0.5（首条非最相关）；q02-q06 mrr=1.0；q07-q08 不可答。

### 限制

- 合成开发集验证评测流程，不代表论文准确率
- 金标准为人工标注的字符区间，不绑定 chunk_id
- 真实语料题集在用户提供资料后另行标注
- 不支持等价替代证据组或测试集冻结
- 向量检索使用 CPU 推理，大规模语料需考虑 FAISS

## 复现验证（可选）

创建独立环境验证锁文件可复现：

```powershell
& D:\Anaconda\python.exe -m venv .venv-verify
& .\.venv-verify\Scripts\python.exe -m pip install --cache-dir .cache/pip -r requirements.lock.txt
& .\.venv-verify\Scripts\python.exe -m pip install --cache-dir .cache/pip --no-deps --no-build-isolation -e .
& .\.venv-verify\Scripts\python.exe -m pytest -q
```
