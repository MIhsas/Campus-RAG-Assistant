# T021 PDF 原文 → 提取块/页码 → 命中引用 对照

夹具：`examples/pdf-corpus/sample-text.pdf`（scripts/make-pdf-fixtures.py 生成：fpdf2 + 本机 SimHei，本地合成，无网络）。
提取规则：逐页 pypdf 提取 → 行尾空白去除/换行统一/连续空行折叠（不改写非空白字符）→ 空行分段；
块定位 `pdf_page`（页码 1 基 + 页内段序）；引用跨度相对提取块逐字一致（不宣称与视觉排版等价）。合成资料，不代表真实学校规定。

| 页 | 提取块（block_id / part） | 提取文本 |
|---|---|---|
| 1 | 3428681d9af60ba3 / part 1 | 【合成测试 PDF — 仅供解析演示，不代表真实学校规定】\n第一章 总则\n第一条 成绩复核申请须在成绩公布后 10 个工作日内提出。\n第二条 复核仅核对分数，不重新评阅试卷。 |
| 2 | d897e41b44bfa468 / part 1 | 第二章 补充\n第三条 缓考申请不得由他人代办。\n第四条 2024 级学生适用本示例，2025 级另行通知。 |

## 检索命中 → 引用核对（query="复核 分数"）

- 命中 #1：块 3428681d9af60ba3（PDF 第 1 页）→ preview_url `/preview#syn-pdf-text-001/3428681d9af60ba3`

## ask extractive 证据引用

- E1：块 3428681d9af60ba3（PDF 第 1 页 · [0,87)），quote 与提取块逐字一致，preview_url `/preview#syn-pdf-text-001/3428681d9af60ba3`

## 无文本 PDF 的明确不可用状态

- syn-pdf-notext-001：`全篇未提取到文本（可能为扫描件或图片型 PDF），需要 OCR/人工核对；不进索引、不算解析成功`（不进索引、不算解析成功）
