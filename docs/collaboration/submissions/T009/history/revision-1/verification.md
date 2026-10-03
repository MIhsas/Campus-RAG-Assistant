# T009 验证记录

## 环境

- 工作目录：step2_code/backend
- Python：.venv (3.12)
- 日期：2026-09-21

## 1. 全量 pytest

```
$ .venv/Scripts/python.exe -m pytest -q --tb=short -rs
349 passed, 1 skipped, 2 warnings in 22.19s
```

跳过：符号链接权限 winerror=1314（既有）。

## 2. pip check

```
$ .venv/Scripts/python.exe -m pip check
No broken requirements found.
```

## 3. JS 语法检查

```
$ node scripts/check-js-syntax.cjs
preview.html: syntax OK
search.html: syntax OK
All 2 HTML files passed syntax check.
```

## 4. 异步行为回归

```
$ node scripts/check-search-behavior.cjs
check-search-behavior: 7 scenarios passed
```

## 5. 示例评测 CLI

```
$ .venv/Scripts/python.exe -m campus_assistant.evaluation.run \
    --manifest examples/parse-corpus/manifest.json \
    --corpus-root examples/parse-corpus \
    --questions examples/evaluation/questions.json \
    --top-k 5

valid: true
summary: evidence_recall=1.0, hit=1.0, mrr=0.917
question_count: 8, answerable_count: 6, unanswerable_count: 2
per_question: q01-q06 recall=1.0, q07-q08 answerable=false
```

## 6. wheel 构建

```
$ .venv/Scripts/python.exe -m pip wheel . --no-deps --no-build-isolation \
    --no-index --wheel-dir .cache/t009-wheel --cache-dir .cache/pip
Successfully built campus-assistant-backend
SHA-256: 2eb6e158f1c0248e0c8ea217653f50afe10ac0f02afd27c132a460ef4bd0e5a7
```

wheel 中包含 evaluation 包（__init__.py, models.py, metrics.py, run.py）。

## 7. 初始化计数

测试 `test_single_init` 验证 parse_manifest、chunk_documents、BM25Index.__init__ 在一次评测中各调用 1 次。

## 8. 确定性

测试 `test_same_input_same_output` 验证同输入两次运行结果完全一致。

## 9. 未验证项

- 浏览器视觉验收（无浏览器工具）
- 真实学校语料评测（用户未提供）
