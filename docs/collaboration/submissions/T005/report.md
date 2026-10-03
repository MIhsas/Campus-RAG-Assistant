# T005 语料预览与来源定位报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。submission_revision：6。响应 T005-R5。

---

## 0 R1 修复摘要

**问题**：列表首次 500 → handleHash 看到 `allDocs.length===0 && docsLoaded===true` → 显示"语料未配置或无文档"并丢弃待定位 ID → 用户重试列表成功后 processPending 无目标可恢复。

**根因**：handleHash 未区分"列表暂时失败"和"真正无文档/未配置"。

**修复**：handleHash 中 `allDocs.length===0` 分支增加 `listState` 判断：
- `listState === 'error' || 'loading'` → 存储 pendingDocId/pendingBlockId，等待重试恢复
- `listState === 'unconfigured'` → 显示"语料未配置"
- `listState === 'ready'`（真正空列表）→ 显示"暂无文档"

修复后流程：
1. `#doc/block` → 列表 500 → handleHash 存储 pending → 详情显示"加载中"
2. 用户点重试 → loadDocs 成功 → listState='ready' → renderListWithFilter → processPending → selectDoc(docId, blockId) → 渲染详情 + 高亮块

---

## 1 验证

| 检查 | 结果 |
|---|---|
| JS 语法检查 | `JavaScript syntax OK`，exit 0 |
| 全量 pytest | 151 passed, 1 skipped |
| pip check | pass |
| handleHash error/loading 分支存储 pending | ✓（源码确认） |
| handleHash unconfigured 显示"语料未配置" | ✓（源码确认） |
| handleHash ready 空列表显示"暂无文档" | ✓（源码确认） |

## 2 浏览器交互验证

**未验证**。交由 Astra 复核：
- `/preview#syn-parse-docx-001/e57ac232ebc1c1a5` + 列表首次 500 + 重试成功 → 详情恢复 + 块高亮
- 筛选不丢错误
- 未知 ID/块提示正确
- 原有快速切换、状态并发、partial 明细回归
