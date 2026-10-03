# T003 语料登记与校验报告

执行者：Mimo（Claude Code）。执行时间：2026-09-12。任务修订：v1。submission_revision：3。响应 T003-R2。

---

## 0 R2-A/B/C 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| A | 日期字段有默认值，date.fromisoformat 接受紧凑/周日期 | 移除 `= None` 默认值（必需但允许显式 null）；严格 YYYY-MM-DD 正则 + date.fromisoformat 双重校验 |
| B | NUL 路径导致 CLI 输出非 JSON 堆栈 | `_is_safe_local_path` 拒绝 `\x00`；resolve/exists/is_file 用 try/except 转为 JSON 错误；main() 末尾兜底 JSON |
| C | Pydantic 英文消息直传 + broad except | `_pydantic_error_to_chinese` 映射已知类型为中文；value_error 提取自定义中文消息；移除 model_validate 的 broad except |

---

## 1 A：日期字段修复

- `published_at`、`effective_from`、`effective_to`：移除 `= None` 默认值，声明为 `Optional[str]`（必需字段，允许显式 null）
- 验证顺序：正则 `^\d{4}-\d{2}-\d{2}$` → `date.fromisoformat()`
- 拒绝：`"20240901"`（紧凑格式）、`"2024-W36-7"`（周日期）、`"2024-13-01"`（非法月份）、`"2025-02-29"`（非闰年）
- 通过：`null`（显式 null）、`"2024-09-01"`（合法日期）
- 缺失字段：Pydantic 报 "此字段为必填项"

## 2 B：NUL 路径修复

- `_is_safe_local_path`：新增 `"\x00" in local_path` 检查，返回 UNSAFE_LOCAL_PATH
- `_resolve_within_root`：`(root / local_path).resolve()` 包裹 try/except (ValueError, OSError)
- 文件状态检查：`resolved.exists()` 和 `resolved.is_file()` 各自包裹 try/except
- `main()` 末尾：`validate_manifest` 调用包裹 try/except，兜底输出 JSON

## 3 C：中文错误消息

- `_pydantic_error_to_chinese`：映射 string_type→"必须是字符串"、missing→"此字段为必填项"、extra_forbidden→"不允许的额外字段" 等
- `value_error` 类型：直接使用验证器的中文消息（已全部使用中文 ValueError）
- 移除 `except Exception` broad catch（model_validate 只抛 ValidationError）

## 4 符号链接 skip 详情

skip 消息记录实际异常：`OSError winerror=1314 errno=22`（"A required privilege is not held by the client"）。

## 5 测试

86 passed，1 skipped（符号链接权限 winerror=1314）。新增：
- 缺日期字段（published_at/effective_from 各自缺失）
- 显式 null 日期通过
- 紧凑格式 "20240901" 拒绝
- 周日期 "2024-W36-7" 拒绝
- NUL 路径拒绝（单元测试 + subprocess JSON 输出）
- 中文错误消息：缺字段→"必填"、类型错误→"数组"、未知字段→"不允许"

## 6 已知限制

1. 符号链接逃逸测试 skip（winerror=1314，权限不足）。
2. 弃用警告保留。
