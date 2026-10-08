# T031 验证记录（verification.md，submission_revision=2）

> 所有命令在 Windows（Git Bash）下真实执行；退出码均为实测。**T031-R1 轮**只跑 JS 语法与 search/ask 行为回归（返工单范围）；未重跑向量实验、全量 pytest、ASR、Agent 或外部模型。

## 0. T031-R1 轮验证（2026-10-07）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node scripts/check-js-syntax.cjs` | 9 个 HTML 内联 JS 全过（含两页恢复状态修改） | 0 |
| `node scripts/check-search-behavior.cjs` | **21 scenarios passed**（17 既有 + 4 R1 链） | 0 |
| `node scripts/check-ask-behavior.cjs` | **33 scenarios passed**（29 既有 + 4 R1 链） | 0 |

R1 因果链断言要点：①`?student_type=本科&document_id=doc-2023` 跨页落地后控件保留且**显式提交 body.filters.student_type==='本科'、body.document_id==='doc-2023'**（search→ask 与 ask→search 两方向）；②`document_id=unavailable-review-file` 落地后控件保留原值（ghost+失效提示），**提交 body.document_id==='unavailable-review-file'**（绝非 null/undefined）且 422 message 展示；③目录延迟期间提交 0 请求（提示暂不提交），释放后提交携带两条件；④「指定文件」空选 0 请求+提示，显式切回「全部资料」后提交不带 document_id。桩=原生 select 语义（SelectElement：不存在 option 赋值得 ''）。

数据未改核验：selection-map `42d63bc4…`、experiment `57b22f93…`、T030 questions `5fde70a3…` 哈希复核一致。**无真实浏览器工具**——返工单两条链的浏览器复验留待 Astra，不代签。

## 1. T031 revision 1 轮验证（历史记录）

## 1. 聚焦测试（后端）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python -m pytest tests/test_source_selection.py -q` | **20 passed**（未选兼容、三模式单文件、条件交集、不放宽、422×3、search/ask 一致、目录、encode_documents 计数=1、generated mock 证据范围） | 0 |
| `python -m pytest tests/test_source_selection.py tests/test_search_api.py tests/test_ask_api.py tests/test_search_filters.py tests/test_qa_evidence.py -q` | **107 passed**（既有回归不破坏） | 0 |

## 2. 页面行为与语法

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node scripts/check-js-syntax.cjs` | 9 个 HTML 内联 JS 全过 | 0 |
| `node scripts/check-search-behavior.cjs` | **17 scenarios passed**（含 T031：快照保留/status 刷新不丢选择、空态区分、重试用原快照） | 0 |
| `node scripts/check-ask-behavior.cjs` | **29 scenarios passed**（含 T031：生成失败转摘录用原快照、历史存 document_id/恢复零请求/旧记录标签） | 0 |

桩环境（DOM/fetch stub）不是浏览器实证——真实浏览器核对命令与检查表见 demo-notes.md（本环境无浏览器工具，未运行、不代签）。

## 3. 真实包本地 API 演示

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python scripts/demo-source-selection.py` | api-demo.json：目录 20 份；选 2023 文件三模式命中全为 d1fe991c…、preview 前缀一致；选 2026 全为 5cb2ac21…；文件+日期排除 hits=[]；未知 ID 422（SOURCE_DOCUMENT_NOT_FOUND）；/ask extractive 证据=所选文件 | 0 |

## 4. 对照实验与冻结

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python scripts/evaluate-source-selection.py` | experiment.json + freeze.json；baseline 与 T030 存储排名 **30/30 逐项一致**；三模式 selection 分支 R/H=0.900（q19 不改善如实记录） | 0 |

- 选择映射 `selection-map.json` **跑前冻结**（SHA-256 `42d63bc4558584c0…`；题面文号/文件名→目录人工唯一匹配 10/10，不从 gold/排名反推）。
- 实验冻结 `freeze.json`：映射哈希 + 当前实现哈希（source_selection/service/api-search/api-ask/qa-evidence）+ BGE 身份文件；**T030 冻结未改**（其 questions/freeze 哈希复核仍为 `5fde70a3…`/`fd2f2476…`）。

## 5. 契约要点复核（测试断言覆盖）

- 未选择=旧行为（请求体无 document_id；命中含多文档混排）。
- 选文件后三模式只返回该 ID；文件选择∩日期/本科筛选相交；合法文档被排除时 hits=[] 不放宽、filter_summary 计数不被冒充。
- 空串/整数/未知 ID 显式 422；`/api/v1/search/documents` 无 local_path/sha256/正文字段；未配置 available=false 空目录。
- 计数桩：一次建库 encode_documents=1，选择切换/多次查询不重复编码；generated mock 仅收到所选文件证据（provider=fake-recording，真实外部调用=0）。

## 6. 未运行/未验证项（如实标注）

- 真实浏览器人工核对（无浏览器工具；命令与检查表已交付 demo-notes.md）。
- ASR/Agent/UI 全量回归、全量 pytest、性能/安全压力测试、多文件选择（任务不支持）。
- 实验 n=10 单次运行，无显著性检验；「提升」仅指增加用户条件后的对照差异，不作算法结论。
