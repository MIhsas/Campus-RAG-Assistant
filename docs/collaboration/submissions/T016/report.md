# T016 定向返工报告（submission_revision=2，responds_to=T016-R1）

日期：2026-09-27。task_id=T016、task_revision=v1、submission_revision=2、**status=ready_for_review、external_model_calls=0**。仅按 T016-R1 修复三项问题；其余功能与 T015 整理未动，未扩展功能、未改产品语料/gold、无外部调用。

## 修复 1（P1）：被筛除/失效引用不再作为可用办理依据显示与保存

**根因**：`service.py` 对非通过引用仍返回完整 `quote`，页面 `citeBlock` 无条件渲染 → 2023 草稿出现“需医院证明/3个工作日”；`saveDraftAsList` 存下这些 citations 且丢弃 fallback/status/unspecified。

**修复**：
- 服务端：非通过引用 `usable=false、quote=null`，仅保留状态与来源标识（document_id/block_id/跨度/标题/版本）作诊断 + 中文原因；必要引用失效的步骤 `detail` 置空（不再展示未经当前依据支持的具体办理要求）；degraded 步骤保留 `fallback=资料未说明，请向办理部门核实。` 与 unspecified 列表。
- 页面端：`citeBlock` 对非可用引用渲染“⚠ …（未作为可用办理依据，原文内容不列入清单）”+ 查看原文诊断链接，**不渲染 quote**；顶部横幅区分“全部已核对”与“可保存；N 个步骤存在待核实/未说明项……不含未准入来源的原文要求”。
- 保存端：`usableCitations()` 过滤——待办与 verify 快照只存保存时实际采用（核对通过）的引用；policy 条目补存 `basis_status/pending_note/pending_fields`，恢复后显示“待核实：…（资料未说明：…）”。

**回归证据**（pytest `test_excluded_content_never_in_draft_output` + stub 链 1）：2023 草稿→保存→刷新待办的**完整输出/渲染/存储串**均无“需医院证明/3个工作日”，保留“资料未说明/待核实”；2024 对照正常显示有效材料引用；成绩复核 2023 的失效步骤无“10个工作日内/仅查分不查卷”具体要求。本地 API 演示输出同样验证（api-demo.json 重生成）。

## 修复 2（P1）：verify 核查全部已采用引用（含可选）

**根因**：`verify_snapshot` 以 `required` 跳过可选引用 → 已提供给用户的可选依据失效仍报 unchanged。

**修复**：删除跳过逻辑——快照只含保存时实际采用的引用（未采用的可选引用不进入快照、不被当作有效依据），**逐条核查全部**；缺失/哈希/适用条件变化均报 changed 并提示复核。页面 verify 流程本就保留勾选、备注与个人步骤（不静默覆盖），未改动。

**回归证据**（pytest `test_verify_checks_adopted_optional_citations`）：2024 缓考快照（含已采用的 d4 可选引用）→ 原语料 unchanged；隔离夹具 DOCX 缺失 → changed（issues 指名“确认材料与办理时点”）；隔离夹具哈希更新 → changed（“哈希已变化”）。产品语料与 gold 未动。

## 修复 3（P2）：新草稿请求开始即令旧草稿失效

**根因**：`doDraft` 清页面但未清 `currentDraft`，请求失败后按旧 `saveable` 重新启用保存 → 可把旧条件结果写入待办。

**修复**：请求开始时 `currentDraft=null` 并禁用保存；失败横幅明示“旧草稿已失效，不可保存”；结束时仅当**当前成功取得**的草稿 saveable 才启用保存。保存动作只指向当前展示的成功草稿。

**回归证据**（stub 链 3）：成功草稿（可保存）→ 换条件再次生成 → 503 → 保存按钮保持禁用、点击为零操作、localStorage 零新增待办、横幅含“旧草稿已失效”。

## 验证（相关范围，真实命令见 verification.md）

- `tests/test_procedures.py` **14 passed**（12 原有 + 2 条 R1 因果链；原 12 项全部保持通过）。
- procedures 页面 JS 语法（4 页）+ 行为 **9 场景**（7 原有 + 链 1/链 3）。
- 本地 API 演示重生成（api-demo.json / citation-crosscheck.md），修复证据断言全过。
- **未修改 ask/search**，按返工单不重复其测试与全量 pytest。

## 历史与文件

- revision 1 历史副本保留：`report.rev1.md`、`verification.rev1.md`、`submission.rev1.json`、`changed-files.rev1.json`、`api-demo.rev1.json`、`citation-crosscheck.rev1.md`、`demo-notes.rev1.md`。
- 本修订修改：`procedures/service.py`、`static/procedures.html`、`tests/test_procedures.py`、`scripts/check-procedures-behavior.cjs`、`scripts/demo-procedures-api.py`（quote 空值兼容）；清单见 `changed-files.json`。

## 验证层级与限制

- 三条因果链的证据为 pytest（服务全输出）+ DOM/fetch/localStorage stub（页面渲染/保存/恢复）+ 本地 API 演示；**stub 不冒充真实浏览器**。Astra 上轮已真实浏览器补验准入混入问题；完整待办闭环的浏览器复验按返工单留待修复后补验（demo-notes 步骤依旧适用）。
- 合成模板原型边界不变；不宣称学校指南准确率。

完成后停止，等待 Astra 验收。T017 未发布。
