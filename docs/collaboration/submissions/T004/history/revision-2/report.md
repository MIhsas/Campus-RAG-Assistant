# T004 文档正文解析基线报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。submission_revision：2。响应 T004-R1。

---

## 0 R1—R4 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | 表格行 row_index 仅对非空行递增，定位偏移 | row_index 对所有源行递增（含空行），ordinal 仅对输出块递增 |
| R2 | DOCX 加载后遍历异常未隔离 | 遍历循环整体包裹 try/except，捕获 ValueError/TypeError/KeyError/AttributeError/ParseError → DOCUMENT_PARSE_ERROR |
| R3 | Windows 默认 CLI 输出非 UTF-8 | `_ensure_utf8_stdout()` 在 main 入口将 stdout 重配为 UTF-8；CLI 测试以原始字节捕获，不注入 PYTHONIOENCODING |
| R4 | 合并单元格、页眉页脚、浮动图片静默忽略 | `_detect_merged_cells`（gridSpan/vMerge）、`_detect_header_footer`、`_detect_floating_images`；warnings 始终存在（空列表或具体提示） |

---

## 1 R1：表格行定位

`source_row_index` 对所有源行递增（含空行），空行跳过输出但行号保留。结果：

- `["", "", "A"]` → A 的 `row_index=3`
- `["A", "", "B"]` → A=1, B=3
- `["A", "", "", "B"]` → A=1, B=4

## 2 R2：异常隔离

遍历阶段 try/except 捕获 `ValueError, TypeError, KeyError, AttributeError, ET.ParseError`，转为 DOCUMENT_PARSE_ERROR，保留同批其他文档结果。损坏 DOCX + 正常 TXT 同批：valid=false, documents=[正常], errors=[损坏]。

## 3 R3：UTF-8 输出

`_ensure_utf8_stdout()` 在 main() 入口将 `sys.stdout` 重配为 `io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")`。CLI 测试以 `stdout=subprocess.PIPE` + `env={}` 原始字节捕获，严格 `decode("utf-8")` 后解析 JSON。

## 4 R4：内容检测

- **合并单元格**：检查 `w:gridSpan`（水平合并）和 `w:vMerge`（垂直合并，非 continue 值）
- **页眉页脚**：遍历 sections 的 header/footer/even/first，非空文本触发警告
- **浮动图片**：检测 `wp:anchor` 元素
- **嵌套表格**：已有检测
- **内联图片**：已有检测
- 无损文档：`warnings=[]`；有损提取：非空且具体

## 5 测试

125 passed, 1 skipped。新增：空首行/中间空行/连续空行定位、损坏 DOCX + 正常 TXT 批次隔离、CLI 原始字节 UTF-8、合并单元格/页眉/无警告检测。

## 6 文档修正

- backend/README.md 新增正文解析章节：命令、UTF-8 保存、block 结构、locator 回查、格式边界、失败语义
- 报告测试计数修正：原 86 已含健康测试，新增 29 后为 115 → 本轮 125（新增 10 项 R1-R4 测试）
