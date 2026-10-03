# T004 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`115 passed, 1 skipped, 2 warnings`
- **说明**：16 健康 + 70 校验 + 29 解析。skipped = 符号链接权限（winerror=1314）。

## V02 pip check

- **命令**：`.venv/Scripts/python.exe -m pip check`
- **退出码**：0
- **输出**：`No broken requirements found.`

## V03 解析 CLI 成功

- **命令**：`PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe -m campus_assistant.corpus.parse --manifest ./examples/parse-corpus/manifest.json --corpus-root ./examples/parse-corpus`
- **退出码**：0
- **输出**：valid=true, document_count=2, documents 含 TXT（6 blocks）和 DOCX（11 blocks）
- **TXT block 示例**：
  ```json
  {"block_id": "542187ebbac5a4b2", "ordinal": 2, "kind": "paragraph",
   "text": "第一条 学生应当按照教学计划...", "locator": {"type": "lines", "line_start": 3, "line_end": 3}}
  ```
- **DOCX table_row 示例**：
  ```json
  {"block_id": "...", "ordinal": 3, "kind": "table_row",
   "text": "20240001\t张三\t高等数学A1\t85",
   "locator": {"type": "table_row", "table_index": 1, "row_index": 2},
   "cells": ["20240001", "张三", "高等数学A1", "85"]}
  ```

## V04 解析 CLI 失败（空文件）

- **场景**：空 TXT → EMPTY_DOCUMENT, exit 1

## V05 解析 CLI 失败（损坏 DOCX）

- **场景**：伪造 DOCX 字节 → DOCUMENT_PARSE_ERROR, exit 1

## V06 不支持格式

- **场景**：.pdf 文件 → UNSUPPORTED_FORMAT, exit 1

## V07 哈希不符时不解析

- **场景**：sha256 填 "0"*64 → HASH_MISMATCH（来自校验），解析不执行

## V08 批次部分失败

- **场景**：1 个合法 TXT + 1 个损坏 DOCX → valid=false, documents=[合法], errors=[损坏]

## V09 Block ID 确定性

- 重复运行同一清单 → block_id 完全一致
- 不同 document_id → block_id 不同

## V10 源文件未修改

- 解析前后 TXT 和 DOCX 文件字节完全一致

## V11 复现验证

- **环境**：.venv-verify（从锁文件全新安装）
- **结果**：115 passed, 1 skipped

## V12 T003 清理验证

- **validate.py main()**：无 broad except，corpus_root.resolve() 在 try/except 内
- **中文消息**：Pydantic "Value error," 前缀已去除
- **回归**：86 项校验测试仍全部通过
