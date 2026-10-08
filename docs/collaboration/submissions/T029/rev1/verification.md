# T029 验证记录

工作目录 `F:\Collage Paper`。零外部模型调用、无下载/安装、未 commit/push；原始数据集只读。验证集中于：输入→产品 manifest 映射（未知字段/来源保留）、选定文件原字节不变、原文跨度可核对、实际检索主路径。

## 1. 适配脚本与包构建（真实命令）

```bash
cd step2_code/backend
./.venv/Scripts/python.exe scripts/prepare-real-corpus.py --dataset-root "F:/Collage Paper/data/datasets/sicau-rag-v1" --selection .cache/t029/selection-final.json --out-dir "F:/Collage Paper/data/corpora/sicau-rag-pilot-v1"
# manifest.json: 20 份；产品校验器: valid   退出码 0
# 同命令重跑（核验模式，不覆盖）：VERIFY OK: 20 份输入/输出一致（未写入）  退出码 0
```

- **原字节不变**：拷贝后逐文件 SHA-256 与数据集 manifest/`checksums.sha256` 一致（脚本内置断言，20/20 通过）；仅核验最终候选文件，未反复哈希 1.32GiB 全库。
- **映射正确性**：产品校验器（validate_manifest）判定 manifest valid；`is_synthetic=false` 严格布尔；source_url/source_site 同源一致；全部来源（含 source_page）保留于 provenance.jsonl；未知日期=null、未知 scope=空数组（mapping-notes §1 逐字段规则）。

## 2. 解析验证（产品 parse 管线）

```bash
# parse_manifest(pack) → valid=True，errors=0，docs=20
```

- 20/20 解析成功（块数 2—370；PDF 页码 locator / DOCX paragraph+table_row）；**41 条 warnings** 均为学业管理办法 DOCX 合并单元格提示（非失败，逐条存 parse-summary.json）。
- **解析不全不伪装成功**：候选 dc7012b16a2c（评选实施细则）共 5 页中 1、2 页未提取文本（图像页）→ 解析阶段即报 DOCUMENT_PARSE_ERROR，移出准入包并入待处理清单（intake-report §3）。

## 3. 检索验证（预期先冻结再查询）

```bash
# 预期保存：.cache/t029/query-checks-expected.json（查询前写入，含 expected_quote/来源/类别）
# 实测输出：docs/collaboration/submissions/T029/query-checks.json
```

- **9 题 BM25 全部实测** + 4 题（q1/q3/q5/q9）Dense/Hybrid 冒烟；一次索引构建（chunk 数与分段耗时记录于 query-checks.json index 节，非性能结论）；本地 BGE 无下载。
- 逐题记录条件、实际排序/分数/文档/块/span/preview_url、引句命中（**空白归一化**匹配——PDF 折行沿用解析规则；正式引用跨度以原块逐字为准）、逐题分析。
- 覆盖四类要求：明确规则/材料/流程（q1/q4/q5/q7/q9）、两版差异（q2/q3）、带条件准入/未知被排除（q6）、无所问依据但有命中（q8）。**不要求全命中、未调算法**：q3 的 2023/2020 版冲突句未入 top5 如实记录。
- **引句回溯**：9 条关键引用 span 逐字符定位与原块切片一致（citation-crosscheck.md，数字/否定词/主体/时限/版本关系核对）；原 PDF 页/DOCX 版面独立复核方法与交接项已列。

## 4. 实际检索主路径（API 级，零外部请求）

```bash
# serve-corpus build_app(pack) + TestClient：
# GET /api/v1/search/status → ready；document_count=20；parsed_count=20；synthetic_count=0（真实资料）；modes=[bm25]
# POST /api/v1/ask（extractive，q1）→ 200 evidence_only；5 条证据；E1=68fb37043ab7/8a790c05/span[0,364]/preview_url ✓
```

摘录→出处闭环成立；生成按钮语义=未配置（首批默认生成器关闭）。**浏览器部分交 Astra**（demo-notes 检查表 a—f）；MiMo 无浏览器，未编造截图。

## 5. 范围与未验证

**真实核查**：§1—§4 全部本轮实际执行。
**未运行**：全量/UI/ASR/Agent 测试（默认不跑）；未改共享解析器（无解析回归需求——parse.py 未动）；未跑 T027 评测（不混算）。
**未验证**：真实校园准确率（9 题≠评测）；浏览器交互（交 Astra）；OCR/旧 Office/表格件（待处理）。

## 6. 依赖与版本

未安装新依赖；解析/检索/摘录全部走既有产品管线（`corpus/parse|validate`、`retrieval/*`、`qa/evidence`、serve-corpus）；新增仅 `scripts/prepare-real-corpus.py`（其 `--help` 型用法见 mapping-notes/demo-notes）。
