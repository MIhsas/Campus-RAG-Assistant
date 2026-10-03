# T009 检索评测基线与问题集契约（revision 2）

## 修订说明

响应 T009-R1，修正四项阻塞问题。revision 1 已保存至 history/revision-1。

## R1 修正：来源标注完整校验

在 `evaluation/run.py` 的 `_run_eval` 中扩展证据校验，覆盖：

1. **document_id** 存在于语料
2. **document_sha256** 匹配
3. **parser_version** 与实际解析器版本一致
4. **block_id** 存在于该文档的已解析块中
5. **char_start/char_end** 满足 `0 ≤ start < end ≤ len(block.text)`
6. **quote** 与 `block.text[char_start:char_end]` 逐字符一致

任一失效则整批失败：valid=false、summary=null、per_question=[]、exit 1。新增4项负例 CLI 测试（bad block_id、bad parser_version、char_end 超长、quote 不匹配），均验证坏题集不触发 BM25Index.search。

## R2 修正：金标准标注

修正 questions.json 中三处错误：

| 题号/证据 | 修正前 | 修正后 |
|---|---|---|
| q01/e01 | [33,63) | [38,63)，对应"缓考申请须经所在学院批准..." |
| q02/e02 | [24,35) | [33,44)，对应"补考成绩最高记为60分" |
| q05 | 查询"需要什么材料"，TXT 证据是审批流程 | 改为"缓考申请的审批流程和证明材料"，e05b 修正为 [14,19)="需医院证明" |

逐条核验全部 7 个证据单元，dataset_version 升至 1.2。

## R3 修正：题集结构约束

在 `evaluation/models.py` 的 Question 模型中新增：

- **题内 evidence_id 唯一**：重复 → ValueError
- **题内来源区间唯一**（document_id + block_id + char_start + char_end）：重复 → ValueError，同块不同区间允许
- **is_synthetic**：改为 StrictBool，拒绝 "true"/"false"/1/0
- **split**：固定为 "dev"，拒绝 "test"/其他值

新增13项测试覆盖所有约束。

## R4 修正：非对象 JSON 安全处理

在 `evaluation/run.py` 中，JSON 解析后、Pydantic 校验前增加 `isinstance(data_q, dict)` 检查。顶层为数组/null/数字/字符串时直接返回 DATASET_SCHEMA_ERROR，不再触发 AttributeError。

新增4项 subprocess 测试（array、null、number、string）验证退出 1、valid=false、DATASET_SCHEMA_ERROR。

## 合成开发集评测结果（修正后）

```
valid: true
evidence_recall: 1.0
hit: 1.0
mrr: 0.917
answerable_count: 6
unanswerable_count: 2
empty_result_rate: 0.0
```

## 验证记录

| 项目 | 结果 |
|---|---|
| 全量 pytest | 368 passed, 1 skipped |
| pip check | No broken requirements found |
| JS 语法 | preview.html/search.html OK |
| 异步行为回归 | 7 scenarios passed |
| 示例评测 CLI | valid=true, exit=0, 8 题, 6 可答 |
| wheel 构建 | 成功，evaluation 包含在 wheel 中 |
| wheel 非源码导入 | import from: ...\tmpXXX\campus_assistant\ |
| 初始化计数（2 题） | parse/chunk/index 各 1 次 |
| 坏标注不触发检索 | search_called=0 ✓ |
| 确定性 | 同输入两次结果完全一致 |
