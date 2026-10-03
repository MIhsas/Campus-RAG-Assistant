# T007 离线 BM25 检索基线报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。task_revision=v1，submission_revision=1。

---

## 1 完成内容

### 1.1 分词器

`retrieval/tokenize.py`：`tokenize(text) -> list[str]`，策略 `cjk_bigram_ascii_v1`。

- CJK 连续段长度≥2 → 滑动二元组；长度=1 → 单字保留
- ASCII 字母数字段整体 lowercase
- 其他字符作分隔符，不跨段合并，不做停用词/同义词/拼音/Unicode 规范化

### 1.2 BM25 索引

`retrieval/bm25.py`：`BM25Index(chunks, *, k1=1.5, b=0.75)` + `search(query, *, top_k=5)`。

- 正 IDF 变体：`idf(t) = ln(1 + (N - df(t) + 0.5) / (df(t) + 0.5))`
- 查询词去重后按首次出现顺序求和，零词频项不贡献
- 词频饱和、长度归一化（b 参数）
- 同分按 chunk_id 字符串升序稳定排序
- 输入深拷贝，输出结果独立
- chunk_id 唯一校验，重复报错

### 1.3 检索 CLI

```
python -m campus_assistant.retrieval.search --manifest <path> --corpus-root <path> --query "缓考申请" [--max-chars 500] [--top-k 5]
```

调用 chunk_manifest 一次，UTF-8 JSON 输出。参数验证先于文件读取。退出码 0=成功（含无命中）、1=上游错误、2=参数错误。

### 1.4 测试

45 项检索测试（12 tokenize + 25 BM25 + 8 CLI）。覆盖：手工分词断言、BM25 算术金例、词频饱和、长度归一化、未知词、空索引、top_k、去重查询、贡献加和、重复 ID、参数校验、深拷贝隔离、CLI 成功/无命中/部分失败/参数错误/UTF-8。

### 1.5 示例输出

查询"缓考申请"在 parse-corpus 上：valid=true, 3 hits, 17 chunks indexed。

---

## 2 文件清单

见 `changed-files.json`（40 个文件）。新增：`retrieval/__init__.py`、`tokenize.py`、`bm25.py`、`search.py`、3 个测试文件。修改：`backend/README.md`、`step2_code/README.md`。

---

## 3 已知限制

1. CJK 二元组基线，单字查询不命中长词二元组。
2. 纯关键词检索，不理解语义或同义词。
3. 不持久化索引、不调用模型、不生成答案。
4. Jieba/BGE/FAISS/RRF 主路线后续单独比较。
