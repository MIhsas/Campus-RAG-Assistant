# T003 验证记录

执行时间：2026-09-12。工作目录：`F:\Collage Paper\step2_code\backend`。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`50 passed, 2 warnings in 2.40s`
- **说明**：16 项健康回归 + 34 项语料校验。2 个弃用警告保留。

## V02 pip check

- **命令**：`.venv/Scripts/python.exe -m pip check`
- **退出码**：0
- **输出**：`No broken requirements found.`

## V03 示例 CLI 成功

- **命令**：`.venv/Scripts/python.exe -m campus_assistant.corpus.validate --manifest ./examples/synthetic-corpus/manifest.json --corpus-root ./examples/synthetic-corpus`
- **退出码**：0
- **输出**：`{"valid": true, "document_count": 2, "errors": []}`

## V04 损坏哈希 CLI 失败

- **操作**：复制示例语料到临时目录，将 policy-abc-v1.txt 内容改为 "corrupted content"（哈希变化）。
- **命令**：`.venv/Scripts/python.exe -m campus_assistant.corpus.validate --manifest /tmp/corpus-bad/manifest.json --corpus-root /tmp/corpus-bad`
- **退出码**：1
- **输出**：
  ```json
  {
    "valid": false,
    "document_count": 1,
    "errors": [
      {
        "code": "HASH_MISMATCH",
        "document_id": "syn-policy-abc-v1",
        "field": "sha256",
        "message": "哈希不符: 预期 a46b66f0e3cca8a6...，实际 e22ba9da67f77f55..."
      }
    ]
  }
  ```
- **说明**：policy-abc-v2 通过（document_count=1），policy-abc-v1 哈希不符被报告。临时目录已清理。

## V05 健康接口回归

- **命令**：启动 uvicorn 于 127.0.0.1:8001，curl 访问两个端点
- **live**：HTTP 200，X-Request-ID: `05204786-fc73-46dc-b115-3e8fc6c3bb1e`，body request_id 一致
- **ready**：HTTP 503，X-Request-ID: `59ce4a83-cf97-4b12-97c3-1b742b264bc3`，KNOWLEDGE_BASE_NOT_CONFIGURED
- **说明**：中间件统一 request ID 后，健康接口行为不变。

## V06 changed-files.json 校验

- **方法**：Python 标准库逐项计算 SHA-256 和字节数
- **文件数**：20
- **说明**：不包含 .venv、.cache、__pycache__、.pytest_cache 或 .egg-info。

## V07 语料校验测试详情

34 项测试分组：

| 分组 | 数量 | 覆盖 |
|---|---:|---|
| TestValidManifest | 3 | 合法清单、中文路径、空范围 |
| TestSchemaErrors | 13 | 缺字段、未知字段、无效 URL/日期/布尔、空文档、版本错误、JSON 解析 |
| TestDuplicateIds | 1 | 重复 document_id |
| TestPathSafety | 6 | 绝对路径、盘符、UNC、..、.、ADS 冒号 |
| TestFileChecks | 3 | 缺失文件、目录、哈希不符 |
| TestMultipleErrors | 1 | 多错误同时收集 |
| TestNoModifyInput | 1 | 不改写输入 |
| TestErrorFormat | 1 | 错误输出格式 |
| TestCLI | 4 | subprocess 成功/失败/用法错误/清单不存在 |
| TestHashComputation | 1 | 大文件分块哈希 |
