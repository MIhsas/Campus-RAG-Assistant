# T043 意见落档与未知学生类型正式准入 — 实施报告（report.md，submission_revision=2，responds_to=T043-R1）

身份：task_id=T043、task_revision=v1、**submission_revision=2、responds_to=T043-R1、status=ready_for_review**、**external_model_calls=0**、planner_live_verified=false。
revision 1 已由 Astra 核对：意见落档、后端参考准入、实发证据/消息、真实浏览器参考链路**通过并保持**（7+137 Python、34 项审计沿用不重跑）。本轮仅 **P1 前台导航上下文快照** 定向返工，详见 [fix-report.md](./fix-report.md)。revision 1 八件已归档 `rev1/`；零模型调用、不读密钥。

## 1. 本轮修复（两条因果链同修）

- **A. URL 恢复后二次跨页丢失**：修复前导航链接仅在提交后重建且取 `lastSubmitted*`——严格搜索→问答恢复正确，但不重新提交直接返回搜索时链接仍静态、问题/条件/开关全丢（开关默认回 true）；search 反向接收同样缺陷。
- **B. 历史导航误用最近模式**：旧 strict 历史显示正确但「证据搜索」仍带最近 reference 请求的开关。

**修复**：引入独立 **navContext（当前显示上下文快照）**——URL 恢复（含等待目录/选项）、提交结果、历史查看三处各自绑定并即时重建跨页链接；**旧历史缺模式字段=当时 strict（false）**；查看历史零请求、不重执行历史；控件编辑不改写旧结果导航；`lastSubmitted*` 原语义保持（重试/失败转摘录不受影响）；指定文件失效保留、目录延迟保护、候选绑定结果、默认 reference 不变。

## 2. 验证摘要（详见 verification.md）

两页行为检查 **24/41 场景 exit 0**（含真实 checkbox 桩与新链：两方向 URL 恢复免提交跨页、旧 strict 历史导航 strict、改控件不改快照、提交/重试/转摘录/候选参数）；9 页 JS 语法 exit 0；**Astra 导航探针原样运行 11/11、exit 0**（修复前 3 失败；原失败记录保全 `9374947e…`，探针与标准未改）。无真实浏览器——请 Astra 补验；不代签浏览器或人工政策认证。

## 3. 意见与边界（保持）

用户 8 项确认、旧 109/3/2、模板 33 分域保持；u04/u03 两决定实施不变（后端未改）；正式 search/ask 默认 true、底层默认 strict 为授权设计未动。非阻断：`confirmed_count` 语义限定为「按已提交条件准入（未选择类型不表示类型已核实）」，计数语义后续统一。不改 gold/冻结/指标/原意见/casebook/模型输出；旧授权结束、不 live。

完成后停止，等待 Astra 验收；不推进 T044。
