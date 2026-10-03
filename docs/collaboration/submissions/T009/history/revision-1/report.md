# T009 检索评测基线与问题集契约

## 实施概述

基于已有 parse_manifest → chunk_documents → BM25Index 管线，新增离线评测模块，实现问题集校验、区间覆盖指标计算和 CLI 评测入口。

## 新增文件

| 文件 | 职责 |
|---|---|
| `evaluation/__init__.py` | 包入口 |
| `evaluation/models.py` | 问题集 Pydantic 模型，严格校验（未知字段拒绝、StrictBool/StrictInt、ID 正则 `\Z`） |
| `evaluation/metrics.py` | Evidence Recall@K、Hit@K、MRR@K 纯函数，区间覆盖判定 |
| `evaluation/run.py` | CLI 入口，一次建索引，来源校验，UTF-8 JSON 输出 |
| `tests/test_evaluation.py` | 手算指标测试、区间边界、数据集校验 |
| `tests/test_evaluation_cli.py` | subprocess 回归：成功/坏数据集/语料错误/参数/初始化计数 |
| `examples/evaluation/questions.json` | 8 道合成开发题（6 可答 + 2 不可答） |
| `examples/evaluation/README.md` | 题集说明与标注方法 |
| `scripts/check-search-behavior.cjs` | 7 场景异步行为回归 |

## T003 遗留：证据标注校验

- 标注前先核验 document_id 存在于语料、document_sha256 匹配、block_id 可达
- 任一失效则整次评测失败，不跳过坏题
- is_synthetic=false 时拒绝含合成文档的语料

## T008 遗留：异步行为回归

基于 T008-R4-ui.cjs 模式，纳入项目可执行脚本 `scripts/check-search-behavior.cjs`，7 场景通过：
1. 空白后旧成功不覆盖提示
2. 空白后旧失败不覆盖提示
3. A→B 旧成功不覆盖 B
4. A→B 旧失败不覆盖 B
5. HTTP 失败后重试用原参数
6. JSON 失败后重试用原参数
7. 网络失败后重试用原参数

## 合成开发集评测结果

```
evidence_recall: 1.0
hit: 1.0
mrr: 0.917
answerable_count: 6
unanswerable_count: 2
empty_result_rate: 0.0
```

每题详情：
- q01（缓考流程）：recall=1.0, hit=1.0, mrr=0.5
- q02（补考分数）：recall=1.0, hit=1.0, mrr=1.0
- q03（取消资格）：recall=1.0, hit=1.0, mrr=1.0
- q04（转专业条件）：recall=1.0, hit=1.0, mrr=1.0
- q05（缓考材料，2 证据）：recall=1.0, hit=1.0, mrr=1.0
- q06（张三成绩）：recall=1.0, hit=1.0, mrr=1.0
- q07（奖学金）：answerable=false
- q08（宿舍管理）：answerable=false

## 验证记录

| 项目 | 结果 |
|---|---|
| 全量 pytest | 349 passed, 1 skipped |
| pip check | No broken requirements found |
| JS 语法检查 | preview.html/search.html OK |
| 异步行为回归 | 7 scenarios passed |
| 示例评测 CLI | valid=true, 8 题, 6 可答 |
| wheel 构建 | 成功，evaluation 包含在 wheel 中 |
| 初始化计数 | parse/chunk/index 各 1 次 |
| 确定性 | 同输入两次结果完全一致 |

## 限制

- 合成开发集验证评测流程，不代表论文准确率
- 金标准为人工标注字符区间，不绑定 chunk_id
- 不支持等价替代证据组或测试集冻结
- 真实语料题集在用户提供资料后另行标注
