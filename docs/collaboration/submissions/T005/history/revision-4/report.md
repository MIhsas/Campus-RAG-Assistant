# T005 语料预览与来源定位报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。submission_revision：4。响应 T005-R3。

---

## 0 R2 错误恢复修复摘要

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 状态 HTTP 500 | 文字提示，无重试 | `showStatusError` 含重试按钮，调用 loadStatus |
| 状态 JSON 解析失败 | catch 泛化"网络错误" | 显式 `try { d = await r.json() } catch` → "无效 JSON" + 重试 |
| 状态网络错误 | "网络错误" 无重试 | "网络错误" + 重试按钮 |
| 详情 HTTP 500 | 文字提示，无重试 | `showDetailError` 含重试按钮，调用 selectDoc(capturedDocId, capturedBlockId) |
| 详情 JSON 解析失败 | catch 泛化"加载失败" | 显式 JSON catch → "无效 JSON" + 重试 |
| 详情网络错误 | "加载失败" 无重试 | "网络错误" + 重试按钮 |
| 筛选覆盖错误 | 输入文字 → renderList(allDocs) → "无匹配文档" 覆盖错误 | filterDocs 检查 `listState !== 'ready'` 则不操作 |
| 成功后旧错误残留 | clearOldErrors 仅在 loadStatus 开始调用 | loadDocs 成功也调用 clearOldErrors |
| 成功后筛选丢失 | loadDocs 成功调用 renderList(allDocs) 忽略筛选 | renderListWithFilter 应用当前筛选条件 |

---

## 1 状态管理

新增 `listState` 变量（'idle' | 'loading' | 'error' | 'unconfigured' | 'ready'），loadDocs 在各分支设置：

| loadDocs 分支 | listState | 后续 filterDocs |
|---|---|---|
| 503 | 'unconfigured' | 不操作 |
| HTTP 非 ok | 'error' | 不操作 |
| JSON 解析失败 | 'error' | 不操作 |
| 网络错误 | 'error' | 不操作 |
| 成功 | 'ready' | 应用当前筛选 |

## 2 重试机制

- **状态重试**：`showStatusError` 在状态栏内添加重试按钮，点击调用 `loadStatus()`
- **列表重试**：`showListError` 的重试按钮调用 `loadDocs() + loadStatus()`
- **详情重试**：`showDetailError` 添加重试按钮，点击调用 `selectDoc(capturedDocId, capturedBlockId)` 保留定位

## 3 错误区分

| 错误类型 | 提示文案 |
|---|---|
| HTTP 500+ | "接口错误：HTTP N" |
| JSON 解析失败 | "接口返回无效 JSON" |
| 网络中断 | "网络错误" |
| 预期 503 | "语料未配置"（无重试） |
| 预期 404 | "文档不存在"（无重试） |

## 4 验证

| 检查 | 结果 |
|---|---|
| listState 变量存在 | ✓ |
| showStatusError 含重试 | ✓ |
| showDetailError 含重试 | ✓ |
| renderListWithFilter 存在 | ✓ |
| filterDocs 检查 listState | ✓ |
| clearOldErrors 在成功路径调用 | ✓ |
| 全量 pytest | 151 passed, 1 skipped |
| pip check | pass |

## 5 浏览器交互验证

**未验证**。Claude Code 无浏览器能力。以下项交由 Astra 复核：
- 列表首次 500 → 输入筛选 → 错误/重试仍可见 → 重试成功 → 匹配文档显示
- 状态/详情 500 → 重试成功 → 旧错误消失
- 连续重试及旧失败晚到不覆盖新成功
