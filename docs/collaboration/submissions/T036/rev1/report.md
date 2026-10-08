# T036 真实题集与模板离线人工复核包 — 实施报告（report.md，submission_revision=1）

身份：task_id=T036、task_revision=v1、**submission_revision=1、status=ready_for_review、external_model_calls=0、planner_live_verified=false、human_review_status=unreviewed**。零外部模型调用（构建仅用 Python 标准库 + 现有解析器，不加载检索/ASR/生成器）、无下载/安装、未 commit/push、未修改 Astra 文件。**本包是审阅辅助工具，不代表人工复核已完成；MiMo 未代填任何人工结论。**

## 交付物与实际输出路径

| 内容 | 路径 |
|---|---|
| 构建脚本 | `step2_code/backend/scripts/build-human-review-pack.py` |
| 离线页面模板 | `step2_code/backend/scripts/human-review-pack.html`（仅服务导出工具，产品页面未改） |
| 聚焦测试 | `step2_code/backend/tests/test_human_review_pack.py`（4 项）+ `scripts/check-review-pack.cjs`（DOM/JS 桩 15 项） |
| **复核包（原样默认）** | `step2_code/backend/.cache/human-review/T036-v1/`：`review.html`（SHA `f557f3e7…`）、`pack.json`（`53dccd30…`）、`README.md`（`66bc59f4…`） |
| **模拟导出示例** | `step2_code/backend/.cache/human-review/T036-v1-simulated-export.json`（SHA `eec10bf8…`；record_title=「模拟操作测试」，**非真实复核结论**） |
| 提交 | 本目录四件 + [demo-notes.md](demo-notes.md)（Astra 短清单） |

（按任务书不提交大型生成包副本；上述本机输出保持可用并已记录 SHA。）

## 复核包内容（构建时 77 条引用逐字/跨度/哈希程序化核对通过）

- **24 题（20 可答 + 4 不足）× 57 证据**：原 query、完整条件、answerable、事实组（OR/AND 语义明示）、既有理由/已查范围/修订记录字段；每条证据含文档/块 ID、跨度、逐字 quote、**原解析块全文**、前后相邻块、页码定位（未知如实标）、本地原件路径（可复制另开核对，不访问来源网站）。
- **13 步模板 × 20 引用**：detail、未说明项、必要/可选引用同构对照；跨页引用以全部原引并列展示（不截断页尾）。
- 不足 4 题展示已查范围/排除依据（无 gold 引用 ≠ 学校无规定）；语义注记（OR 每源独立完整支持、不同 fact_id=AND、程序化一致≠语义正确）常驻页面。

## 人工记录与导出（不写回任何历史文件）

- 逐题目、逐证据、逐步骤、逐引用四档意见（未复核/确认/需修订/未确认）+ 意见文本；**初值全部未复核**，复核人/记录标题留空，无预填签名或日期。
- 「导出复核记录」下载**新 JSON**（含输入文件 SHA 身份、record_type=human_review_record、复核人手填内容、各项意见与汇总计数）——不写回 gold、模板或历史 human-review.md；无导入合并/自动改标注/全选通过/登录/云同步。
- 页面**不自动保存**（无 localStorage），刷新/关闭丢失未导出意见，可随时导出阶段性记录；页面仅汇总数量，不能把整套资料标成已审定。

## 顺带修正（T035-R2 非阻断项）

defense-script 第 3→4 节衔接：2023 不推荐对照后**切回 2026、重新显式整理依据、确认入口出现后才点击**进入办事页；该步骤计入第 4 节 130 秒（30+40+40+20），总预算仍 **560 秒 ≤600**。human-review-pending.md 增补复核包工具入口（§0）。

## 验证摘要（详见 verification.md）

实跑构建命令 exit 0（77 条核对、24/57/13/20 齐备）；拒覆盖（非空目录 exit 1）；隔离坏引用拒绝（exit 1、不写包、原件未动）；HTML 离线（无 fetch/CDN/外链、数据内嵌）；默认意见 114/114 未复核；模拟导出：恰 1 项「需修订+意见」、其余 113 项未复核、输入 SHA 一致；长 ID（64 位）未截断；输入/历史实验 SHA 前后不变。桩证据≠真实浏览器（Astra 短清单见 demo-notes）。

完成后停止，等待 Astra 验收。T037 未发布。
