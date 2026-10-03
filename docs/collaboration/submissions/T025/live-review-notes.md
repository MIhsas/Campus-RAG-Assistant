# T025 B 真实冒烟 — 逐条核对记录（live-review-notes.md）

身份：stage=B_executed、submission_revision=3、external_model_calls=**4**（实际发送数，见下）、planner_live_verified=**false**（留待 Astra 依据真实证据认定，不以退出码自改）。

执行：2026-09-28，按 T025-R2 固定范围**执行一次**（用户授权：固定合成题「查找缓考依据并整理办理草稿」/proc-apply-defer/年级 2023、官方 `https://api.deepseek.com`、`deepseek-flash`、≤4 次 HTTP、max_tokens=300、零重试）。命令（实跑，退出码 1）：

```powershell
# env.local 静默载入执行进程（不打印内容）+ 进程级 NO_PROXY=api.deepseek.com（既往已知 TLS 经验，未改系统代理）
& .\.venv\Scripts\python.exe scripts\live-smoke-planner.py --mode live --out 'F:\Collage Paper\docs\collaboration\submissions\T025\live-run.json'
# LIVE_EXIT=1
```

未发任何额外探测请求；未启用答案生成器；失败/未达 completed **未自动修复后重跑**；失败历史原样保留于 `live-run.json` 事件流。

## 1. 运行结论（服务端判定，T024-R1 口径）

| 项 | 实测值 |
|---|---|
| status / stop_reason | **partial / failed_actions** |
| 服务端文案 | 「必要产物已生成，但期间有失败/被拒动作，未全部完成。完成仅指生成可核对结果，不代表学校审批、办事已办妥或待办已保存。」 |
| 规划轮次 / 工具执行 | 4 轮 / 2 次工具 |
| **真实 HTTP（发送处计数）** | **4 = 循环计数 4**（4 个 URL 均为 `https://api.deepseek.com/chat/completions`），零重试，恰达 ≤4 预算上限 |
| 模型结束语 | 仅记录（planner_summary / 事件「不作结论」），不作主结论 |

**为何是 partial 而非 completed**：第 1 轮模型传入自造 filters（`{"年级": "2023"}`，改写/非快照条件）被范围锁**业务前拒绝**——按完成判定原则「期间有失败/被拒动作」不得标 completed。失败历史不清理、不补工具凑成功。

## 2. 实际动作与观察（逐轮，源自 live-run.json 事件流）

| 轮 | 动作 | 结果 | 观察/说明 |
|---|---|---|---|
| 1 | call search_policy（args 含自造 filters） | **rejected** | 「范围条件以用户提交的快照为准，不得放宽或改写」——业务未被调用；原条件未丢 |
| 2 | call search_policy | ok | **命中 3 条**（真实检索，BM25 合成语料） |
| 3 | build_checklist_draft（proc-apply-defer，与快照一致） | ok | 草稿 saveable=True，4 步骤（d1—d3 ok、d4 degraded） |
| 4 | finish | ok | 结束语仅记录 |

## 3. 逐条核对（程序化核对 vs 人工核对分开）

**程序化核对**（脚本按实际结果生成，与直接 service/快照对照）：

| # | 核对项 | 实测 | 通过 |
|---|---|---|---|
| 1 | 是否实际搜索 | search_policy 成功 1 次，命中 3 条 | ✓ |
| 2 | 草稿存在且事项/条件正确 | 草稿存在，procedure_id=proc-apply-defer，快照条件=年级 2023（**未被第 1 轮改写**） | ✓ |
| 3 | 引用与直接 service 相同 | 草稿引用 4 条，与本地 `build_draft` 直接结果逐条一致 | ✓ |
| 4 | 人工核实需求如实标注 | saveable=True，未明确事项 4 项，未通过引用 1 条——已如实标注（**程序化摘要，非人工核对结论**） | ✓ |
| 5 | 无失败/提前 finish | status=partial，失败/被拒事件 1 条（第 1 轮 filters 被拒） | **✗（如实记录）** |
| 6 | 零自动保存 | 静态实现判断：脚本仅写 --out 运行记录 | ✓ |

**人工核对（留待用户/答辩实际执行，不由脚本代核）**：

1. 草稿 4 步骤内容与合成原文的语义核对（d4 为 degraded：2024-only 可选引用未通过，该项信息为「资料未说明，请向办理部门核实」）。
2. 4 项「未明确事项」（unspecified）是否需要在真实办事中另行向办理部门确认。
3. 第 1 轮模型改写 filters 的行为是否需要在后续提示词/适配层进一步收紧（当前由范围锁在业务前拦截，条件未放宽——这是防线生效，不是漏洞，但模型意图可在后续迭代关注）。

## 4. 完整审计（每轮 provider 字段，真实响应；缺失字段 null，无缺失）

| 轮 | request_id | model | usage（prompt/completion/total） | finish_reason | latency_ms | max_tokens |
|---|---|---|---|---|---|---|
| 1 | 35868575-fe9b-4757-b542-f9f98f6666ec | deepseek-flash | 630 / 36 / 666 | stop | 765 | 300 |
| 2 | 29a920b9-f06b-433c-a5a5-b47fff120f73 | deepseek-flash | 679 / 27 / 706 | stop | 421 | 300 |
| 3 | 45c09a26-fe89-4ed5-b2f4-a69b6ea9d2cd | deepseek-flash | 947 / 31 / 978 | stop | 844 | 300 |
| 4 | 1381357b-dcc9-49ff-930d-ba8850240dc2 | deepseek-flash | 1040 / 84 / 1124 | stop | 796 | 300 |

- 合计 4 次规划 HTTP（= 发送处计数 = 服务端应答数）；无重试；无失败轮审计丢失（本轮无技术失败，各轮审计完整）。
- **密钥零落盘**：live-run.json 仅 `key_present: true`；无 Authorization/密钥值（交付前断言核对）。
- 费用口径如实：max_tokens=300 仅约束输出（4 轮 completion 36/27/31/84 tokens），输入同样计费（prompt 630→1040 递增）；本记录不折算金额。

## 5. 结论与边界

- **本次是真实 DeepSeek（deepseek-flash）结构化规划的首次联调证据**：4 轮结构化动作往返成功、观察驱动第二轮决策（第 2 轮提示含第 1 轮真实结果）、条件锁/事项锁生效、预算/零重试/发送处计数成立、T024-R1 产物判定如实（partial 而非伪装 completed）。
- **planner_live_verified 留待 Astra 认定**（本记录不自改）。退出码 1 是核对表第 5 行如实失败与 partial 判定的正常结果，不代表联调通道失败。
- 合成语料（全部 is_synthetic=true）+ 合成模板——**不代表学校真实政策与真实办事效果**。
- B 授权仅此一次，已执行完毕；不自动再跑、不改模型/端点/预算凑成功。
