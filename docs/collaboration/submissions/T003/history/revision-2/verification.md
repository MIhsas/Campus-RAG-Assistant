# T003 验证记录

执行时间：2026-09-12。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=2，响应 T003-R1。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`76 passed, 1 skipped, 2 warnings`
- **说明**：16 项健康回归 + 60 项语料校验。1 skipped 为符号链接权限不足。

## V02 pip check

- **命令**：`.venv/Scripts/python.exe -m pip check`
- **退出码**：0
- **输出**：`No broken requirements found.`

## V03 示例 CLI 成功

- **命令**：`.venv/Scripts/python.exe -m campus_assistant.corpus.validate --manifest ./examples/synthetic-corpus/manifest.json --corpus-root ./examples/synthetic-corpus`
- **退出码**：0
- **输出**：`{"valid": true, "document_count": 2, "errors": []}`

## V04 损坏哈希 CLI 失败

- **操作**：复制示例到临时目录，修改 policy-abc-v1.txt 内容
- **退出码**：1
- **输出**：valid=false，HASH_MISMATCH for syn-policy-abc-v1，document_count=2（两个结构合法条目）

## V05 非 UTF-8 清单（R3）

- **操作**：写入 `\xff\xfe\x00{` 字节
- **退出码**：1
- **输出**：`{"valid": false, "document_count": 0, "errors": [{"code": "MANIFEST_READ_ERROR", ...}]}`

## V06 null campus（R3）

- **操作**：scope.campus=null
- **退出码**：1
- **输出**：`{"valid": false, "document_count": 0, "errors": [{"code": "MANIFEST_SCHEMA_ERROR", ...}]}`

## V07 健康接口回归

- **live**：200，X-Request-ID 与 body request_id 一致
- **ready**：503，KNOWLEDGE_BASE_NOT_CONFIGURED

## V08 R1 字段约束验证详情

| 测试 | 输入 | 结果 |
|---|---|---|
| is_synthetic="false" | 字符串 | rejected (MANIFEST_SCHEMA_ERROR) |
| is_synthetic="true" | 字符串 | rejected |
| is_synthetic=True/False | 布尔 | accepted |
| published_at="2024-13-01" | 非法月份 | rejected (MANIFEST_SCHEMA_ERROR, published_at) |
| published_at="2025-02-29" | 非闰年 | rejected |
| published_at="2024-09-01T12:00:00" | 时间戳 | rejected |
| scope 缺失 | 无 scope 字段 | rejected |
| scope={} | 空对象 | rejected |
| admission_years=["2024"] | 字符串 | rejected |
| admission_years=[1899] | 超范围 | rejected |
| campus=["  "] | 空白 | rejected |
| campus="abc" | 非数组 | rejected |
| campus=None | null | rejected |
| source_url="https://?query" | 无主机 | rejected |
| source_url="https://user:pass@..." | 凭据 | rejected |

## V09 R4 document_count 验证

| 场景 | 期望 count | 实际 |
|---|---|---|
| 2 结构合法 + 1 坏哈希 | 2 | 2 ✓ |
| schema 失败 | 0 | 0 ✓ |
| 2 合法 + 重复 ID + 坏文件 | 2 | 2 ✓ |

## V10 changed-files.json

- **方法**：Python 标准库逐项计算
- **文件数**：20
- **说明**：不包含 .venv、.cache、__pycache__ 或 .pytest_cache
