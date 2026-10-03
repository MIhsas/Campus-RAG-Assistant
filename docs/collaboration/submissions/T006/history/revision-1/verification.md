# T006 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。

---

## V01 分块测试

- **命令**：`.venv/Scripts/python.exe -m pytest tests/test_corpus_chunk.py -q`
- **退出码**：0
- **输出**：`45 passed`

## V02 全量 pytest

- **退出码**：0
- **输出**：`196 passed, 1 skipped, 2 warnings`

## V03 pip check

- **退出码**：0

## V04 JS 语法检查

- **退出码**：0
- **输出**：`JavaScript syntax OK`

## V05 示例 CLI

- **命令**：`.venv/Scripts/python.exe -m campus_assistant.corpus.chunk --manifest ./examples/parse-corpus/manifest.json --corpus-root ./examples/parse-corpus`
- **退出码**：0
- **输出**：valid=true, chunk_count=17, document_count=2, parsed_count=2

## V06 正文到 chunk 完整示例

输入 TXT 文档 `syn-parse-txt-001`，首段文本"【合成测试文件 — 不得用于论文评测或真实校园问答】"（26 字符），max_chars=500：
- chunk_id: `609b22c2ad981fe4...`（SHA-256 前 16 位）
- kind: paragraph
- char_start: 0, char_end: 26
- locator: {"type":"lines","line_start":1,"line_end":1}
- cells: null
- metadata.sha256: ea716fadda...
- chunker_version: 1.0
- strategy: block_window_v1
- max_chars: 500
- warnings: []

来源映射：`/preview#syn-parse-txt-001/<block_id>`
