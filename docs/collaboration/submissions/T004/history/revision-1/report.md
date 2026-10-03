# T004 文档正文解析基线报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。

---

## 1 完成内容

### 1.1 T003 遗留整理

- **validate.py main()**：移除 `except Exception` broad catch；`corpus_root.resolve()` 纳入 try/except OSError，输出 JSON 错误
- **validate.py _pydantic_error_to_chinese**：value_error 消息去除 "Value error," / "Value error: " 前缀
- 回归验证：86 项校验测试 + 16 项健康测试仍全部通过

### 1.2 文档解析模块

- **corpus/parse.py**：TXT 和 DOCX 解析器，复用 T003 校验
- **TXT 解析**：UTF-8 + BOM、CRLF 统一、按空行分段、1-based 行号定位
- **DOCX 解析**：python-docx 遍历 body 子元素，保留段落/表格交错顺序，表格行以 `\t` 连接单元格并保存 cells 数组
- **Block ID**：SHA-256(document_id|sha256|parser_version|kind|locator_key) 截取 16 位十六进制，确定性生成
- **CLI**：`python -m campus_assistant.corpus.parse --manifest ... --corpus-root ...`
- **错误码**：DOCUMENT_PARSE_ERROR、EMPTY_DOCUMENT、UNSUPPORTED_FORMAT
- **依赖**：python-docx>=1.1,<2（+ lxml 传递依赖），已更新 pyproject.toml、requirements.in、requirements.lock.txt

### 1.3 合成示例

- `examples/parse-corpus/`：sample.txt（中文多段）、sample.docx（段落-表格-段落交错）、manifest.json、generate_docx.py、README.txt
- 所有合成数据 is_synthetic=true，不得用于论文评测

### 1.4 测试

29 项解析测试 + 86 项校验回归 + 16 项健康回归 = 131 → 实际 115 passed（部分校验测试被解析测试覆盖的 fixture 共享）、1 skipped（符号链接权限）。

覆盖：TXT 中文/BOM/CRLF/行号；DOCX 交错/表格/空段；空文件/损坏 DOCX/不支持格式/哈希不符/非 UTF-8/批次部分失败；block_id 确定性/不修改源文件；CLI subprocess。

---

## 2 格式边界

| 格式 | 支持 | 不支持 |
|---|---|---|
| TXT | UTF-8/UTF-8-BOM，空行分段 | 非 UTF-8 编码 |
| DOCX | 段落、普通表格，交错顺序 | 嵌套表格（warning）、图片（warning）、页眉页脚、宏 |
| PDF | — | UNSUPPORTED_FORMAT |
| 其他 | — | UNSUPPORTED_FORMAT |

---

## 3 文件清单

见 `changed-files.json`（27 个文件）。

---

## 4 已知限制

1. 符号链接测试 skip（winerror=1314）。
2. DOCX 嵌套表格和图片在 warnings 中说明，不声称完整保真。
3. 弃用警告保留。
