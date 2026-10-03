# T018-R1 定向返工报告（submission_revision=2）

日期：2026-09-27。responds_to=T018-R1。task_revision 保持 v1、status=ready_for_review、**external_model_calls=0**。仅修复条件恢复/事项预选因果链与测试桩、校正说明；保留 T016-R1/T018 的结果与历史快照语义，未改 ask 与后端。

## P1-1 修复：条件恢复兼容真实 DOM 集合

**根因**（`static/procedures.html` setSelectValue）：对 `sel.children` 直接 `forEach`——真实 DOM 的 children 是 HTMLCollection（无 forEach），任意非空下拉条件进入即抛异常，被 loadStatus 的 catch 静默吞掉；且 `importFiltersDone` 在成功前已置 true，恢复不再重试。

**修复**：改用索引遍历（`for (i < sel.children.length)`，HTMLCollection/数组通用）；`applyImportFiltersOnce` 用 try/catch 包裹恢复，**完整恢复成功后才置 importFiltersDone**，失败时提示“带入条件恢复失败，请手动设置条件（原条件未被取消）”且不放宽任何条件。缺失选项保留（ghost 选项 + “已保留该条件”提示）语义不变。

## P1-2 修复：事项预选不依赖测试桩属性

**根因**（applyImportProcedureOnce）：调用 `c.listeners.click`——listeners 是测试桩自定义属性，真实 DOM 不存在；found 仍置 true，事项既未选中也无异常提示，selectedProcedureId 为 null 导致 doDraft 直接返回。

**修复**：抽出公共 `selectProcedure(procedureId)`（设置 selectedProcedureId + selected 类），**卡片点击与 URL 恢复共用**；applyImportProcedureOnce 仅预选卡片（成功才标记完成，失败提示“不存在于当前清单”），不自动草稿/保存/调模型。产品代码不再出现桩内部属性。

## 测试桩校正与因果链回归

- `check-procedures-behavior.cjs` 桩升级（T018-R1 要求）：`children` 改为 **HTMLCollection 形态**（length+索引+item，无 forEach/map——数组专有方法依赖会立即暴露）；事件存入**桩外 WeakMap**，元素无公开 `listeners`，测试经 `trigger(el, name)` 触发。44 处测试调用点转换（一次正则转换截断含连字符 id 的接收者，已按模式逐一修复并核对全部 31 处剩余调用形态正确）。
- 因果链回归（并入既有导入场景）：带入 `proc-review-grade` + `admission_year=2023` → 选项加载后条件恢复、事项卡 `selected` 类生效、**加载本身零 draft 请求零存储写入**；显式点击“生成办理步骤草稿”后请求为 `proc-review-grade/draft` 且 `filters.admission_year=2023`；缺失选项场景保留（值保留 + 提示）。该场景在修复前的页面代码下会被严格桩抓住（children.forEach 抛异常→条件未恢复；无 listeners→未预选）。

## 说明校正（非阻断项）

1. **模拟生成器隔离表述**：demo-campus.py 与测试均改为“演示 app 显式使用 mock、不向真实服务发请求”；源码字符串检查重命名为 `test_demo_entry_source_uses_mock_only` 并注明**不是运行时隔离证明**（导入链可能构造默认 app——本轮不重构入口）。
2. **首页说明**：home.html 的绝对描述限定为 demo-campus 启动方式（“以 demo-campus.py 启动时为…；普通服务以状态栏实时信息为准”），T014 历史证据表述不变。

## 验证（真实命令见 verification.md）

- JS 语法 6 页通过；`check-procedures-behavior.cjs` **11 场景**通过（含强化因果链）。
- `tests/test_demo_campus.py` 5 passed（改名用例仍绿；按相关性仅跑此一件）。
- 未重复 ask/后端/全量测试；零外部调用；无浏览器能力——真实浏览器复验留待 Astra（rev1 的带参页面复现路径 `/procedures?procedure_id=proc-review-grade&query=成绩复核&admission_year=2023` 应可见条件恢复、预选与手动生成）。

## 历史与文件

- revision 1 历史副本：`report.rev1.md`、`verification.rev1.md`、`submission.rev1.json`、`changed-files.rev1.json`。
- 本修订修改：`static/procedures.html`、`scripts/check-procedures-behavior.cjs`、`scripts/demo-campus.py`（说明）、`static/home.html`（说明）、`tests/test_demo_campus.py`（改名+注释）；清单见 `changed-files.json`。

完成后停止，等待 Astra 验收。T019 未发布。
