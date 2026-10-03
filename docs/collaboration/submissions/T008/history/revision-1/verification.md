# T008 验证记录

执行时间：2026-09-14。工作目录：`F:\Collage Paper\step2_code\backend`。

---

## V01 全量 pytest

- **退出码**：0
- **输出**：`277 passed, 1 skipped, 2 warnings`

## V02 pip check

- **退出码**：0

## V03 JS 语法检查

- **命令**：`node scripts/check-js-syntax.cjs`
- **退出码**：0
- **输出**：`preview.html: syntax OK`, `search.html: syntax OK`

## V04 wheel 包含新 HTML

- wheel 含 `campus_assistant/static/preview.html` 和 `campus_assistant/static/search.html`

## V05 API 冒烟（demo 服务 port 8011/8015）

| 端点 | HTTP | 结果 |
|---|---|---|
| /api/v1/search/status | 200 | status=ready, chunks=17, indexed=17, synthetic=2 |
| POST /api/v1/search {"query":"缓考申请"} | 200 | hits=3, top1 score=6.671 |
| /search | 200 | 12330 bytes |

## V06 T007 测试修正

- patch `chunk_manifest` 而非 `_run_search` → 计数=1 ✓
- 参数错误 exit 2 ✓

## V07 浏览器交互

**未验证**。
