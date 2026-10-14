# T043-R1 修复报告（fix-report.md，submission_revision=2）

身份：task_id=T043、task_revision=v1、submission_revision=2、**responds_to=T043-R1**、status=ready_for_review、external_model_calls=0、planner_live_verified=false。
范围：**仅前台导航上下文快照**（search.html/ask.html、两份 check-*-behavior.cjs、T043 提交材料）。后端/意见落档/两决定实施保持（Astra 已核对通过，不重跑）；零模型调用、不读密钥。

## 必修 P1：导航未使用当前显示上下文的完整快照（两条因果链，同修）

**根因**：两页 `updateNavLinks()` 仅以 `lastSubmitted*` 为源、且仅在 `doSearch`/`doAsk` 完成后执行——①URL 恢复只回填控件、不建立导航上下文（`lastSubmittedIncludeUnknown` 仍初值 true），未提交就跨页时链接保持静态、问题/条件/开关全丢；②历史查看（renderHistory→renderResult）不绑定该条自己的快照，导航仍取最近请求的模式。

**修复（最小方式）**：引入独立 **`navContext`（当前显示上下文快照）**，`updateNavLinks()` 只读它——三处各自绑定、互不干扰：
1. **URL 恢复**（含等待目录/选项期间）：init 就从入站参数建立 navContext（query/filters/document_id/include_unknown_student_type；缺模式参数=页面默认 reference），并立即重建链接——**无需提交即可原样跨页**；
2. **提交结果**：doSearch/doAsk 快照时同步 navContext（此后控件编辑不改写）；
3. **历史查看**：view 按钮把该条自身快照随 opts.nav 传入 renderResult 绑定（**缺模式字段=false（当时 strict）**），查看仍零请求、不重执行历史。

`lastSubmitted*` 语义不变——**重试/失败转摘录仍用原请求快照**，不受 navContext/控件影响。指定文件失效保留、目录延迟提交保护、候选绑定结果快照、strict 历史语义均保持；首次无参数页面仍默认 reference。

## 验证（本窗口实跑；与 Astra 既有证据分列）

| 项 | 实测 |
|---|---|
| 行为桩（真实执行两页产品 JS，DOM/fetch 桩） | check-search-behavior **24 场景 exit 0**（23+1）；check-ask-behavior **41 场景 exit 0**（40+1）。新增链：两方向 URL 恢复→**无需提交**再次跨页（query/filters/开关完整）；提交/重试/失败转摘录/候选参数按快照（改控件不吃新值）；旧 strict 历史查看→零请求+标签 strict+**导航切回历史快照**（此前误带最近 reference）。新开关为**真实 checkbox 桩**（默认 checked、真实读写），非源码字符串检查 |
| 9 页 JS 语法 | check-js-syntax **exit 0**（All 9 HTML files passed） |
| **Astra 导航探针（原样运行）** | `& 'D:\nodejs\node.exe' docs\collaboration/reviews/T043-navigation-probe.cjs` → **11 检查全过、failures=0、exit 0**（修复前 3 失败/exit 1）。探针/通过标准未改；原失败记录先保全 `T043-navigation-probe-failed-preserved.json`（SHA `9374947e…` 与当时原件逐字节一致），运行后探针结果文件由原脚本自写（未手改） |

**Astra 既有证据（沿用，不重跑）**：revision 1 的 7+137 Python、34 项审计、真实浏览器参考准入/复制验证。本窗口**无真实浏览器**，URL 恢复跨页与历史导航修复的浏览器复验请 Astra 补验（桩级+探针已揭示并覆盖两因果链）。

## 同批非阻断整理

`confirmed_count` 语义限定（不改后端）：该字段现义为**「按已提交条件准入的文档数（未选择学生类型时不表示类型已核实）」**；「学生类型已匹配」的严格计数语义留待后续统一，本次不扩后端改造。

## 保全与边界

- revision 1 八件归档 `rev1/`（未覆盖既有历史）；原用户 8 确认、旧 109/3/2、模板 33、casebook/gold/freeze/结果/语料/模型输出只读未改。
- 不读密钥/不 live/不 commit/push/不改 Astra 工单与状态表；旧 T040 授权结束不变。
