# T003 验证记录

执行时间：2026-09-12。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=3，响应 T003-R2。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`86 passed, 1 skipped, 2 warnings`
- **说明**：16 健康 + 70 语料校验。skipped = 符号链接权限不足（winerror=1314）。

## V02 pip check

- **命令**：`.venv/Scripts/python.exe -m pip check`
- **退出码**：0
- **输出**：`No broken requirements found.`

## V03 示例 CLI 成功

- **命令**：`.venv/Scripts/python.exe -m campus_assistant.corpus.validate --manifest ./examples/synthetic-corpus/manifest.json --corpus-root ./examples/synthetic-corpus`
- **退出码**：0
- **输出**：`{"valid": true, "document_count": 2, "errors": []}`

## V04 R2-A 日期验证

| 测试 | 输入 | 结果 |
|---|---|---|
| 缺 published_at | 字段缺失 | rejected (必填) |
| 缺 effective_from | 字段缺失 | rejected (必填) |
| 显式 null | published_at=null | accepted |
| 紧凑格式 | "20240901" | rejected (YYYY-MM-DD 格式) |
| 周日期 | "2024-W36-7" | rejected (YYYY-MM-DD 格式) |
| 非法月份 | "2024-13-01" | rejected |
| 非闰年 | "2025-02-29" | rejected |
| 合法日期 | "2024-09-01" | accepted |

## V05 R2-B NUL 路径

- **单元测试**：`_minimal_valid(local_path="bad\x00name.txt")` → UNSAFE_LOCAL_PATH ✓
- **subprocess**：CLI exit 1，stdout 可解析 JSON，code=UNSAFE_LOCAL_PATH，stderr 无 Traceback ✓

## V06 R2-C 中文错误消息

| 测试 | 场景 | 输出消息包含 |
|---|---|---|
| 缺 title | 字段缺失 | "必填" |
| campus="not a list" | 类型错误 | "数组" |
| unknown field | 未知字段 | "不允许" 或 "额外" |

## V07 符号链接 skip 详情

- **skip 原因**：`OSError winerror=1314 errno=22`
- **含义**：A required privilege is not held by the client

## V08 健康接口回归

- live 200 + ready 503，X-Request-ID 与 body 一致

## V09 changed-files.json

- 20 项字节数和 SHA-256 全部由 Python 标准库生成
