# T008 验证记录

执行时间：2026-09-14。submission_revision=3，响应 T008-R2。

---

## V01 全量 pytest

- **退出码**：0
- **输出**：`283 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 JS 语法检查

- **退出码**：0
- **输出**：`preview.html: syntax OK`, `search.html: syntax OK`

## V04 R1 请求生命周期（源码确认）

- doSearch 入口先 `searchSeq++` 再判断空白 ✓
- 空白提交后旧请求的 `mySeq !== searchSeq` ✓
- `btn.disabled = false` 由 `mySeq === searchSeq` 守卫 ✓
- retrySearchParams 同样守卫 ✓

## V05 R2 真实计数测试

- monkeypatch parse_manifest/chunk_documents/BM25Index.__init__ ✓
- 创建后 counts = {parse: 1, chunk: 1, index: 1} ✓
- 4 次 HTTP 请求后 counts 不变 ✓

## V06 浏览器交互

**未验证**。
