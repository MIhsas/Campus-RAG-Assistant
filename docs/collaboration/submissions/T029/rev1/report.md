# T029 真实语料首批接入与检索验证 — 实施报告

身份：task_id=T029、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0、planner_live_verified=false**。零外部模型调用、未安装依赖/工具、未 commit/push；原始数据集 `data/datasets/sicau-rag-v1` **只读**（含其 verification.json 未动）。

## 概述

将用户提供的 1182 份真实四川农业大学资料**有选择地**接入现有产品：轻量全库盘点 → 24 份候选 → 正文核实（文号/施行条款/副本比对）→ **20 份准入首批语料包** `data/corpora/sicau-rag-pilot-v1/`（原字节+原 SHA 保留）→ 产品 validate/parse/chunk/serve 管线验证 → 9 道开发核查问题（预期先冻结再查询）+ 9 条关键引用独立对照 + 摘录→出处闭环。**接入验证，不是正式真实校园效果评测**；办事/自查模板未改、未冒充已适配。

## 交付物

| 文件 | 内容 |
|---|---|
| [intake-report.md](intake-report.md) | 1182 全库盘点 vs 首批 20 份实际解析（两个数字分开）；待处理清单（OCR 63/旧 Office 144/表格 19/非文本/长手册等）+ 本次 defer 5 份及原因；未知条件被筛选排除说明；版本关系核实摘要 |
| [mapping-notes.md](mapping-notes.md) | 数据集清单→产品 manifest 字段映射；未知保留规则（null/空数组、year_hints 不作日期）；**版本关系核实依据**（转专业 3 版、教学管理 4 版正文互证）；同文副本去重判定；来源/provenance 保留 |
| [parse-summary.json](parse-summary.json) | 20 份逐份解析结果（块数/页码/locator/警告；warnings=DOCX 合并单元格提示 41 条，非失败；1 份解析不全已移出并记录） |
| [query-checks.json](query-checks.json) | 9 题（预期先存）× BM25 + 4 题 Dense/Hybrid 冒烟：条件、实际排序/分数/文档块跨度/preview 链接、引句命中（空白归一）、逐题分析 |
| [citation-crosscheck.md](citation-crosscheck.md) | 9 条关键引用 span 逐字对照（数字/否定词/主体/时限/版本关系）+ 原 PDF 页/DOCX 独立复核方法 |
| [demo-notes.md](demo-notes.md) | Windows 启动命令（含空格路径）+ 浏览器核验步骤（交 Astra）+ API 级已核对证据 + 复现命令 |

**大型产物位置**：语料包 `data/corpora/sicau-rag-pilot-v1/`（manifest.json + 20 原文件 + provenance.jsonl + selection.json；文件名=doc_id=原 SHA-256）；数据集 manifest SHA-256 `6a41ff3c…`（与 Astra preflight 一致）。

## 关键结果

- **盘点/准入**：全库 1182 份仅做清单分类；首批 20 份解析 **20/20 成功**（valid=True、0 错误）；1 份解析不全（PDF 前 2 页图像）移出并记录。
- **版本关系已核实 2 组**：转专业〔2020〕1→〔2023〕1→〔2026〕1号、本科教学管理办法〔2018〕2→〔2020〕6→〔2022〕12→〔2025〕14号（正文施行/适用条款互证，旧版身份保留、不混成现行规定）；其余独立组记待核实；同文副本 3 份去重 defer。
- **未知如实保留**：日期无据=null；适用范围未知=空数组（加筛选时保守排除并如实说明，含年级区间口径无法表达的原句记录）。
- **检索验证**（真实资料本地，9 题开发核查、非 gold）：明确规则/材料/流程题预期来源均入 top5；两版差异题三版齐现；条件准入题演示未知被保守排除；**无所问依据题（缓考门数）top5 有命中但无依据——有命中≠有依据实测支持**。Dense/Hybrid 4 题冒烟（本地 BGE、一次索引构建、无下载）。**不与 T027 合成指标混算**。
- **闭环**：`/api/v1/ask` 摘录返回 E 编号+文档/块/span+preview_url；状态 `synthetic_count=0`（真实资料标识）。

## 验证摘要（真实命令见 verification.md）

- 适配脚本构建 20 份包（产品校验器 valid）+ **重复执行核验模式 VERIFY OK（不覆盖）**；选定文件原字节 SHA 逐份一致。
- 解析 20/20；查询 9 题 BM25 + 4 题 Dense/Hybrid（引句命中与逐题分析见 query-checks.json）；9 条引用跨度对照（citation-crosscheck.md）。
- API 闭环（status/ask）实测；**浏览器核验步骤交 Astra**（demo-notes 检查表 a—f，MiMo 无浏览器不编造截图）。

## 边界与声明

- **不得写全库已入库**：仅 20/1182 首批准入，其余留待处理清单（OCR/转换/表格/主题范围）。
- **真实校园准确率未验证**：9 题开发核查≠评测；不与 T027 合成指标混算。
- 首批默认**生成器关闭**；办事/自查模板未适配真实政策；未改产品算法/语料/gold/旧题集。
- 未联网补采、未装 OCR/转换工具、未把文件送外部模型、未 commit/push。

完成后停止，等待 Astra 验收。T030 未发布。
