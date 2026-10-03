# T005 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=2，响应 T005-R1。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`151 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 wheel 资源检查

- **命令**：`.venv/Scripts/python.exe -m pip wheel --no-deps --no-build-isolation --wheel-dir .cache/astra-t005r2-wheel .`
- **结果**：`campus_assistant/static/preview.html` 在 wheel 中 ✓

## V04 API 冒烟（demo 服务 port 8005）

| 端点 | 状态 | 结果 |
|---|---|---|
| /api/v1/corpus/status | 200 | status=ready, document_count=2 |
| /api/v1/corpus/documents | 200 | items=2 |
| /api/v1/corpus/documents/syn-parse-txt-001 | 200 | blocks=6 |
| /api/v1/corpus/documents/nope | 404 | DOCUMENT_NOT_FOUND |
| /preview | 200 | 18976 bytes |
| /openapi.json status model | 200 | has $ref ✓ |

## V05 单次 parse 调用验证

- monkeypatch 计数：`create_app` 调用 `parse_manifest` 恰好 1 次 ✓

## V06 OpenAPI 响应模型

- `/api/v1/corpus/status` 200 响应引用 Pydantic 模型（$ref） ✓
- `/api/v1/corpus/documents` 503 引用 ErrorResponse 模型 ✓

## V07 源码静态排查（R1-R4）

- preview.html 无 innerHTML 数据拼接（仅 `textContent = ''` 清空） ✓
- 无 inline onclick（全部 addEventListener） ✓
- URL 链接通过 `.href` 属性赋值 ✓
- selectDoc 接受 blockId 参数并传递 ✓
- handleHash 使用 processPending 而非无限轮询 ✓
- banner 按 is_synthetic 动态显示 ✓
- 空状态/错误状态有明确提示和重试按钮 ✓
- 列表项为 button 元素（可 Tab 聚焦） ✓

## V08 浏览器交互验证

**未验证**。Claude Code 无浏览器能力。以下项交由 Astra 复核：
- 文档详情渲染、切换文档
- 复制块链接 + 刷新回查定位
- 键盘 Tab/Enter 操作
- 合成/真实混合 banner
- 未配置/无匹配/错误状态
- 带 HTML 标签文本以纯文本显示
- 窄屏布局
