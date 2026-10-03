# T004 文档正文解析基线报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。submission_revision：3。响应 T004-R2。

---

## 0 R4 修复摘要

| 问题 | 修复 |
|---|---|
| 合并检测路径错误 | `tc.find(w:gridSpan)` → `tc.find(w:tcPr).find(w:gridSpan)`，vMerge 同理 |
| 测试用伪造 XML 层级 | 改用 `cell.merge()` 生成真实横向/纵向合并 |
| 内联图片检测被删除 | 恢复 `doc.inline_shapes` 检测 |
| generate_docx.py 路径和描述 | 固定输出到 `Path(__file__).parent / "sample.docx"`，说明结构可复现但 ZIP 字节不一定相同，提供哈希更新步骤 |

---

## 1 合并单元格检测

`_detect_merged_cells` 现在查找 `w:tcPr` 子元素内的 `w:gridSpan` 和 `w:vMerge`：

```
w:tc → w:tcPr → w:gridSpan (水平合并)
w:tc → w:tcPr → w:vMerge   (垂直合并)
```

测试使用 `table.cell(r1,c1).merge(table.cell(r2,c2))` 生成真实合并文档，确认警告触发。

## 2 图片检测

- **内联图片**：`doc.inline_shapes` 非空时警告
- **浮动图片**：`wp:anchor` 元素检测
- 两者均报告一次，不重复

## 3 generate_docx.py

- 输出路径：`Path(__file__).parent / "sample.docx"`（固定到示例目录）
- 说明：结构可复现（相同段落/表格/文本），ZIP 字节不保证相同
- 提供哈希更新命令

## 4 测试

127 passed, 1 skipped。新增：水平合并（cell.merge）、垂直合并（cell.merge）、内联图片（minimal PNG）。

## 5 官方资料来源

- python-docx: https://python-docx.readthedocs.io/
- python-docx PyPI: https://pypi.org/project/python-docx/
- lxml: https://lxml.de/
