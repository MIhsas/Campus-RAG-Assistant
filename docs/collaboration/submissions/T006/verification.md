# T006 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=2，响应 T006-R1。

---

## V01 分块测试

- **命令**：`.venv/Scripts/python.exe -m pytest tests/test_corpus_chunk.py -q`
- **退出码**：0
- **输出**：`54 passed`

## V02 全量 pytest

- **退出码**：0
- **输出**：`205 passed, 1 skipped, 2 warnings`

## V03 pip check

- **退出码**：0

## V04 JS 语法检查

- **退出码**：0
- **输出**：`JavaScript syntax OK`

## V05 R1 sibling 隔离验证

- 修改 chunk[0].metadata.scope.campus → chunk[1].metadata.scope.campus 不变 ✓
- 修改 chunk[0].locator.line_start → chunk[1].locator 和输入不变 ✓
- 测试：`test_sibling_metadata_independent`、`test_sibling_locator_independent` ✓

## V06 R2 CLI exit code 验证

| 参数 | 退出码 | stdout | parse_manifest 调用 |
|---|---|---|---|
| `--max-chars 0` | 2 | 空 | 否 |
| `--max-chars -1` | 2 | 空 | 否 |
| `--max-chars 10001` | 2 | 空 | 否 |
| `--max-chars abc` | 2 | 空 | 否 |
| `--max-chars 1` | 0 | JSON | 是 |
| `--max-chars 10000` | 0 | JSON | 是 |

## V07 R3 ordinal 排序验证

- 输入 blocks: [ordinal=3, ordinal=1, ordinal=2]
- 输出: ordinal=1 先，ordinal=3 后 ✓
- 输入数组未被修改 ✓

## V08 完整示例

- chunk_id: `b6d87f7b8e04d81963edd60c7bcfa5d9cbb0ba41d92f63ad237bce66f97075cd`
- document_id: `syn-parse-txt-001`
- block_id: `d3e1919af830143d`
- text: "【合成测试文件 — 不得用于论文评测或真实校园问答】"
- char_range: [0, 26)
- 来源映射: `/preview#syn-parse-txt-001/d3e1919af830143d`
