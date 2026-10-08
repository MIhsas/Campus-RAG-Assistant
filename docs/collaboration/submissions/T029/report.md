# T029 真实语料首批接入与检索验证 — 实施报告（revision 2）

身份：task_id=T029、task_revision=v1、**submission_revision=2、responds_to=T029-R1**、status=ready_for_review、**external_model_calls=0、planner_live_verified=false**。零外部模型调用、无下载/安装、未 commit/push；原始数据集只读；未改检索/筛选算法、旧 gold、Astra 探针/评论、STATUS/CLAUDE。v1 提交件归档 `rev1/`；v1 语料包保留 `data/corpora/sicau-rag-pilot-v1/`。返工明细见 [fix-report.md](fix-report.md)。

## 概述

T029 v1 完成首批真实资料接入（20/1182）与检索闭环验证。**T029-R1 定向返工**：① 修复重复核验漏检（输入原文件 SHA、selection/provenance 边车比对、产品有效性——任何漂移 DIFF 报出、非零退出、不覆盖）；② 修正来源站点（按已选 source_url 主机解析）与两份已核实日期，生成 **`data/corpora/sicau-rag-pilot-v1.1/`**（v1 保留）；③ 合并数量对账、scope 口径、演示预期与 compare 固定提示整理。

## 交付物

| 文件 | 内容 |
|---|---|
| [fix-report.md](fix-report.md) | R1 两项必修 + 随单整理的改动、真实命令/退出码、证据层级 |
| [intake-report.md](intake-report.md)（rev2） | 1182 盘点 vs 20 份解析（**维度不相加**；25 条选择记录=20+5 对账；其余 1157=930+227）；待处理清单；未知条件排除；日期补正与准入对照 |
| [mapping-notes.md](mapping-notes.md)（rev2） | 字段映射（**source_site=URL 主机**，原站点留 provenance）；日期已填 4 项及页码依据；版本关系核实；副本去重 |
| [parse-summary.json](parse-summary.json) | 20 份逐份解析（正文未变，v1.1 同字节） |
| [query-checks.json](query-checks.json) | 9 题开发核查（预期先冻结；**排名证据对应 v1、与 v1.1 同字节等价**） |
| [citation-crosscheck.md](citation-crosscheck.md) | 9 条关键引用 span 对照 |
| [demo-notes.md](demo-notes.md)（rev2） | v1.1 启动命令/复现；演示预期改用已验证三版题（q2）；浏览器步骤交 Astra |

**大型产物**：`data/corpora/sicau-rag-pilot-v1.1/`（20 份原字节+manifest+provenance+selection）；v1 包与原数据集均未动。

## R1 修复结果（摘要）

1. **VERIFY 六项比对**（输入 SHA/manifest/selection/provenance/输出哈希/产品有效性）——Astra 隔离探针原样复跑 **4/4 passed、exit 0**（输入变化、selection 变化均非零退出且不覆盖）；精简回归 3 passed。
2. **source_site**：20 份全部与已选 URL 主机一致（d1fe rwy→jiaowu、9204 jiaowu→jwnews 已纠；原站点存 provenance）。
3. **日期补正 2 份**：bb8ba97c 发文/生效 2025-11-11（PDF p75「自发文之日起施行」）、68fb3704 发文 2018-12-20（p2 落款；无施行条款→effective 仍 null）。**准入对照**：as_of=2026-10-03 时 bb8b 被排除→准入（3/20→4/20），筛选未放宽；68fb 仍排除（不推算生效日）。
4. **随单整理**：数量对账（1157=930+227；25 条选择记录对账；non_text≠图片数）、scope 18/2、演示预期改 q2、compare 固定提示改中性「解析块级文字差异」（JS 9 页语法通过）。

## 验证摘要（真实命令见 verification.md / fix-report.md）

- Astra 探针原样 exit 0；`tests/test_prepare_real_corpus.py` 3 passed；JS 语法 9 页通过。
- v1.1 构建 + 两次重复核验 `VERIFY OK` exit 0；v1↔v1.1 逐字节一致、manifest 差异恰为 source_site×2+日期×2。
- v1.1 摘录→出处主路径补核（E1=68fb3704/8a790c05/span[0,364]/preview；synthetic_count=0）。**未重跑**三模式编码与九题（同字节，证据等价）；**未跑**全量/UI/ASR/Agent。

## 边界声明

**不得写全库已入库**（20/1182）；真实校园准确率未验证（9 题≠评测，不与 T027 混算）；compare「新增 9/删除 5/修改 0/未变 0」为解析块级结果，不宣称条款级准确；办事/自查模板未适配；生成器默认关闭。

完成后停止，等待 Astra 验收。T030 未发布。
