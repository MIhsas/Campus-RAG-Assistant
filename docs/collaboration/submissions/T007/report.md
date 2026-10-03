# T007 离线 BM25 检索基线报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。task_revision=v1，submission_revision=2。响应 T007-R1。

---

## 0 R1 修复摘要

**问题**：`indexed_chunk_count` 等于 `len(chunks)`（总块数），掩盖了无词元块。纯标点或空文本块被报告为"已索引"。

**修复**：
- BM25Index 新增 `valid_chunk_count` 只读属性，返回实际参与 BM25 统计的有效块数（N）
- search.py `_run_search` 使用 `index.valid_chunk_count` 替代 `len(chunks)`
- README 新增输出计数说明，区分 `chunk_count`（总块数）和 `indexed_chunk_count`（有效索引数）

---

## 1 BM25Index.valid_chunk_count

```python
@property
def valid_chunk_count(self) -> int:
    """Number of chunks with at least one token (actual N used in BM25)."""
    return self._N
```

- `chunk_count`：上游分块器产生的总块数（含无词元块）
- `indexed_chunk_count`：实际参与 BM25 统计的有效块数（至少有一个词元）
- 纯标点或空文本块不参与索引，`indexed_chunk_count < chunk_count` 不是加载错误

## 2 新增测试

| 测试 | 场景 | chunk_count | indexed | hits | exit |
|---|---|---:|---:|---:|---:|
| test_mixed_valid_and_punctuation | 有效+标点 | 2 | 1 | 1 | 0 |
| test_all_punctuation | 全标点 | 2 | 0 | 0 | 0 |
| test_no_chunks_empty_doc | 空文件 | 0 | 0 | 0 | 1 |
| test_valid_chunk_count（4 项） | 属性正确性 | — | — | — | — |
| test_single_call | chunk_manifest 单次调用 | — | — | — | — |

## 3 验证

| 检查 | 结果 |
|---|---|
| 全量 pytest | 258 passed, 1 skipped |
| pip check | pass |
| JS 语法检查 | pass |
| 示例 CLI | chunk_count=17, indexed=17, hits=3 |
