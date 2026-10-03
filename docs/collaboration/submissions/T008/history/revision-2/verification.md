# T008 验证记录

执行时间：2026-09-14。submission_revision=2，响应 T008-R1。

---

## V01 全量 pytest

- **退出码**：0
- **输出**：`283 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 JS 语法检查

- **退出码**：0
- **输出**：`preview.html: syntax OK`, `search.html: syntax OK`

## V04 R1 严格输入验证

| 输入 | 期望 | 实际 |
|---|---|---|
| top_k=true | 422 | 422 ✓ |
| top_k=1.0 | 422 | 422 ✓ |
| top_k="5" | 422 | 422 ✓ |
| query="   " | 422 | 422 ✓ |
| query=" 缓考 " | 200, query=" 缓考 " | ✓ |

## V05 R2 构建异常降级

- patch chunk_documents 抛 RuntimeError → app 返回（不抛出） ✓
- search/status=failed ✓
- POST search → 503/SEARCH_UNAVAILABLE ✓
- preview/corpus 仍可读 ✓
- health/live=200, health/ready=503 ✓
- message 不含异常路径 ✓
- synthetic_count=1（在分块前计算） ✓

## V06 R3 页面重试（源码确认）

- lastSubmittedQuery/lastSubmittedTopK 独立于 input.value ✓
- retrySearchParams 使用捕获参数 ✓
- statusSeq 独立 ✓
- 503/HTTP/JSON/catch 各有重试按钮 ✓

## V07 R4 来源展示（源码确认）

- 全合成/部分合成动态提示 ✓
- 三组日期展示 + formatDate ✓
- "无有效词元" / "无有效索引" / "无匹配" 区分 ✓

## V08 浏览器交互

**未验证**。
