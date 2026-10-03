# T026 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。按任务书仅本地回放、loopback mock 与受影响聚焦回归；**零外部模型调用、未执行 live、无下载、无安装**；未改 UI 不跑页面；未跑全量/ASR/embedding。

## 1. 离线回放（loopback mock 明确标记，真实运行）

```bash
./.venv/Scripts/python.exe scripts/t026-offline-replay.py --out "F:/Collage Paper/docs/collaboration/submissions/T026/offline-replay.json"
# run1: partial/failed_actions (bad_rejected=True)
# run2: completed/finished tools=2
# decl_ok=True obs_consistent=True exit_ok=True
# 退出码：0
```

对照任务「最小验证」清单（详见 `offline-replay.json`）：

- **出站声明不含模型可写 filters/事项**：检查来源是 **mock 捕获的真实出站请求 payload**（第 1 次请求 system 消息）——参数条目无 `    - filters`/`    - procedure_id`；`build_checklist_draft` 标注「（无参数；范围条件与已选事项由服务端固定注入）」；含正确 JSON call 示例（args 省略固定条件/事项）与「本次可用检索模式」行。
- **执行结果严格按 2023 快照**：run1 的 `snapshot.filters` 保持 `{admission_year: 2023}`；草稿与本地 `build_draft` 直接结果**全对象相等**（draft_matches_direct_service=true）。
- **T025 首轮坏动作仍被拒**：回放动作原样 `{"tool":"search_policy","args":{"query":"缓考","filters":{"年级":"2023"}}}` → `tool_rejected`（业务前拒，「不得放宽或改写」），不为全绿放松条件锁；finish 后 status=partial/failed_actions 如实（不伪装 completed）。
- **同一服务下一次独立运行正常完成**：run2 completed、tools=2、草稿对照一致（同一适配器实例与同一 mock 服务）。
- **观察截断透明**：真实草稿待核实 **4** 项、观察只列 3 → `pending_items_total=4 / listed=3 / truncated=true`；完整草稿仍 4 项；issues/evidence 同口径（total/listed/truncated）。

## 2. 聚焦回归（62 项，真实运行）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_agent_workflow.py tests/test_deepseek_planner.py tests/test_live_smoke_planner.py -q -p no:cacheprovider --basetemp .cache/t026 --tb=short -rs
# 62 passed, 2 warnings in 17.96s
# 退出码：0
```

- 新增：声明排除固定参数（出站 payload 断言）、越权 filters/procedure_id 明确拒绝（含与快照一致也不得传）、坏动作回放仍拒 + 二次独立运行 completed、待核实 4/3/截断、证据截断口径。
- 更新：`test_matching_filters_accepted` → 改为 `test_matching_filters_also_rejected_no_silent_execute` + `test_omitted_filters_uses_snapshot_scope`（T026 语义）。
- **零回归**：T024 既有断言短语（「不得放宽或改写」「不得擅自更换事项」）与 smoke CLI 三类验证保持全过（越权拒绝文案保留原短语）。完成判定（`_finish_verdict`）未改，既有完成语义断言不变。

## 3. 依赖

未安装依赖、未下载模型、requirements 未改。无需 pip check。

## 4. 未验证项

1. **真实模型未再调用**（T025 B 授权已结束）：参数收敛/观察透明化的改进**未经真实模型验证**，不宣称错误率降低或真实效果改善（mock 正常结果不外推）。
2. planner_live_verified=false 保持；完整无失败真实冒烟仍未通过（见 T025-evidence-errata.md）。
3. 真实学校语料不在本轮范围。
