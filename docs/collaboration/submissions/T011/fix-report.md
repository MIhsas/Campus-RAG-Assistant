# T011-R1 定向修复报告（submission_revision=2）

日期：2026-09-22。responds_to=T011-R1。task_revision 保持 v1。范围严格按返工单：仅前台状态更新逻辑与相应行为检查；未改后端，未重跑全量 pytest、依赖检查、模型编码与三模式评测。

## P1 根因

`static/search.html` 中 `fillSelect` 重建下拉时末尾固定执行 `sel.value = ''`，且 `loadStatus` 每次都无条件重建三个筛选下拉；而 `executeSearch` 成功路径会再次调用 `loadStatus()`。于是成功搜索后，用户已选的校区/类型/年级被清回“不限”，下一次 `doSearch` 经 `currentFilters()` 读到空控件，请求悄悄去掉这些条件、扩大资料范围。与 T011-R1 复现一致（结果快照正确、控件被清、再次搜索放宽）。

## 修复（仅 search.html）

1. **后台状态刷新不再触碰控件**：`filter_options` 与上次相同时（`lastFilterOptionsJson` 比对）不重建下拉。搜索成功后的状态刷新、以及搜索等待期间用户新编辑的条件都不会被改动。
2. **重建时保留仍有效选择**：确需重建时（首次加载或选项实际变化），`fillSelect` 读取并还原当前选择；仍有效的值原样保留。
3. **选项消失不无提示取消约束**：当前选择已不在选项集合时，把它保留为“XXX（已不在当前选项）”选项项（真实 DOM 下 select 才能持有该值），并在状态区明确提示“仍按该条件筛选（仅手动更改或清除条件会取消）”。下一次请求仍携带该条件。
4. 结果快照继续绑定提交时条件（响应回显），错误重试继续沿用原提交 mode/query/filters——行为不变，未改动。

## 行为回归（scripts/check-search-behavior.cjs）

- **Test 9（R1 指定因果链）**：选中校区/年级/日期 → 成功搜索（并记录请求条件）→ 等待成功路径触发的 status 刷新完成 → 断言四个控件均保留（含搜索等待期间编辑的学生类型）→ 不碰控件再次搜索 → 断言请求仍携带原条件。stub 的 status 响应包含可选值（成都校区/都江堰校区、全日制本科、2024/2025），选中值均在选项内。该回归不只检查旧结果快照。
- **Test 10（选项消失分支）**：选中 2024 → 搜索期间选项变为仅 2025 → status 刷新后控件仍为 2024 且以选项项形式保留，状态区出现“已不在当前语料选项”提示 → 再次搜索请求仍带 admission_year=2024。
- 旧 12 个场景断言全部保留。

## 真实验证（本轮只跑 JS 语法与行为检查）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node scripts/check-js-syntax.cjs` | preview.html / search.html syntax OK，2 files passed | 0 |
| `node scripts/check-search-behavior.cjs` | **14 scenarios passed** | 0 |
| 负向对照（临时退回旧逻辑：总是重建 + 总是清空） | `FAIL: campus survives status refresh`（`'' !== '成都校区'`） | 1 |
| 还原修复后重跑上述两项 | 14 scenarios passed，语法 2 files passed | 0 / 0 |

负向对照说明新回归确实守住 R1 的因果链：旧逻辑下在“状态刷新后控件保留”处失败，修复后通过。对照代码为临时内存级改动，已完整还原并复跑确认（最终代码即当前 search.html）。

## 证据层级与未验证项

- 行为脚本为 DOM/fetch stub 级证据，不是真实浏览器。按 R1“无浏览器工具可如实交 Astra 补验”：真实浏览器的“筛选→搜索→原文→清除条件”及一次错误重试请 Astra 补验。错误重试沿用原参数的行为在 stub 级 Test 3/4/9 已覆盖。
- 未改后端，无需补后端检查；revision 1 的全量 404 项 pytest、pip check、模型演示与三模式评测证据仍有效（见 `verification.rev1.md` 与 T011-R1 的独立复核），按返工单未重复。

## 本修订文件

- 修改：`step2_code/backend/src/campus_assistant/static/search.html`、`step2_code/backend/scripts/check-search-behavior.cjs`
- 提交记录：`report.rev1.md`、`verification.rev1.md`、`submission.rev1.json`、`changed-files.rev1.json` 为 revision 1 历史副本；当前 `report.md`/`verification.md`/`submission.json`/`changed-files.json` 为 revision 2；本文件为新增。
