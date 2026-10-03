# T010 验证记录

## 关键验证命令与结果

### 1. 全量测试
```
.venv/Scripts/python.exe -m pytest -q --tb=short
# 374 passed, 1 skipped, 2 warnings in 29.95s
```

### 2. pip check
```
.venv/Scripts/python.exe -m pip check
# No broken requirements found.
```

### 3. 语法检查
```
node scripts/check-js-syntax.cjs
# preview.html: syntax OK
# search.html: syntax OK
```

### 4. BM25 评测
```
.venv/Scripts/python.exe -m campus_assistant.evaluation.run --manifest examples/parse-corpus/manifest.json --corpus-root examples/parse-corpus --questions examples/evaluation/questions.json --top-k 5 --mode bm25
# evidence_recall=1.0, hit=1.0, mrr=0.917
```

### 5. Dense 评测
```
.venv/Scripts/python.exe -c "from campus_assistant.evaluation.run import _run_eval; ..."
# evidence_recall=1.0, hit=1.0, mrr=0.917
```

### 6. Hybrid 评测
```
.venv/Scripts/python.exe -c "from campus_assistant.evaluation.run import _run_eval; ..."
# evidence_recall=1.0, hit=1.0, mrr=0.917
```

### 7. API 三模式测试
- BM25: POST /api/v1/search `{"query":"缓考","mode":"bm25"}` → 200, mode=bm25
- Dense unavailable: `{"mode":"dense"}` → 503/RETRIEVER_UNAVAILABLE
- Invalid mode: `{"mode":"invalid"}` → 422

### 8. JS 语法检查
```
node scripts/check-js-syntax.cjs
# preview.html: syntax OK
# search.html: syntax OK
```

### 9. 搜索页模式切换
- 页面包含"关键词"、"语义"、"混合"三个模式按钮
- 默认选中"关键词"
- 未启用模型时"语义"和"混合"按钮禁用

## 浏览器验证

无浏览器工具，标记由 Astra 补验。

## 未验证项

- 浏览器模式切换→搜索→查看原文完整流程
- CPU 查询实际延迟
