# T004 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=3，响应 T004-R2。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`127 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0
- **输出**：`No broken requirements found.`

## V03 水平合并检测

- 使用 `table.cell(0,0).merge(table.cell(0,1))` 创建真实横向合并
- 结果：warnings 含"水平合并" ✓

## V04 垂直合并检测

- 使用 `table.cell(0,0).merge(table.cell(1,0))` 创建真实纵向合并
- 结果：warnings 含"合并" ✓

## V05 内联图片检测

- 创建 minimal PNG（2×2 红色像素，手工构造无 PIL），`d.add_picture()`
- 结果：warnings 含"内联图片" ✓

## V06 简单文档无警告

- 纯文本段落 DOCX：`warnings=[]` ✓

## V07 示例 CLI

- valid=true, document_count=2, TXT 6 blocks, DOCX 11 blocks

## V08 R1—R3 回归

- 空行定位、损坏 DOCX 隔离、UTF-8 原始输出：全部通过（127 passed 包含）

## V09 generate_docx.py

- 输出路径固定到 `Path(__file__).parent / "sample.docx"`
- 说明结构可复现、ZIP 字节不保证相同
- 哈希更新步骤已写入脚本文档
