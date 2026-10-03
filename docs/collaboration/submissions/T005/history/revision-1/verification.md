# T005 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`149 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0
- **输出**：`No broken requirements found.`

## V03 API 冒烟（示例服务）

启动 `uvicorn campus_assistant.demo:app --host 127.0.0.1 --port 8003`：

| 端点 | 状态 | 结果 |
|---|---|---|
| /api/v1/corpus/status | 200 | status=ready, document_count=2, parsed_count=2 |
| /api/v1/corpus/documents | 200 | items=2, 格式 TXT/DOCX |
| /api/v1/corpus/documents/syn-parse-txt-001 | 200 | blocks=6 |
| /api/v1/corpus/documents/unknown | 404 | DOCUMENT_NOT_FOUND |
| /preview | 200 | 12852 bytes, 含"语料预览" |

服务已停止。

## V04 预览测试详情

| 分组 | 数量 | 覆盖 |
|---|---:|---|
| TestUnconfigured | 3 | status=unconfigured, documents 503, detail 503 |
| TestReadyState | 4 | status=ready, 列表2项, 详情blocks, 未知ID 404 |
| TestPartialState | 2 | partial状态（1成功1失败）, failed验证 |
| TestRequestId | 3 | status/documents/detail 均有 request_id |
| TestAppIsolation | 1 | 配置/未配置 app 独立 |
| TestParseOnce | 1 | 多请求读同一快照 |
| TestFactoryValidation | 2 | manifest/root 必须配对 |
| TestPreviewPage | 2 | 可访问, 不同 cwd 可用 |
| TestOpenApi | 2 | corpus 端点在 schema, 503 声明 |
| TestHealthRegression | 2 | live 200, ready 503 不变 |
| TestCliSmoke | 1 | demo 模块加载成功 |

## V05 浏览器交互验证

Claude Code 无浏览器能力，未进行浏览器交互验证。标记为**未验证**，交给 Astra 复核。

## V06 changed-files.json

- 31 项文件字节数和 SHA-256 由 Python 标准库生成
