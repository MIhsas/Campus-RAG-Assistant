# T024 真实冒烟计划（仅计划，未运行）

**状态：尚未获得真实模型调用授权。本文档仅为下一步准备，本轮不执行任何外部请求。** `planner_live_verified=false` 在真实冒烟通过并经 Astra 验收前保持不变。

## 目标与范围

用官方 DeepSeek 服务对 DeepSeekPlanner 做**一次最小真实联调**，验证：结构化动作往返、观察驱动的第二轮决策、预算/零重试在真实网络下的行为。**不是**效果评测，不回答真实政策问题（语料仍为合成）。

## 资料与配置

- 语料：`examples/parse-corpus`（**合成资料**，is_synthetic=true；不代表学校真实政策）。
- 模板：`examples/procedures/procedures.json`（合成演示模板）。
- 模型：`deepseek-flash`（V4.1 Flash，官方 base URL `https://api.deepseek.com`；model 别名非固定权重版本）。
- 入口：`serve-corpus.py --planner deepseek --procedures …`；密钥仅本地环境变量（`CAMPUS_PLANNER=deepseek` + `DEEPSEEK_API_KEY`），不进任何记录。
- 运行方式：仅用户显式点击「运行 DeepSeek 规划」一次（问题：缓考申请的条件；条件：年级=2023）。

## 预算上限（与代码常量一致）

| 项 | 上限 |
|---|---|
| 规划轮次 | ≤ 4 |
| 工具执行 | ≤ 6（search_policy / build_checklist_draft） |
| 规划 HTTP | 每轮 ≤ 1 次，**零自动重试**（预期全程 ≤ 4 次） |
| 每次规划 max_tokens | 300（结构化动作 JSON） |
| 单次 HTTP 超时 | 20 秒 |
| 单调总时限 | 30 秒（超时后不再调度；在途调用不撤销） |

## 故障即停规则

- 任一规划 HTTP 技术失败（连接/超时/HTTP 非 200/非法 JSON/截断）→ **立即停止，不重试**；保留已完成部分（partial）并记录安全错误文案。
- 工具失败/被拒 → 记录事件继续预算内调度；finish 不得伪装全部成功。
- 任何情况下不降级为脚本规划器、不伪造成功。

## 验收口径（真实运行后由 Astra 判定）

1. 至少一轮真实结构化动作往返成功（动作 JSON 被正确解析并执行）。
2. 第二轮提示词确含第一轮真实观察（保存脱敏请求摘要核对）。
3. attempts 计数 = 实际 HTTP 次数（零重试成立）。
4. 审计字段（request_id/usage/finish_reason）来自真实响应，缺失写 null。
5. 全程密钥零落盘；输出与日志不含 Authorization。

## 费用口径

- 按 `deepseek-flash` **官方价目表**× 实际 token 用量计费；本计划不预估具体金额（不编造价格），实际以账单为准。
- 预期用量上限：4 次规划请求 × (提示约 1.5k + 生成 ≤300 tokens)；无生成答案调用（`--generator` 保持关闭），费用仅规划链。
- 故障即停 + 零重试保证失败场景不产生追加费用。

## 授权前置（缺一不可）

1. 用户明确授权**具体范围**（官方端点、deepseek-flash、问题 1—2 道、HTTP 次数上限、max_tokens、无重试）。
2. 本地 `CAMPUS_PLANNER=deepseek` 与 `DEEPSEEK_API_KEY` 已配置（执行进程内可见）。
3. 由用户下达执行指令后方可运行；Astra 的计划审阅**不视为**调用授权。

运行后提交：live-smoke 结果记录（真实 attempts/审计字段/脱敏轨迹）并由 Astra 认定 `planner_live_verified` 是否可改为 true——执行方不自行改判。
