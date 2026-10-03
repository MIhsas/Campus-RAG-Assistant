# T008 检索接口与证据搜索页报告

执行者：Mimo（Claude Code）。执行时间：2026-09-14。task_revision=v1，submission_revision=1。

---

## 0 T007 测试修正

**TestChunkManifestCalledOnce**：原测试 patch `_run_search`（外层函数），无法验证 `chunk_manifest` 的真实调用次数。修正为 patch `campus_assistant.corpus.chunk.chunk_manifest`，通过 `_run_search` 直接调用验证计数=1。新增 CLI 参数错误 exit 2 测试。

---

## 1 工厂快照

`create_app` 解析后依次调用：
1. `parse_manifest` → 1 次
2. `chunk_documents(documents, max_chars=500)` → 1 次（不调用 chunk_manifest）
3. `BM25Index(chunks, k1=1.5, b=0.75)` → 1 次

搜索状态：unconfigured / ready / partial / failed，沿用语料状态。构建异常转 failed，记录 INDEX_BUILD_ERROR。默认不读文件/不建索引。

## 2 API 端点

### GET /api/v1/search/status → 200

Pydantic 响应：status, document_count, parsed_count, chunk_count, indexed_chunk_count, synthetic_count, retriever_version, tokenizer_version, chunker_version, max_chars, k1, b, errors, request_id。

### POST /api/v1/search

请求：`{"query": "缓考申请", "top_k": 5}`（query 1-500 字符，top_k 1-20，extra forbid）。

- ready/partial → 200：query, query_tokens, status, chunk_count, indexed_chunk_count, hits, errors, request_id
- unconfigured → 503/CORPUS_NOT_CONFIGURED
- failed → 503/SEARCH_UNAVAILABLE
- 无效输入 → 422（Pydantic validation）
- 全标点查询 → 200 + hits=[]

## 3 搜索页面

`/search` 静态 HTML：标题"证据搜索"、说明"关键词检索结果，不是自动生成的政策答案"、输入框+搜索按钮+Enter 提交、链接到 `/preview`。

结果展示：标题、正文片段、来源站/版本/适用范围/日期、合成标记、"查看原文"跳转 `/preview#doc/block`、`<details>` 匹配依据（词频/IDF/贡献）、分数标"关键词匹配分"。

状态区分：空闲、加载中、无匹配、无有效词元、未配置、接口错误+重试。请求序号保护。

## 4 测试

| 类别 | 数量 | 覆盖 |
|---|---:|---|
| test_search_api | 19 | unconfigured、ready、partial、failed、标点查询、参数拒绝、请求 ID、多 app 隔离、初始化计数、重复请求 |
| test_retrieval_cli 修正 | 2 | chunk_manifest 真实调用=1、参数错误 exit 2 |
| JS 语法 | 2 文件 | preview.html + search.html |

## 5 验证

| 检查 | 结果 |
|---|---|
| 全量 pytest | 277 passed, 1 skipped |
| pip check | pass |
| JS 语法（两页） | pass |
| wheel 含 search.html | ✓ |
| API 冒烟（示例服务） | search/status=ready, POST 3 hits, /search=200 |

## 6 浏览器交互验证

**未验证**。交由 Astra 复核。
