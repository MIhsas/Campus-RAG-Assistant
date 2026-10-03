# T006 正文分块与来源映射报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。task_revision=v1，submission_revision=2。响应 T006-R1。

---

## 0 R1—R3 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | metadata/locator 共享引用，修改一个 chunk 污染兄弟和输入 | 每个 chunk 独立 `copy.deepcopy(meta)` 和 `copy.deepcopy(locator)`；新增 sibling 隔离测试 |
| R2 | CLI `--max-chars 0` 退出 1 而非 2 | CLI 在 argparse 后、路径解析前调用 `_validate_max_chars`；失败时 `parser.error()` 退出 2、stderr 消息、stdout 空 |
| R3 | 未按 block.ordinal 排序 | `sorted(doc.blocks, key=lambda b: b.get("ordinal", 0))` 不修改输入数组；新增乱序 blocks 测试 |

---

## 1 R1：输出对象隔离

```python
# 每个 chunk 循环内独立拷贝
"locator": copy.deepcopy(locator),
"metadata": copy.deepcopy(meta),
```

测试：两个同源 paragraph chunk，修改 chunk[0].metadata.scope.campus → chunk[1] 不变；修改 chunk[0].locator.line_start → chunk[1] 和输入不变。

## 2 R2：CLI 参数验证

`_validate_max_chars(args.max_chars)` 在 `parser.parse_args()` 之后、路径解析之前执行。失败调用 `parser.error(str(e))`：
- argparse 输出 stderr 错误消息
- 退出码 2
- stdout 为空（无 JSON）
- `parse_manifest` 不被调用

测试：`--max-chars 0`、`-1`、`10001`、`abc` → exit 2 + stdout 空；`1` 和 `10000` → exit 0。

## 3 R3：按 ordinal 排序

```python
blocks = sorted(doc.get("blocks", []), key=lambda b: b.get("ordinal", 0))
```

输入 `[ordinal=3, ordinal=1, ordinal=2]` → 输出按 1, 2, 3 排序，输入数组不变。

## 4 完整示例（真实 CLI 输出）

```json
{
  "chunk_id": "b6d87f7b8e04d81963edd60c7bcfa5d9cbb0ba41d92f63ad237bce66f97075cd",
  "document_id": "syn-parse-txt-001",
  "block_id": "d3e1919af830143d",
  "ordinal": 1,
  "kind": "paragraph",
  "text": "【合成测试文件 — 不得用于论文评测或真实校园问答】",
  "char_start": 0,
  "char_end": 26,
  "locator": {"type": "lines", "line_start": 1, "line_end": 1},
  "cells": null,
  "metadata": {
    "document_id": "syn-parse-txt-001",
    "title": "合成测试教务管理办法（正文解析示例）",
    "source_url": "https://example.org/policy/parse/txt",
    "source_site": "合成测试示例站",
    "sha256": "ea716fadda710f98910bc0e14113baf5655091f10f8eece6db15e61563613d07",
    "version_label": "解析示例 v1",
    "published_at": "2025-01-15",
    "is_synthetic": true
  },
  "parser_version": "1.0",
  "chunker_version": "1.0",
  "strategy": "block_window_v1",
  "max_chars": 500,
  "warnings": []
}
```

来源映射：`/preview#syn-parse-txt-001/d3e1919af830143d`，字符区间 [0, 26)。

## 5 验证

| 检查 | 结果 |
|---|---|
| 分块测试 | 54 passed |
| 全量 pytest | 205 passed, 1 skipped |
| pip check | pass |
| JS 语法检查 | pass |
| CLI 示例 | valid=true, 17 chunks |
| R1 sibling 隔离 | pass |
| R2 exit code 2 | pass（0/-1/10001/abc） |
| R3 ordinal 排序 | pass |
