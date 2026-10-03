# T005 语料预览与来源定位报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。submission_revision：3。响应 T005-R2。

---

## 0 R1—R2 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | 旧响应覆盖当前文档 | `detailRequestSeq` 计数器：每次 selectDoc 递增并捕获序号，fetch 返回后检查 `mySeq !== detailRequestSeq`，过期响应丢弃；JSON 解析后二次检查 |
| R2 | HTTP 错误伪装为空列表 | loadStatus 检查 `r.ok`；loadDocs 区分 503/非 ok/JSON 解析失败/网络错误，各有明确提示和重试按钮；selectDoc 检查非 ok 非 404/503；错误明细替换而非累加 |

---

## 1 R1：请求序号机制

```javascript
var detailRequestSeq = 0;

async function selectDoc(docId, blockId) {
  detailRequestSeq++;
  var mySeq = detailRequestSeq;
  // ... fetch ...
  if(mySeq !== detailRequestSeq) return; // stale, discard
  // ... JSON parse ...
  if(mySeq !== detailRequestSeq) return; // check again
  renderDetail(d.document);
}
```

- 每次 selectDoc 递增全局序号并捕获当前值
- fetch 返回后立即检查序号是否仍匹配
- JSON 解析后二次检查（解析期间可能有新选择）
- 使用 capturedDocId/capturedBlockId 而非可能已被改写的全局变量

## 2 R2：HTTP 错误处理

| 场景 | loadStatus | loadDocs | selectDoc |
|---|---|---|---|
| 200 | 正常解析 | 正常解析 | 正常渲染 |
| 503 | 显示"接口错误" | "语料未配置" | "语料未配置" |
| 500+ | "接口错误：HTTP N" | "列表接口错误：HTTP N" + 重试 | "详情接口错误：HTTP N" |
| JSON 解析失败 | catch | "列表接口返回无效 JSON" + 重试 | catch |
| 网络中断 | "网络错误" | "网络错误" + 重试 | "加载失败" |

- `clearOldErrors()` 在 loadStatus 开始时移除已有 `.errors-box`
- 重试按钮调用 `loadDocs()` + `loadStatus()` 恢复完整状态

## 3 验证

| 检查 | 结果 |
|---|---|
| preview.html 含 `detailRequestSeq` | ✓（API 冒烟确认） |
| preview.html 含 `mySeq !== detailRequestSeq` | ✓（API 冒烟确认） |
| preview.html 含 `!r.ok` 检查 | ✓ |
| preview.html 含 `clearOldErrors` | ✓ |
| 全量 pytest | 151 passed, 1 skipped |
| pip check | pass |
| wheel 含 preview.html | ✓ |
| API 冒烟（status/preview） | ✓ |

## 4 浏览器交互验证

**未验证**。Claude Code 无浏览器能力。以下项交由 Astra 复核：
- 快速先选 TXT 再选 DOCX：最终详情应为 DOCX
- HTTP 500 场景：显示错误提示和重试按钮
- 错误恢复后错误明细消失
