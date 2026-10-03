# T005 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。submission_revision=4，响应 T005-R3。

---

## V01 全量 pytest

- **命令**：`.venv/Scripts/python.exe -m pytest -q`
- **退出码**：0
- **输出**：`151 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 源码模式验证（服务端 HTML）

启动 demo 服务 port 8009，curl /preview 检查关键模式：

| 模式 | 存在 |
|---|---|
| `listState` 变量 | ✓ |
| `showStatusError` 函数 | ✓ |
| `showDetailError` 函数 | ✓ |
| `renderListWithFilter` 函数 | ✓ |
| `listState !== 'ready'` guard in filterDocs | ✓ |
| `selectDoc(docId, blockId)` in detail retry | ✓ |
| `clearOldErrors()` in loadDocs success | ✓ |

## V04 错误恢复结构验证

- loadStatus 的 `!r.ok` 路径调用 `showStatusError`（含重试按钮） ✓
- loadStatus JSON catch 调用 `showStatusError`（区分"无效 JSON"） ✓
- loadStatus 网络 catch 调用 `showStatusError`（"网络错误"） ✓
- selectDoc 的 `!r.ok` 路径调用 `showDetailError` ✓
- selectDoc JSON catch 调用 `showDetailError` ✓
- selectDoc 网络 catch 调用 `showDetailError` ✓
- filterDocs 在 `listState !== 'ready'` 时直接返回 ✓
- loadDocs 成功路径设置 `listState = 'ready'` 并调用 `clearOldErrors()` + `renderListWithFilter()` ✓

## V05 R1 快速切换回归

- `detailRequestSeq` 计数器仍在 ✓
- `mySeq !== detailRequestSeq` 双重检查仍在 ✓

## V06 浏览器交互验证

**未验证**。交由 Astra 复核：
- 列表 500 + 输入筛选 + 重试成功 + 筛选生效
- 状态/详情分别 500 + 重试 + 错误消失
- 旧失败晚到不覆盖新成功
