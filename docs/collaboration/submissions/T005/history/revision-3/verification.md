# T005 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=3，响应 T005-R2。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`151 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 wheel 资源检查

- wheel 含 `campus_assistant/static/preview.html` ✓

## V04 API 冒烟（demo 服务 port 8007）

| 端点 | HTTP | 结果 |
|---|---|---|
| /api/v1/corpus/status | 200 | status=ready, docs=2/2 |
| /preview | 200 | 20728 bytes |

## V05 源码验证：R1 请求序号

- preview.html 含 `detailRequestSeq` 声明 ✓
- preview.html 含 `mySeq !== detailRequestSeq` 两次检查 ✓
- selectDoc 使用 `capturedDocId`/`capturedBlockId` 局部变量 ✓

## V06 源码验证：R2 HTTP 错误处理

- loadStatus 检查 `!r.ok` ✓
- loadDocs 区分 503 / `!r.ok` / JSON 解析失败 / 网络错误 ✓
- selectDoc 检查 `!r.ok` 非 404/503 ✓
- `clearOldErrors()` 在 loadStatus 开始时调用 ✓
- 重试按钮调用 `loadDocs()` + `loadStatus()` ✓

## V07 浏览器交互验证

**未验证**。Claude Code 无浏览器能力。交由 Astra 复核：
- 快速连续选择：最终详情与选中项一致
- HTTP 500 场景：错误提示 + 重试按钮
- 错误恢复后旧错误明细消失
