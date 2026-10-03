# T006 正文分块与来源映射报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。task_revision=v1，submission_revision=1。

---

## 1 完成内容

### 1.1 分块器

`corpus/chunk.py` 公开 `chunk_documents(documents, *, max_chars=500)`，纯函数，不修改输入。

- **paragraph**：固定字符窗口滑动，start=0,max_chars,...，end=min(start+max_chars,len(text))，无重叠，不 trim/清洗/重复
- **table_row**：整行一个 chunk，完整保留 cells 和 text；超过 max_chars 不拆行，附 `TABLE_ROW_EXCEEDS_MAX_CHARS` 警告
- **chunk_id**：SHA-256(document_id, metadata.sha256, parser_version, block_id, chunker_version, strategy, max_chars, char_start, char_end, text)，ensure_ascii=False, separators=(',',':')，确定性生成
- **metadata**：原文档独立深拷贝，修改输出不影响输入
- **warnings**：独立复制原文档警告并追加本块警告

### 1.2 CLI

```
python -m campus_assistant.corpus.chunk --manifest <path> --corpus-root <path> [--max-chars 500]
```

stdout UTF-8 JSON：schema_version, chunker_version, strategy, max_chars, valid, document_count, parsed_count, chunk_count, chunks, errors。退出码 0=全部成功，1=部分/全部失败，2=参数错误。

### 1.3 测试

45 项分块测试覆盖：精确切分、字符区间、拼接等于原文、边界、换行/emoji、空文本、表格整行、超长表格警告、空 cells/text 异常、多块排序、多文档排序、metadata 深拷贝、chunk_id 稳定性、参数校验（0/-1/10001/float/string/bool）、未知 kind、CLI 成功/失败/用法错误/UTF-8/单次 parse 调用/部分失败保留。

### 1.4 示例 CLI 输出

```
valid=true, chunks=17, document_count=2, parsed_count=2
首 chunk: syn-parse-txt-001, paragraph, char_range(0, 26)
```

---

## 2 文件清单

见 `changed-files.json`（33 个文件）。新增：`corpus/chunk.py`、`tests/test_corpus_chunk.py`。修改：`backend/README.md`。

---

## 3 已知限制

1. 当前为块内固定字符窗口工程基线，不是最终论文结构化算法。
2. 表格行软上限：超过 max_chars 有警告但不拆分，不补表头。
3. 合成示例不可用于论文准确率。
