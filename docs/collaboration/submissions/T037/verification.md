# T037 验证记录（verification.md，submission_revision=1）

> 命令真实执行、退出码实测。范围=争议引文逐字切片核对 + 现有筛选服务准入复现 + SHA 不变核对；**未跑 pytest 全量/检索实验/UI/ASR/Agent/模型**；零外部调用。

## 1. 争议引文逐字切片核对（真实解析器）

| 命令（要点） | 结果 | 退出码 |
|---|---|---|
| `python …`（parse_manifest 真实包新解析；q10 全 14 条 gold 跨度逐条 `text[s:e]==quote`） | **14/14 OK**（f1×7 普通情形、f2×7 互评情形） | 0 |
| 同上（q08 f1-s1/f1-s2、u03 两源、u04 办理地点 [80:175]、适用范围句 [21:54]） | 全部 OK | 0 |
| 废止/替代检索（20 份全文关键词：废止/以本办法为准/不一致/原办法…） | 11 处命中：10 处为兜底条款（不一致以本办法为准/上级文件为准）+1 处教育部文件点名废止其前身——**无任何文件点名废止教发〔2016〕10号** | 0 |
| 2016 规范施行条款查证 | 无失效/替代声明；标注「（试行）」 | 0 |

## 2. 现有筛选服务准入复现（u03/u04 + 无筛选对照）

| 命令（要点） | 结果 | 退出码 |
|---|---|---|
| `compute_allowed_document_ids(docs, u03 条件 as_of=2026-10-03)` | allowed=4（57c0945c/5cb2ac21/85840636/bb8ba97c）；excluded `date_unknown_from=16`；**bed3ac/db05e0 均排除** | 0 |
| 同上（无筛选对照） | active=false、allowed=ALL 20；bed3ac/db05e0 可见 | 0 |
| `compute_allowed_document_ids(docs, u04 条件 student_type=本科)` | allowed=18；excluded `scope_unknown=2`（83eb/ddf41747）；**83eb 排除** | 0 |
| 同上（无筛选对照） | 83eb 可见 | 0 |

匹配语义核实（filters.py 源码阅读）：`want not in values` 精确匹配——`["在校生"]` 不放行 student_type=本科（B2 选项后果已在方案中说明）。

## 3. 输入与历史产物不变（前后核对）

| 文件 | SHA | 结论 |
|---|---|---|
| questions.json v1.3 | `5fde70a332744b64…` | 未变 |
| manifest.json | `34e182f18178c8a8…` | 未变 |
| procedures.json v1.2 | `78f1c1d9f839c41d…` | 未变 |
| T031 experiment.json | `57b22f93bd1420fa…` | 未变 |
| T034 experiment.json | `cef9f162f1eb164a…` | 未变 |
| 用户意见记录 | `2e1af1493846efd7…` | 未变 |

**6/6 不变**（exit 0）。未写 manifest/gold/模板；未重算历史指标。

## 4. 原文快照（.cache/T037-source-check/）

| 文件 | SHA-256（前 16） | 内容 |
|---|---|---|
| `287dcca7-毕业论文2016-全文块.txt` | `0bb4ab87608ba35f…` | 64 块全文 |
| `bed3ac95-考试管理2019-全文块.txt` | `540ec46bf0835df6…` | 19 块全文（含落款/印发日期） |
| `db05e0ca-考场规则-全文块.txt` | `ceca127cb9ec1da8…` | 2 块全文 |
| `83eb3948-学籍指南-全文块.txt` | `11a2dc4ef158799c…` | 4 块全文 |
| `bb8ba97c-教学管理2025-全文块.txt` | `752df431a358feb7…` | 75 块全文（最新版对照） |

结构化证据：`source-check.json`（SHA `579c13a6988f14dd…`）——含来源身份/文号/页码块跨度/逐字 quote/采用判断/未验证点。

## 5. 未验证/证据边界

- **未查**学校现行网页、未验证政策废止关系；「2016 规范是否被废止」的最终认定属人工/权威来源事项。
- bed3ac `effective_from=2019-11-07` 依正文落款/印发推断，无独立发文登记佐证（已在 source-check unverified 标注）。
- 83eb「所有在校生」与研究生语境来源的优先关系**未由人裁定**。
- 本轮无产品代码变更；筛选放宽/版本规则/新数据集均未实施。
