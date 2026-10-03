# T007 验证记录

执行时间：2026-09-13。工作目录：`F:\Collage Paper\step2_code\backend`。

---

## V01 分词测试

- **命令**：`.venv/Scripts/python.exe -m pytest tests/test_retrieval_tokenize.py -q`
- **退出码**：0
- **输出**：`12 passed`
- **覆盖**：bigrams、单字、分隔符分隔、ASCII lowercase、混合、空白/标点/emoji、类型校验

## V02 BM25 测试

- **命令**：`.venv/Scripts/python.exe -m pytest tests/test_retrieval_bm25.py -q`
- **退出码**：0
- **输出**：`25 passed`
- **覆盖**：算术金例（ln(1.2)≈0.1823）、同分 ID 排序、词频饱和、长度归一化、未知词、空索引、top_k、去重查询、贡献加和、重复 ID、参数校验、深拷贝隔离、matched_terms、preview_url 编码

## V03 CLI 测试

- **命令**：`.venv/Scripts/python.exe -m pytest tests/test_retrieval_cli.py -q`
- **退出码**：0
- **输出**：`8 passed`
- **覆盖**：成功命中、输出字段、无命中、部分失败保留命中、top_k=0/-1/abc exit 2、UTF-8 无环境变量

## V04 全量 pytest

- **退出码**：0
- **输出**：`250 passed, 1 skipped, 2 warnings`

## V05 pip check

- **退出码**：0

## V06 JS 语法检查

- **退出码**：0
- **输出**：`JavaScript syntax OK`

## V07 示例 CLI 有命中

- **命令**：`.venv/Scripts/python.exe -m campus_assistant.retrieval.search --manifest ./examples/parse-corpus/manifest.json --corpus-root ./examples/parse-corpus --query "缓考申请" --top-k 3`
- **退出码**：0
- **输出**：valid=true, hits=3, chunks=17, indexed=17
- **Top 1**：score=6.6713, chunk_id=8726b8b8..., text="缓考申请\t考试前3个工作日\t需医院证明"
  - matched: 缓考(tf=1,df=2,idf=1.9741,contrib=2.5653), 考申(tf=1,df=2,idf=1.9741,contrib=2.5653), 申请(tf=1,df=5,idf=1.1856,contrib=1.5407)
  - score ≈ 2.5653+2.5653+1.5407 = 6.6713

## V08 示例 CLI 无命中

- **命令**：同上 `--query "不存在的查询"`
- **退出码**：0
- **输出**：valid=true, hits=0
