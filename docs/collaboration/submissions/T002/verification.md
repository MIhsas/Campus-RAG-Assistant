# T002 验证记录

执行时间：2026-09-12。工作目录：`F:\Collage Paper\step2_code\backend`。

---

## V01 路径确认

- **命令**：`ls -la step2_code/`
- **退出码**：0
- **输出**：空目录（仅 `.` 和 `..`）
- **说明**：确认 backend 不存在，T001 已通过（STATUS.md 记录）。

---

## V02 虚拟环境创建与隔离

- **命令**：`D:/Anaconda/python.exe -m venv .venv`
- **退出码**：0

- **命令**：`.venv/Scripts/python.exe -c "import sys; print(sys.prefix); print(sys.base_prefix); print(sys.prefix != sys.base_prefix)"`
- **输出**：
  ```
  F:\Collage Paper\step2_code\backend\.venv
  D:\Anaconda
  True
  ```
- **说明**：venv 隔离成功，prefix ≠ base_prefix。

---

## V03 依赖安装

- **命令**：`.venv/Scripts/python.exe -m pip install --cache-dir .cache/pip fastapi "uvicorn>=0.32,<1" "pytest>=8,<9" "httpx>=0.27,<1" "setuptools>=68.0" wheel`
- **退出码**：0
- **输出摘要**：Successfully installed fastapi-0.141.1 uvicorn-0.52.4 pytest-8.4.2 httpx-0.28.1 setuptools-84.0.0 wheel-0.48.0 及传递依赖
- **说明**：仅安装任务书必要包，未选 fastapi[standard] 或 uvicorn[standard]。缓存放 backend/.cache/pip。

---

## V04 可编辑安装

- **命令**：`.venv/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e .`
- **退出码**：0
- **输出**：Successfully installed campus-assistant-backend-0.1.0

---

## V05 pytest 测试

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：
  ```
  ................                                                         [100%]
  16 passed, 2 warnings in 0.48s
  ```
- **说明**：16 项测试覆盖全部七项验证行为。2 个弃用警告来自 Starlette TestClient，不影响功能。

---

## V06 pip check

- **命令**：`.venv/Scripts/python.exe -m pip check`
- **退出码**：0
- **输出**：`No broken requirements found.`

---

## V07 锁文件生成

- **命令**：`.venv/Scripts/python.exe -m pip freeze --local`
- **退出码**：0
- **输出**：24 个包的精确版本（去除 editable 行后写入 requirements.lock.txt）
- **说明**：锁文件标注 Python 3.12 / Windows，不声称跨平台通用。

---

## V08 HTTP 冒烟测试

### V08a live 端点

- **命令**：`curl -s -D - http://127.0.0.1:8000/api/v1/health/live`
- **HTTP 状态**：200 OK
- **响应头**：`X-Request-ID: ffe5b552-8f98-47dd-be97-ef0784f3f88a`
- **响应体**：`{"status":"ok","service":"campus-assistant-backend","version":"0.1.0","request_id":"ffe5b552-8f98-47dd-be97-ef0784f3f88a"}`
- **验证**：status=ok, service/version 正确, request_id 与 X-Request-ID 一致。

### V08b ready 端点

- **命令**：`curl -s -D - http://127.0.0.1:8000/api/v1/health/ready`
- **HTTP 状态**：503 Service Unavailable
- **响应头**：`X-Request-ID: 934f7763-8bf5-4a8f-85ef-9f1f7740a311`
- **响应体**：`{"status":"not_ready","code":"KNOWLEDGE_BASE_NOT_CONFIGURED","message":"知识库尚未配置","retryable":false,"request_id":"934f7763-8bf5-4a8f-85ef-9f1f7740a311"}`
- **验证**：503 正确，业务码、中文提示、retryable=false 均正确。

### V08c 未知路径

- **命令**：`curl -s -D - http://127.0.0.1:8000/api/v1/nonexistent`
- **HTTP 状态**：404 Not Found
- **响应头**：`X-Request-ID: 7c185e99-c86c-4c77-8159-e38e89a288a5`
- **验证**：404 返回且有 X-Request-ID 追踪头。

### V08d 客户端 ID 不回显

- **命令**：`curl -s -D - -H "X-Request-ID: 00000000-0000-0000-0000-aaaaaaaaaaaa" http://127.0.0.1:8000/api/v1/health/live`
- **HTTP 状态**：200 OK
- **响应头 X-Request-ID**：`e44fcbeb-9494-4125-90c6-94936a5a08d1`（≠ 客户端传入值）
- **验证**：客户端值未被回显。

---

## V09 OpenAPI 检查

- **命令**：通过 pytest `TestOpenApiSchema` 类验证（见 test_health.py）
- **结果**：pass
- **验证**：`/api/v1/health/live` 和 `/api/v1/health/ready` 均在 schema 中；ready 的 get 操作包含 "503" 响应声明。

---

## V10 create_app() 多实例化

- **命令**：通过 pytest `TestAppFactory` 类验证（见 test_health.py）
- **结果**：pass
- **验证**：`create_app()` 返回不同实例，均可独立处理请求，无外部网络/数据库/API key 依赖。

---

## V11 复现验证

- **命令**：
  ```
  D:/Anaconda/python.exe -m venv .venv-verify
  .venv-verify/Scripts/python.exe -m pip install -r requirements.lock.txt
  .venv-verify/Scripts/python.exe -m pip install --no-deps --no-build-isolation -e .
  .venv-verify/Scripts/python.exe -m pytest -q
  ```
- **pip install lock**：退出码 0，24 个包全部安装成功
- **editable install**：退出码 0
- **pytest**：退出码 0，16 passed, 2 warnings
- **说明**：独立环境从锁文件复现成功。

---

## V12 changed-files.json 校验

- **方法**：Python 标准库生成，逐项计算 SHA-256 和字节数。
- **文件数**：11
- **说明**：不包含 .venv、.cache、__pycache__ 或 .egg-info。
