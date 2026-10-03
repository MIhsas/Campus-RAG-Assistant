# T005 语料预览与来源定位报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。

---

## 1 完成内容

### 1.1 应用工厂扩展

`create_app(manifest_path=None, corpus_root=None)`：两者必须同时提供或同时省略，否则 ValueError。提供时调用 `validate_manifest` + `parse_manifest` 一次，结果快照存入 `app.state`。支持四种状态：unconfigured / ready / partial / failed。

### 1.2 API 端点

| 端点 | 状态码 | 说明 |
|---|---|---|
| GET /api/v1/corpus/status | 始终 200 | status、document_count、parsed_count、errors、request_id |
| GET /api/v1/corpus/documents | 503（未配置）/ 200 | items 数组，每项含 document_id、title、format、block_count、warnings |
| GET /api/v1/corpus/documents/{id} | 503 / 404 / 200 | document 含 metadata、parser_version、blocks、warnings |

所有端点携带 request_id（与 X-Request-ID 一致）。错误响应使用中文消息，不暴露绝对路径。

### 1.3 演示入口

`campus_assistant.demo:app` 加载 `examples/parse-corpus`，独立 uvicorn 启动命令。

### 1.4 预览页面

`/preview` 返回静态 HTML（从 `campus_assistant/static/preview.html` 读取，不依赖 cwd）。

功能：文档列表 + 标题筛选、详情展示来源/版本/日期/范围、正文块顺序展示、locator 位置、表格 cells、warnings 可见、URL hash 定位（document_id/block_id）、复制定位链接、未配置/加载失败状态、textContent 安全渲染。

### 1.5 测试

22 项预览测试：unconfigured 状态/503、ready 状态、文档列表/详情、未知 ID 404、request_id 追踪、多 app 隔离、快照只解析一次、工厂参数校验、预览页访问、OpenAPI 声明、健康回归、demo 模块 CLI。

---

## 2 文件清单

见 `changed-files.json`（31 个文件）。新增：`api/corpus.py`、`demo.py`、`static/preview.html`、`tests/test_corpus_preview.py`。修改：`main.py`、`README.md`。

---

## 3 已知限制

1. 预览页为开发工具，不替代 Vue 管理端。
2. 通过重启加载新语料，不做热更新。
3. `/api/v1/health/ready` 继续返回 503（知识问答未就绪）。
4. 浏览器交互验证依赖 Astra 复核（Claude Code 无浏览器能力）。
5. 合成测试资料不代表学校政策。
