# T017 定向返工报告（submission_revision=2，responds_to=T017-R1）

日期：2026-09-27。task_id=T017、task_revision=v1、submission_revision=2、**status=ready_for_review、external_model_calls=0**。仅按 T017-R1 修复与整理；未改工厂/旧页面/旧语料/gold，未扩大测试矩阵，零外部调用。

## P1 修复：无编号正文相似度前瞻分支方向

**根因**（`comparison/service.py` 相似度配对循环）：`nxt_r`（左当前 vs 右下一段）更匹配时，说明**右当前段是游离段**——应先记右当前为新增并推进 j、保留左当前等候配对；原实现却记左当前删除并推进 i，`nxt_l` 分支同样反向。导致“新增+修改”普通场景失效（探针实测正向 新增2/删除1/修改0）。

**修复**：两分支对调——`nxt_r >= nxt_l` → 记 `(None, ri)` 新增并 `j += 1`；否则记 `(li, None)` 删除并 `i += 1`。相似度门槛（0.6）保持不变，未达门槛的不相关段落仍保守归新增/删除，不强行配对。

**回归证据**：
- **Astra 独立探针** `T017-R1-probe.py`：修复后退出码 **0**，`forward={added:1, deleted:0, modified:1, unchanged:0}`、`backward={added:0, deleted:1, modified:1, unchanged:0}`，期望断言全部通过（修复前为 exit 1）。
- **新增 pytest 4 项**（`TestT017R1Lookahead`）：正向 新增1/修改1（修改项配对到“申请材料须交所在学院审核。”↔“…并签字。”两句正确原文，跨度 [0,len) 逐字一致）；反向 删除1/修改1（同两句配对、方向对调）；不相关段落不强行配对（修改 0、新增 1、删除 1）；说明文案与实现一致性断言。既有“插入不使未变段落错位”回归保留，`tests/test_comparison.py` 合计 **14 passed**。

## 顺手整理（说明与实际一致）

1. **不含表格差异**：`LIMITATIONS`、模块 docstring 与 README 明确“当前仅比较段落（paragraph）块，表格块不参与对比——不含表格差异；用于 DOCX 时勿把未展示的表格变化当作无变化”。页面本就渲染 `algorithm.limitations`（结果区“算法限制”行）自动可见。本轮不实现表格比较。
2. **重复条号文案修正**：实际实现为“仅首个参与标识配对，其余同号条款**直接归入新增/删除，不做正文匹配**”——原“其余按正文匹配处理”表述与实现不符，已改正（LIMITATIONS/docstring/README）。
3. **demo-notes 修正**：跨组拒绝改为 **API 验证**（页面下拉按分组联动无法选出跨组组合）；页面失败演示用**同文档**（“左右不能选择同一文档（未生成新比较结果）”）；浏览器复制实测明确留待 Astra 复验，不伪称已验证。

## 验证（真实命令见 verification.md）

- `T017-R1-probe.py` 退出 0（正反向均符期望）。
- `tests/test_comparison.py` 14 passed（10 原有 + 4 新；含跨度逐字断言）。
- 本地 API 演示重生成（comparison-demo.json / comparison-expectations.md），分类计数不变（1/1/1/3）、手工对照全一致；响应 limitations 已含新说明。
- 按返工单未改工厂与旧页面 → 未重复 42 项其他回归/页面行为；compare.html 未改（说明由响应 limitations 动态呈现）。

## 历史与文件

- revision 1 历史副本：`report.rev1.md`、`verification.rev1.md`、`submission.rev1.json`、`changed-files.rev1.json`、`comparison-demo.rev1.json`、`comparison-expectations.rev1.md`、`demo-notes.rev1.md`。
- 本修订修改：`comparison/service.py`（前瞻方向 + 说明）、`tests/test_comparison.py`（+4 回归）、`README.md`（边界说明）、demo-notes/提交记录；`scripts/demo-comparison-api.py` 未改（输出随响应更新）。清单见 `changed-files.json`。

## 验证层级与限制

- 修复证据 = 独立探针 + pytest（内存文档，不改产品语料）+ 本地 API 演示；stub/浏览器证据层级沿用 rev1 声明，浏览器复制留待 Astra 复验。
- 算法其余限制（条款重编号/移动）不变，随响应可见。

完成后停止，等待 Astra 验收。T018 未发布。
