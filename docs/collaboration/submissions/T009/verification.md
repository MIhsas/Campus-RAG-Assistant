# T009 验证记录（revision 2）

## 环境

- 工作目录：step2_code/backend
- Python：.venv (3.12)
- 日期：2026-09-21

## 1. 全量 pytest

```
$ .venv/Scripts/python.exe -m pytest -q --tb=short -rs
368 passed, 1 skipped, 2 warnings in 27.02s
```

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
```

## 4. 异步行为回归

```
$ node scripts/check-search-behavior.cjs
check-search-behavior: 7 scenarios passed
```

## 5. 示例评测 CLI（修正后题集）

```
$ .venv/Scripts/python.exe -m campus_assistant.evaluation.run \
    --manifest examples/parse-corpus/manifest.json \
    --corpus-root examples/parse-corpus \
    --questions examples/evaluation/questions.json --top-k 5

valid: true, exit: 0
summary: evidence_recall=1.0, hit=1.0, mrr=0.917
question_count=8, answerable_count=6, unanswerable_count=2
per_question: q01 mrr=0.5, q02-q06 mrr=1.0, q07-q08 answerable=false
```

## 6. wheel 构建与非源码验证

```
$ .venv/Scripts/python.exe -m pip wheel . --no-deps --no-build-isolation \
    --no-index --wheel-dir .cache/t009r2-wheel --cache-dir .cache/pip
SHA-256: cd8a2639fa8c3aea514d5dc08e6969d9f7939bc1d395a04d39de71721b38a26d
```

从解压后的 wheel 目录导入并运行 `_run_eval`：valid=true, recall=1.0，import from 为临时目录。

## 7. 初始化计数（2 题）

测试 `test_multi_question_init` 验证 parse_manifest、chunk_documents、BM25Index.__init__ 在 2 题评测中各调用 1 次。

## 8. 坏标注不触发检索

测试 `test_bad_evidence_no_search` 验证 bad block_id 时 BM25Index.search 调用次数为 0。

## 9. R1 负例（CLI subprocess）

| 变异 | 退出码 | errors.code | errors.field |
|---|---|---|---|
| block_id="nonexistent" | 1 | EVIDENCE_REFERENCE_ERROR | block_id |
| parser_version="999" | 1 | EVIDENCE_REFERENCE_ERROR | parser_version |
| char_end=9999 | 1 | EVIDENCE_REFERENCE_ERROR | char_start/char_end |
| quote="完全不同的文本" | 1 | EVIDENCE_REFERENCE_ERROR | quote |

## 10. R3 模型约束

| 测试 | 结果 |
|---|---|
| is_synthetic="true" | rejected |
| is_synthetic="false" | rejected |
| is_synthetic=1 | rejected |
| is_synthetic=True | accepted |
| split="test" | rejected |
| split="dev" | accepted |
| 重复 evidence_id | rejected |
| 重复来源区间 | rejected |
| 同块不同区间 | accepted |

## 11. R4 非对象 JSON

| 输入 | 退出码 | errors.code |
|---|---|---|
| `[]` | 1 | DATASET_SCHEMA_ERROR |
| `null` | 1 | DATASET_SCHEMA_ERROR |
| `42` | 1 | DATASET_SCHEMA_ERROR |
| `"hello"` | 1 | DATASET_SCHEMA_ERROR |

## 12. 确定性

测试 `test_same_input_same_output` 验证同输入两次运行结果完全一致。

## 13. 未验证项

- 浏览器视觉验收（无浏览器工具）
- 真实学校语料评测（用户未提供）
