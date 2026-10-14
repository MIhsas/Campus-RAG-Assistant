# T041 当前交付包与真实生成案例收尾 — 实施报告（report.md，submission_revision=2，responds_to=T041-R1）

身份：task_id=T041、task_revision=v1、**submission_revision=2、responds_to=T041-R1、status=ready_for_review**、**external_model_calls=0**、planner_live_verified=false；T040 `live_verified=true` **仅历史四题链路/存档限定不变**。
本轮=T041-R1 两项文档口径修复 + 同批收紧；**零外部调用**，不重跑已通过的指标/原文/token/秒数/--help/结构核对（沿用 T041-audit 53 项与 T040-R4 记录）。详见 [fix-report.md](./fix-report.md)。revision 1 五件已归档 `rev1/`；九件改前归档 `docs/delivery/archive-t041-rev1/`。

## 1. 必修1 人工状态口径（experiment-index + defense-script）

「人工未复核」笼统表述统一为：**模型辅助编制；已收到用户逐项意见 109 确认/3 需修订/2 未确认（模板 33 项已确认）；T039 新改项与 T040 新答案待定向复核，非完整教师审定或盲评 gold**。experiment-index 开头/末尾两处替换、历史分表标「实验运行时点（当时尚未收到用户逐项意见）」；defense-script §6 讲解与问题 1/8 三处替换。不抹已有意见、不代签开放项、不改任何数字。

## 2. 必修2 浏览器证据归属（evidence-matrix）

§8「T038—T041 均无浏览器实操/历史归属 T016—T023」错误表述删除；改为按**各评审实际操作范围**引用：T016—T023 各记录；**T038 真实浏览器主路径**（候选查看/控件绑定原结果/PDF 第 4 页跳转/复制与历史隔离/新请求清旧列表/指定文件求交不回退，依据 T038-R1 与 T038-browser/verification.md）；T029/T031/T032/T033 各按其范围。**T041 本轮无新浏览器实操、T040 无浏览器生成闭环证据**保留。§4 待办行浏览器归属同批修正（T032-R1/T033-R1 按范围）。

## 3. 同批收紧

README「按 T035 原样」限定历史快照段落；q08 gold 缺口注明「本次 T040 BM25 正式证据包」（E4/表 6-5，不外推三模式）；thesis 末节标「后续扩充参考（当前首批已接入、开发集已建立）」；runbook §6 模板行区分「2026 真实模板 1.2 已接入+用户确认 33 项」与「学校政策现行性未认证」。

## 验证摘要（详见 verification.md）

九件当前/历史口径扫查通过；涉及链接 30/30（含新增 T038 依据 2 条）；本轮修改 6 件 SHA 实测、未变 3 件与 rev1 一致；双归档先于修改且未覆盖既有归档。已通过数字/原文未重算。**不写 accepted，语义待 Astra 复验。**

完成后停止，等待 Astra 验收；不推进 T042。
