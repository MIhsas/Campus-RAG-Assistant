# T008 检索接口与证据搜索页报告

执行者：Mimo（Claude Code）。执行时间：2026-09-14。task_revision=v1，submission_revision=3。响应 T008-R2。

---

## 0 R1—R2 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | 空白提交未递增 searchSeq，旧请求可覆盖 | doSearch 入口先 `searchSeq++` 再判断空白；按钮 `disabled=false` 由 `mySeq === searchSeq` 守卫 |
| R2 | test_repeated_request_no_rebuild 仅比输出值 | 替换为 monkeypatch 计数 parse_manifest/chunk_documents/BM25Index.__init__，验证多次 HTTP 请求后计数不变 |

---

## 1 R1：请求生命周期修复

```javascript
// Before: blank returns without incrementing searchSeq
if(!query.trim()){ ... return; }
searchSeq++;

// After: always increment first
searchSeq++;
var mySeq = searchSeq;
if(!query.trim()){ ... return; }  // old requests now stale
```

按钮状态守卫：
```javascript
await executeSearch(query, topK, mySeq);
if(mySeq === searchSeq) btn.disabled = false;
```

旧请求完成时 `mySeq !== searchSeq`，不会释放按钮或覆盖结果。

## 2 R2：真实计数测试

```python
def test_repeated_request_no_rebuild(self, tmp_path, monkeypatch):
    # monkeypatch parse_manifest, chunk_documents, BM25Index.__init__
    create_app(...)  # counts = {parse: 1, chunk: 1, index: 1}
    c.get("/api/v1/search/status")  # x2
    c.post("/api/v1/search", ...)  # x2
    assert counts == {"parse": 1, "chunk": 1, "index": 1}
```

验证多次 HTTP 请求不触发重建。

## 3 验证

| 检查 | 结果 |
|---|---|
| 全量 pytest | 283 passed, 1 skipped |
| pip check | pass |
| JS 语法（两页） | pass |
| R1: searchSeq 先递增（源码确认） | ✓ |
| R1: 按钮守卫 mySeq === searchSeq（源码确认） | ✓ |
| R2: 真实计数测试 | pass |
