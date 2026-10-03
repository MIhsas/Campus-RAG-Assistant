# T007 验证记录

执行时间：2026-09-13。submission_revision=2，响应 T007-R1。

---

## V01 全量 pytest

- **退出码**：0
- **输出**：`258 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 JS 语法检查

- **退出码**：0
- **输出**：`JavaScript syntax OK`

## V04 valid_chunk_count 属性测试

- test_all_valid: 2 valid chunks → valid_chunk_count=2 ✓
- test_empty_excluded: 1 empty of 3 → valid_chunk_count=2 ✓
- test_all_empty: 2 empty → valid_chunk_count=0 ✓
- test_punctuation_only_excluded: 1 punct + 1 valid → valid_chunk_count=1 ✓

## V05 CLI indexed_chunk_count 回归

| 场景 | chunk_count | indexed_chunk_count | hits | exit |
|---|---:|---:|---:|---:|
| 有效+标点混合 | 2 | 1 | 1 | 0 |
| 全标点 | 2 | 0 | 0 | 0 |
| 空文件 | 0 | 0 | 0 | 1 |
| 示例语料 | 17 | 17 | 3 | 0 |

## V06 chunk_manifest 单次调用

- monkeypatch 计数验证调用 1 次 ✓

## V07 已有测试保留

- BM25 算术金例、词频饱和、长度归一化、去重查询、贡献加和、深拷贝隔离 ✓
- CLI 成功命中、无命中、部分失败、参数错误 exit 2、UTF-8 输出 ✓
