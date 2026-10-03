# T021 演示记录与步骤（PDF 解析与语料接入）

## 证据层级（先读）

| 层级 | 内容 | 性质 |
|---|---|---|
| 后端 pytest | `tests/test_pdf_corpus.py` 11 项 + 受影响回归（parse/procedures/ask/demo 共 91 项） | 真实本地运行 |
| 本地对照/候选包 | `pdf-extraction-crosscheck.md`、`candidate-package/`（登记 CLI 真实跑通） | 合成夹具，零网络 |
| 页面 JS | 7 页语法 + ask 25 / search 14 场景（含页码显示） | stub，非真实浏览器 |

本轮无浏览器工具：页面/预览实测留待 Astra；stub 不冒充浏览器证据。

## 合成 PDF 夹具（可复现生成）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\make-pdf-fixtures.py
# sample-text.pdf（两页中文文本，含 10 个工作日/2024 级/不重新评阅/不得由他人代办）
# sample-no-text.pdf（仅线条矩形，无文本）
```

生成方式：fpdf2 + 本机 Windows SimHei 字体，本地生成无网络（记录于夹具 README.txt）。合成资料，不代表真实学校规定。

## Astra 可运行检查表

| # | 操作 | 预期 |
|---|---|---|
| a 解析与页码 | 启动 `serve-corpus.py --manifest examples\pdf-corpus\manifest.json --corpus-root examples\pdf-corpus` → /preview | syn-pdf-text-001 两块分别标注“PDF 第 1 页 · 段 1”“PDF 第 2 页 · 段 1”；syn-pdf-notext-001 显示“全篇未提取到文本…需要 OCR/人工核对”（不进索引） |
| b 检索跳转 | /search 查“复核 分数” | 命中卡片显示“PDF 第 N 页”；“查看原文”跳转对应提取块 |
| c 摘录引用 | /ask 同词 → 整理依据 | 证据卡显示页码；文本与提取块逐字一致；跳转同 b |
| d 登记 CLI | `register-corpus.py --input … --meta … --out-dir <新目录>` | 原文逐字节复制（输入不改）、哈希、校验/解析结果、启动命令；缺元数据明确列出；非空输出目录拒绝覆盖 |
| e 旧引用兼容 | /procedures 生成缓考草稿（parse-corpus） | 模板引用全部通过（TXT/DOCX 块 ID 未变） |

## 候选语料包示例

`candidate-package/`（register-corpus.py 实跑产物：sample-text.pdf 原文副本 + manifest.json，登记/解析均通过）与 `candidate-package-report.txt`（CLI 原始输出）。真实资料接入步骤见 backend/README.md“真实资料接入说明”。

## 边界

- 文本 PDF only（pypdf，无 OCR）；提取与视觉排版不宣称等价；复杂表格/多栏仅按提取顺序。
- 空白页不等于扫描件断言；混合文档整篇暂不入索引并提示补页。
- 正常资料库用 serve-corpus.py：不加载合成办事模板/自查规则/mock 生成器。
