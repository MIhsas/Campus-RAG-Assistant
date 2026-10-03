# T002 最小后端工程报告

执行者：Mimo（Claude Code）。执行时间：2026-09-12。任务修订：v1。

---

## 1 完成内容

按 T002 任务书建立 FastAPI 后端起点，包含：

- **应用入口**：`create_app()` 工厂函数，支持多次实例化。
- **健康接口**：`/api/v1/health/live`（200）和 `/api/v1/health/ready`（503）。
- **请求追踪**：所有响应携带服务端生成的 `X-Request-ID`，客户端值不被信任或回显。
- **隔离环境**：`backend/.venv`，基于 Python 3.12（D:\Anaconda），sys.prefix != sys.base_prefix 已验证。
- **依赖锁定**：`requirements.lock.txt` 从实际 freeze 生成，去除 editable 项。
- **测试**：16 项 pytest，覆盖任务书全部七项验证行为。
- **复现验证**：`.venv-verify` 独立环境从锁文件安装并测试通过。

---

## 2 文件清单

见 `changed-files.json`。共 11 个文件：

| 类别 | 文件 |
|---|---|
| 配置 | `.gitignore`、`pyproject.toml`、`requirements.in`、`requirements.lock.txt` |
| 应用代码 | `__init__.py`×2、`main.py`、`health.py` |
| 测试 | `test_health.py` |
| 文档 | `step2_code/README.md`、`backend/README.md` |

---

## 3 接口实现

### GET /api/v1/health/live → 200

```json
{"status": "ok", "service": "campus-assistant-backend", "version": "0.1.0", "request_id": "<uuid>"}
```

### GET /api/v1/health/ready → 503

```json
{"status": "not_ready", "code": "KNOWLEDGE_BASE_NOT_CONFIGURED", "message": "知识库尚未配置", "retryable": false, "request_id": "<uuid>"}
```

### X-Request-ID

- 服务端每次请求生成新 UUID，不信任客户端传入值。
- 健康接口 JSON 内 `request_id` 与响应头 `X-Request-ID` 一致。
- 404 响应同样携带追踪头。

---

## 4 验证结果摘要

| 编号 | 行为 | 结果 |
|---|---|---|
| 1 | live 200 + 约定字段 | ✅ 通过 |
| 2 | ready 503 + 业务码 + 中文提示 | ✅ 通过 |
| 3 | request_id UUID 且与头一致，连续请求不同 | ✅ 通过 |
| 4 | 客户端 X-Request-ID 不回显 | ✅ 通过 |
| 5 | 404 + 追踪头 | ✅ 通过 |
| 6 | OpenAPI 包含两个端点，ready 声明 503 | ✅ 通过 |
| 7 | create_app() 多次实例化，无外部依赖 | ✅ 通过 |

pytest：16 passed（主环境 + 复现环境各一次）。
pip check：No broken requirements found。

---

## 5 已知限制

1. 无数据库、RAG、模型调用或前端。ready 503 是本阶段预期，不是故障。
2. 锁文件面向 Python 3.12 / Windows，其他平台未测试。
3. Starlette TestClient 产生两个弃用警告（httpx 星标版本和 anyio.abc.BlockingPortal），不影响功能。
4. 不初始化 Git，不提交推送。

---

## 6 未完成项

无。本任务全部步骤已完成。
