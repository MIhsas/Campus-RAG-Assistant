# T005 语料预览与来源定位报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。submission_revision：5。响应 T005-R4。

---

## 0 R1—R2 修复摘要

### R1：JavaScript 语法错误

移除 `showDetailError` 函数后多余的 `}`（原 line 372），该花括号提前关闭了外层 IIFE，导致 `function renderDetail` 在 IIFE 外部无法解析。

Astra 提供的语法检查器 `node docs/collaboration/reviews/T005-R4-syntax.cjs` 输出 `JavaScript syntax OK`，退出码 0。

### R2：错误恢复（来自 T005-R3 要求）

| 问题 | 修复 |
|---|---|
| loadStatus 无请求序号保护 | 新增 `statusRequestSeq`，fetch/JSON/catch 后检查 `mySeq !== statusRequestSeq` |
| loadDocs 无请求序号保护 | 新增 `listRequestSeq`，fetch/JSON/catch 后检查 `mySeq !== listRequestSeq` |
| loadStatus 开始即清除旧错误 | 改为仅在成功响应确定后调用 `removeStatusErrors()`，错误/过期响应不操作 |
| loadDocs 成功调用 `clearOldErrors` 删除状态错误 | 移除全局 `clearOldErrors()`；状态错误由 loadStatus 独立管理（`.status-errors-box` 类名） |
| loadDocs 重试按钮调用 loadStatus | 改为仅调用 `loadDocs()`，列表重试不干预状态 |

**错误管理分离**：
- 状态错误：`removeStatusErrors()` 仅由 loadStatus 成功路径调用，使用 `.status-errors-box` 类名
- 列表错误：`showListError()` 仅由 loadDocs 各分支调用
- 详情错误：`showDetailError()` 仅由 selectDoc 各分支调用

---

## 1 验证

| 检查 | 结果 |
|---|---|
| `node T005-R4-syntax.cjs` | `JavaScript syntax OK`，exit 0 |
| 全量 pytest | 151 passed, 1 skipped |
| pip check | pass |
| statusRequestSeq 存在 | ✓ |
| listRequestSeq 存在 | ✓ |
| loadStatus 成功后调用 removeStatusErrors | ✓ |
| loadDocs 成功不调用 clearOldErrors | ✓ |

## 2 浏览器交互验证

**未验证**。Claude Code 无浏览器能力。以下项交由 Astra 复核：
- 快速文档切换（R1 回归）
- 状态/列表/详情分别 HTTP 500 → 重试成功 → 旧错误消失
- 列表 500 + 输入筛选 → 错误/重试仍可见 → 重试成功 → 匹配文档显示
- 旧失败晚到不覆盖新成功
- partial 状态错误明细保留
