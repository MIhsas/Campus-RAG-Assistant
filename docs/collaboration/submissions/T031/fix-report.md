# T031-R1 修复说明（fix-report.md，submission_revision=2）

> 范围按 [T031-R1](../../reviews/T031-R1.md)：只修 search/ask 两页恢复状态与行为测试桩，不改检索算法、后端语义、语料、T030 数据、选择映射与实验结果。验证层级如实：本轮为 JS 语法 + DOM/fetch 桩行为回归；**本环境无真实浏览器工具，未做浏览器复验，留待 Astra 复验，不代签**。

## P1-1：跨页恢复在选项加载前赋值，四条件被清掉 — 已修复

**原因**（返工单确认）：原生 select 在选项尚不存在时写 `value` 会丢值；随后 loadStatus 填充选项时保存的是空值，丢失条件进入了实际提交。

**修复**（`search.html` / `ask.html` 同构）：

- init 不再直接写任何 select；URL 参数进入独立的**待恢复快照** `restorePending`（campus/student_type/admission_year/as_of_date/document_id 原值保存）。
- 等选项就绪后**一次性应用**：filters 在 loadStatus 构建选项后由 `tryApplyRestoreFilters()` 应用；目录由 `loadSourceCatalog()` 解析后由 `tryApplyRestoreDocument()` 应用。应用只执行一次（applied 标志），后续状态刷新不覆写用户编辑（fillSelect 保留当前值）。
- 选项缺失（值已不在当前选项集）→ **保留原值**为 ghost 选项并提示「仍按该条件提交（仅手动更改或清除会取消）」，不放宽。
- 状态加载失败路径（3 处）也完成应用（值按 ghost 保留），不永久卡住提交。
- **有待恢复条件时提交被明确阻止**（提示「正在恢复…暂不提交以免丢失条件」），目录延迟期间不会以缺失条件抢先执行。
- 显式提交使用恢复后的控件值 → 请求体携带原条件（行为测试两方向验证）。

## P1-2：失效 document_id 被转换成全库检索 — 已修复

**原因**（返工单确认）：向原生 select 写入不存在的 ID 得到空值，`currentDocumentId()` 把空值转为 null → 前端未发送原 ID，后端 422 被绕开，静默全库检索。

**修复**：

- **原始待恢复 ID 保留**：`restorePending.documentId` 保存 URL 原值；目录确认后若 ID 不在目录（或目录加载失败/未确认），以 `addSelectValue` 将**原始 ID** 作为明确不可用选项保留（标注「已失效/不在当前目录」或「目录未确认」），控件值=原 ID。
- 提交携带**原 ID** → 服务端明确 422（SOURCE_DOCUMENT_NOT_FOUND），绝不转 null 执行全库。行为测试断言 `body.document_id === 'unavailable-review-file'` 且 422 message 在结果区展示。
- **只有用户显式选择「全部资料」**（切换模式或清除选择）才撤销指定条件。
- 「指定文件」模式未选文件 → **明确阻止提交**并提示「请选择文件，或显式切换回『全部资料』；不会自动按全部资料执行」。
- 提示文案区分三种状态：目录确认在内 / 已失效（保留+提交携带原 ID 由服务端校验）/ 目录未确认（同左）。
- 附带修复：ask 页 `!r.ok` 分支原先只显示「接口错误：HTTP 422」不展示服务端 message——已统一解析展示（422 原因可见）。

## 测试桩符合原生 select 语义（返工单第 3 条）

`check-search-behavior.cjs` / `check-ask-behavior.cjs` 新增 `SelectElement`：**对不存在的 option 赋 value 会得到 ''**（真实 `<select>` 语义），`innerHTML` 清空同时重置选中值；`makeSelect` 按静态 HTML 预置初始选项（source-mode=all/doc 等）。两页根因（早写丢值、写不存在 ID 得空值）在桩中可复现，不是给宽松桩加通过断言。

## 两条因果链覆盖（返工单第 3 条，两脚本各 4 场景）

| 链 | 覆盖 |
|---|---|
| A 携带 student_type=本科 + 有效文件跨页 | search→ask 与 ask→search **两方向**：选项就绪后控件保留两条件；**显式提交仍携带原条件**（`filters.student_type==='本科'` 且 `document_id==='doc-2023'`）；结果快照显示条件与来源 |
| B 失效 document_id URL | 控件保留原 ID（ghost）+ 失效提示；提交 `document_id==='unavailable-review-file'`（**绝不是 null/undefined**）；422 message 展示 |
| C 目录延迟期间提交 | 恢复未完成时**不发请求**（提示暂不提交）；目录就绪后提交携带两条件 |
| D 指定文件模式未选文件 | 阻止提交 + 提示完成选择或显式切回；显式切回「全部资料」后正常提交且不带 document_id |

## 真实验证记录（2026-10-07，Git Bash）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node scripts/check-js-syntax.cjs` | 9 个 HTML 内联 JS 全过 | 0 |
| `node scripts/check-search-behavior.cjs` | **21 scenarios passed**（17 既有 + 4 R1 链） | 0 |
| `node scripts/check-ask-behavior.cjs` | **33 scenarios passed**（29 既有 + 4 R1 链） | 0 |

- 未重跑：向量实验（experiment.json/freeze/selection-map 未改）、全量 pytest、ASR、Agent、外部模型调用。按返工单允许范围执行。
- 既有场景在原生 select 语义桩下全部保持通过（选项存在时赋值语义不变）。
- **无真实浏览器工具**：返工单两条失败链的浏览器复验留待 Astra（demo-notes 检查表仍适用；第 8 项已按本轮事实修正——未启用生成器时生成按钮禁用，该因果链由行为测试覆盖，本地模拟路径为既有 `scripts/demo-deepseek-mock.py`）。

## 交付物变更

- 新增：本 fix-report.md。
- 更新：`submission.json`（revision=2、responds_to=T031-R1）、`changed-files.json`、`report.md`、`verification.md`、`demo-notes.md`（第 8 项前提修正）、`continuation-progress.md`。
- revision 1 九件原字节归档于 `submissions/T031/rev1/`（SHA-256 核验 9/9 一致）。
- 页面文件：`static/search.html`、`static/ask.html`（恢复状态机 + 422 message 展示）；行为脚本两件（原生 select 桩 + R1 场景）。后端 Python、实验数据、T030 数据未改。
