# T021 文本PDF解析与语料接入准备 — 实施报告

身份：task_id=T021、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**（零外部模型调用；未爬学校网站、未接 OCR）。

## 概述

补齐文本 PDF 入口（逐页解析、页码定位与引用）与可复查的本地语料登记操作：preview→search→ask extractive 串通 PDF 页码/出处；无文本/解析不完整明确提示不冒充成功；登记 CLI 产出候选语料包；真实资料接入说明齐备。旧 TXT/DOCX 块 ID 与模板/规则引用**零变化**。

## 功能交付（对照任务书）

1. **PDF 解析**（`corpus/parse.py`，pypdf 6.19.0）：逐页提取 → 明确规范化（行尾空白去除、换行统一 `\n`、连续空行折叠为单空行；不改写非空白字符、不用 LLM 补正文）→ 空行分段；块定位 `pdf_page`（1 基页码+页内段序）；引用跨度相对提取块逐字一致，不宣称与视觉排版等价。加密/损坏明确失败不解密绕过；复杂表格/多栏声明提取限制。
2. **旧引用兼容（红线）**：`_make_block_id` 增加 `parser_version` 参数（默认 PARSER_VERSION=1.0）——TXT/DOCX 路径种子不变、块 ID 不变（回归断言 `9df6bfbd98df733e`/`f28ee3e4c5372f7c` 等在位）；PDF 用独立版本 **`pdf-1.0`** 参与哈希与文档 parser_version。procedures 模板在旧语料上引用核查仍通过。
3. **无文本/不完整明确提示**：全篇无文本 → “全篇未提取到文本…需要 OCR/人工核对”，不进索引、不算解析成功；混合文档（部分页无文本）→ 明确列页并整篇暂不入索引提示补资料（空白页≠扫描件）；`valid=false` 如实。
4. **preview→search→ask 串通**：preview 显示“PDF 第 N 页 · 段 K”；search 命中卡与 ask 证据卡显示页码；`preview_url` 跳转对应提取块（EvidenceItem 新增 `locator` 字段）。无内嵌阅读器/下载接口（按任务不需要）。
5. **登记 CLI**（`scripts/register-corpus.py`）：本地文件 + 元数据 JSON → 逐字节复制原文（不修改输入）+ 哈希 + manifest → 复用既有校验/解析检查 → 可读结果与启动命令。缺必填元数据**明确列出、不猜**；输出目录非空拒绝覆盖；不下载 source_url；TXT/DOCX/PDF 同一入口。`scripts/serve-corpus.py` 启动候选包——**只加载所给语料，不加载合成办事模板/自查规则/mock 生成器**。
6. **真实资料接入说明**（README）：所需原文与来源信息、未知字段按 schema 填 null/空数组（空=未知）、synthetic 与真实区分、PDF 人工核对再启动。
7. **演示夹具与对照**：`examples/pdf-corpus/`（`make-pdf-fixtures.py` 本地生成：fpdf2 + 本机 SimHei，两页中文文本含数字 10/2024 与否定词 不/不得 + 无文本 PDF，生成方式记录于夹具 README.txt）；`pdf-extraction-crosscheck.md`（原文→提取块/页码→命中引用）与 `candidate-package/`（登记 CLI 实跑候选包示例 + 报告）。

## 验证摘要（受影响聚焦，真实命令见 verification.md）

- `tests/test_pdf_corpus.py` **11 passed**（多页/稳定 ID/跨度、无文本、损坏 PDF、旧块 ID 与模板引用不变、search/ask 页码与跳转、登记 CLI 成功/缺元数据/拒覆盖）+ 受影响回归 **91 passed**（parse/procedures/ask_api/demo_campus）。
- JS：7 页语法 + ask 25 / search 14 场景通过（页码显示为增量，行为语义未变）。
- pip check 通过（新依赖 pypdf==6.19.0、fpdf2==2.8.8 已写入 requirements.in）。
- 调试记录：fpdf2 2.8 参数顺序/光标问题致夹具生成失败两轮（multi_cell 需关键字参数 + `new_x="LMARGIN"`），属生成脚本细节；旧“PDF 不支持”测试改为 PNG 保持原意图（PDF 现为受支持格式）；register CLI 测试 subprocess 编码按 UTF-8 显式解码。

## 修改与新增文件

- 新增：`corpus` 支持内置于 parse.py；`scripts/make-pdf-fixtures.py`、`scripts/register-corpus.py`、`scripts/serve-corpus.py`、`scripts/demo-pdf-intake.py`、`examples/pdf-corpus/`（4 件）、`tests/test_pdf_corpus.py`
- 修改：`corpus/parse.py`、`qa/evidence.py`、`api/ask.py`、`static/preview.html`、`static/ask.html`、`static/search.html`、`tests/test_corpus_parse.py`、`requirements.in`、`README.md`
- 清单见 `changed-files.json`；未修改：Astra 文档、旧语料/gold、已验收生成规则、TXT/DOCX 解析行为。

## 已知限制

- **无浏览器工具**：页面/预览实测留待 Astra（demo-notes 检查表 a—e）；stub 不冒充浏览器证据。
- 文本 PDF only：扫描件不做 OCR（明确提示人工核对）；提取不保证与视觉排版/阅读顺序等价。
- 真实学校资料尚未提供；候选包为合成示例，不虚构真实语料。

完成后停止，等待 Astra 验收。T022 未发布。
