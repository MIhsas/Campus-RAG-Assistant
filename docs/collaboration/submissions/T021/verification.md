# T021 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦验证：未跑全量、embedding 重编码、ASR 或真实生成；external_model_calls=0。

## 1. 夹具生成（本地，无网络）

```bash
./.venv/Scripts/python.exe scripts/make-pdf-fixtures.py
# sample-text.pdf 15880 bytes / sample-no-text.pdf 857 bytes，写入 examples/pdf-corpus（含 manifest 与生成说明）
# 退出码：0
```

生成方式 fpdf2 2.8.8 + 本机 SimHei（C:/Windows/Fonts）。调试记录：fpdf2 2.8 `multi_cell` 位置参数错位与光标驻留行尾两处问题（关键字参数 + `new_x="LMARGIN", new_y="NEXT"` 解决），属生成脚本细节，不涉解析器。

## 2. 相关 pytest（11 项新增 + 受影响回归 91 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_pdf_corpus.py tests/test_corpus_parse.py tests/test_procedures.py tests/test_ask_api.py tests/test_demo_campus.py -q -p no:cacheprovider --basetemp .cache/t021-iter6 --tb=short -rs
# 91 passed, 2 warnings in 6.69s
# 退出码：0
```

- `test_pdf_corpus.py`（11）：两页提取（页码 1/2、`pdf_page` 定位、数字 10/2024 与否定词 不/不得 逐字在提取文本中）；块 ID 两次解析一致；引用跨度=提取块全文逐字；无文本 PDF “未提取到文本…OCR”错误且不入 documents；损坏 PDF 明确失败；**旧 TXT/DOCX 块 ID 在位（9df6bfbd98df733e / f28ee3e4c5372f7c）且 parser_version=1.0**；procedures 模板引用在旧语料仍 saveable；search/ask 命中携带 locator 页码与 preview_url；登记 CLI 成功（哈希一致、输入未改、启动命令）、缺元数据列字段退出 2、非空输出目录拒覆盖。
- 受影响回归：`test_corpus_parse`（含 PDF 派发与**旧 ID 不变**断言）、`test_procedures`（模板引用）、`test_ask_api`（EvidenceItem 新增 locator 兼容）、`test_demo_campus`（组合语料解析）。
- 调试记录：旧 `test_pdf_rejected` 断言 .pdf 不支持——与 T012 契约冲突，改为 doc.png 保持“不支持格式明确拒绝”原意图；register CLI 测试 subprocess 显式 UTF-8 解码（Windows 默认 GBK 解码失败）。

## 3. JS 语法与页面行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 7 HTML files passed syntax check.（退出码 0）
"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 25 scenarios passed（退出码 0）
"D:/nodejs/node.exe" scripts/check-search-behavior.cjs
# check-search-behavior: 14 scenarios passed（退出码 0）
```

ask/search 仅增加 PDF 页码显示与 EvidenceItem locator（增量显示），行为语义回归不破。preview.html 增加 pdf_page 定位文案（无独立行为脚本，语法检查覆盖）。

## 4. 对照与候选语料包（本地 API/CLI 实跑）

```bash
./.venv/Scripts/python.exe scripts/demo-pdf-intake.py --out-dir "F:/Collage Paper/docs/collaboration/submissions/T021"
# register_exit: 0（登记校验：通过；解析检查：通过）
# 退出码：0
```

- `pdf-extraction-crosscheck.md`：两页原文→提取块/页码逐条对照 + 检索命中/摘录引用核对 + 无文本 PDF 明确不可用状态。
- `candidate-package/`：register-corpus.py 实跑产物（sample-text.pdf 原文副本 + manifest，校验/解析通过）；`candidate-package-report.txt` 为 CLI 原始输出。

```bash
./.venv/Scripts/python.exe -m pip check
# No broken requirements found.（退出码 0，新依赖 pypdf==6.19.0 / fpdf2==2.8.8 已写入 requirements.in）
```

## 5. 浏览器检查情况（如实说明）

本会话**无浏览器工具**，preview 页码/检索跳转/摘录引用的浏览器实测留待 Astra（demo-notes 检查表 a—e）。stub 不冒充浏览器证据。

## 6. 未验证项

1. 真实浏览器闭环（交 Astra 补验）。
2. 扫描件 OCR（按任务不实现）；复杂表格/多栏结构识别（仅声明提取限制）。
3. 真实学校 PDF 提取质量（真实资料未提供；候选包为合成示例）。
