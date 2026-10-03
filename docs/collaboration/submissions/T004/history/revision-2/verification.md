# T004 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=2，响应 T004-R1。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`125 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0
- **输出**：`No broken requirements found.`

## V03 R1 行号验证

| 输入表格 | 行内容 | row_index |
|---|---|---|
| `["", "", "A"]` | A | 3 ✓ |
| `["A", "", "B"]` | A=1, B=3 | ✓ |
| `["A", "", "", "B"]` | A=1, B=4 | ✓ |

## V04 R2 异常隔离

- 损坏 DOCX（截断 XML）+ 正常 TXT 同批：valid=false, documents=[正常 TXT], errors=[DOCUMENT_PARSE_ERROR] ✓
- subprocess 无 Traceback ✓

## V05 R3 原始编码测试

- `env={}`（无 PYTHONIOENCODING）+ 中文含α：`proc.stdout.decode("utf-8")` → JSON 解析成功 ✓
- 失败场景同上 ✓

## V06 R4 警告检测

- 合并单元格（gridSpan）→ warnings 含"合并" ✓
- 非空页眉 → warnings 含"页眉" ✓
- 简单文档 → `warnings=[]` ✓

## V07 示例 CLI

- **命令**：`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m campus_assistant.corpus.parse --manifest ./examples/parse-corpus/manifest.json --corpus-root ./examples/parse-corpus`
- **退出码**：0
- **输出**：valid=true, document_count=2, TXT 6 blocks, DOCX 11 blocks（含 warnings key）

## V08 复现验证

- .venv-verify：125 passed, 1 skipped
