# T032 真实转专业办理清单与原文核对 — 实施报告（report.md，submission_revision=2）

身份：task_id=T032、task_revision=v1+T032-R1、**submission_revision=2、responds_to=T032-R1、status=ready_for_review、external_model_calls=0、planner_live_verified=false**。零外部模型调用、无下载/安装、未 commit/push、未修改 Astra 文件/STATUS/CLAUDE/探针。原语料包 v1.1、T030 gold/冻结、T031 实验全部只读（来源 PDF 哈希复算 `5cb2ac21…` 与 manifest 一致）。

## T032-R1 定向返工（revision 2 增量）

**P1 三处跨页引用页尾漏字已修复**（步骤 detail 表述完整但绑定证据未完整覆盖；旧对照表摘要曾误称已含）：

| 步 | 前页引用 | v1.0 → v1.1 char_end | 补齐页尾 |
|---|---|---|---|
| t2 基本原则 | 5c3a798d | 260 → **271**（块尾） | 按照必修课初修加权平均 |
| t8 资格遴选 | 10ea5893 | 505 → **507**（块尾） | 或后 |
| t12 学籍学业 | bb74305a | 457 → **463**（块尾） | 必须遵守学校 |

- 三条 quote/char_end 由脚本从真实解析块切片生成（非手写）；下一页必要引用保留；t12 次引去「— 5 —」页码前缀（可读性）；t8 detail 明确排序规则展开见 t2。
- 模板版本 1.0 → **1.1**；citation-crosscheck.md 更正旧摘要并附修订对照；SOURCE-CHECK.md 同步；api-demo.json 重新生成。revision 1 七件与 v1.0 模板快照归档（`rev1/`、`archive-v1.0/`，9/9 字节核验）。
- 验证：原引用跨度校验 **20/20 ok、saveable、exit 0**；Astra `T032-span-probe.py` **三项全过、exit 0**；正常草稿/verify 示例 exit 0（verify=unchanged）。仅模板/说明变更，未重复页面/全量/检索实验。**人工复核状态：未复核**（保留声明）。

## 概述

依据真实语料包中的《本科生转专业实施办法（校教发〔2026〕1号）》（document_id `5cb2ac21…e76`，2026-01-08 发布/生效，scope=本科，is_synthetic=false，**先核实后整理**），完整通读 5 个解析块后按原文「四、组织程序」组织 **一项版本明确、逐步有精确原文引用的办理模板**：

- `data/procedures/sicau-transfer-2026-v1/procedures.json`（sicau-transfer-2026，v1.0，is_synthetic=false，标题含文号/2026版）：**13 步 / 20 条引用**——前置（适用范围与申请资格自查、基本原则与转入限制、转入接收规则与特殊情况）+ 组织程序 (一)–(七) + 学籍学业与报到注册 + 其他。
- 每步主体/动作/时限均取原文明示内容；**材料清单、入口、联系方式、具体日历日期等原文未写明的全部标注「资料未说明」，不编造、不借 2020/2023 版或合成模板补齐**；关键例外前置保留（2024 及之前入学按〔2023〕1号执行、艺体/体育/中外合作仅同类互转、跨校区资格放弃不得再次申请、注册前受处分取消资格、学籍生效不得撤销等）。
- 每条引用绑定真实 document_id / 文件 SHA / block_id / 块内跨度 / 逐字 quote；跨页事实（超额排序 t2、遴选放弃 t8、学籍学业 t12）以多条必要引用共同支持，不截半句冒充完整事实。来源核对说明见 `SOURCE-CHECK.md`，逐字对照表见 [citation-crosscheck.md](citation-crosscheck.md)。
- **只说明该指定版本所载内容：不宣称现行有效、不判定资格、不保证申请成功**；保存为本机个人待办 ≠ 向学校提交申请。编制=模型辅助，**人工复核状态：未复核**。

## 运行与用户流程

- `scripts/serve-corpus.py --manifest … --corpus-root … --procedures data/procedures/sicau-transfer-2026-v1/procedures.json --port 8010` 显式装配；普通启动无模板维持既有行为；不自动混入合成 self-check/procedures/mock（合成演示原样保留）。
- 办事页流程闭环：事项（文号/版本标识）→ 生成草稿（逐步引用+原文跳转）→ 保存个人待办（本机）→ 勾选/备注/提醒 → 刷新恢复 → 「核对当前依据」（verify=unchanged）。四条件沿用既有准入；**确定的排除条件 → 依据不足、不可保存、不回退其他版本、不泄漏失效原文**。
- 最小修正两处文案：service 免责语按 is_synthetic 分支（真实模板不再自称“合成演示清单”）；页面顶部提示改为区分真实/合成模板的中性表述。未改算法/UI/推荐器/问答路由。

## 聚焦验证（详见 verification.md）

- **模板所有引用程序化核对一次**：`verify-procedures-citations.py` 真实包新解析 + service 逐字/跨度/哈希校验 **20/20 ok**，无条件草稿 saveable，exit 0。
- **最少业务验证**（api-demo.json）：真实模板加载、草稿可保存（无条件与本科条件均 20/20）；as_of_date=2020-01-01（先查 manifest：早于生效日）→ **不可保存、失败引用 quote=null、失败步骤 detail 抑制**；保存快照 verify=**unchanged**（篡改后 changed）。
- 页面改动相关回归：JS 语法 9 页、check-procedures-behavior 11 场景、tests/test_procedures.py 14 项，全过。未重跑检索实验/全量 pytest。
- **无真实浏览器工具**：短清单交 Astra 复验（demo-notes.md），stub/API 不冒充浏览器。

完成后停止，等待 Astra 验收。T033 未发布。
