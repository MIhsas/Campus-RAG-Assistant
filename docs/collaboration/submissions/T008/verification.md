# T008 验证记录

执行时间：2026-09-14。submission_revision=4，响应 T008-R3。

---

## V01 全量 pytest

- **退出码**：0
- **输出**：`295 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 JS 语法检查

- **退出码**：0
- **输出**：`preview.html: syntax OK`, `search.html: syntax OK`

## V04 R1 DOCX InvalidXmlError 隔离

- 正常 TXT + 坏 DOCX（parse_manifest）：valid=false、good doc 保留 ✓
- 仅坏 DOCX（parse_manifest）：failed、无 documents ✓
- 工厂集成（good+bad）：partial、search 200 有命中、live 200、ready 503 ✓
- 工厂集成（仅 bad）：failed、search 503、live 200 ✓

## V05 R2 按钮恢复

- 空白分支 `btn.disabled = false`（源码确认）✓

## V06 R3 ID 严格匹配

| 测试 | 结果 |
|---|---|
| 1 字符 ID | pass |
| 64 字符 ID | pass |
| 65 字符 ID → rejected | pass |
| `good\n` → rejected | pass |
| `good\r\n` → rejected | pass |
| `go\nod` → rejected | pass |
| ` good ` → rejected | pass |
| policy_group_id `bad\n` → rejected | pass |
