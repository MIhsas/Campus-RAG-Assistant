# T023 演示记录与步骤（受限任务编排与 TinyAgent 适配验证）

## 证据层级（先读）

| 层级 | 内容 | 性质 |
|---|---|---|
| 编排测试 | `tests/test_agent_workflow.py` 18 项 | 真实本地运行 |
| 必要回归 | `test_run_entry + test_procedures + test_agent_workflow` 41 项 | 真实本地运行 |
| 本地调用轨迹 | `call-trace.json`（4 类运行） | 脚本化模拟规划器 + 合成语料，零外部调用 |
| 页面 JS | 语法 9 页 + ask 行为 26 场景 | stub/语法级，非真实浏览器 |
| TinyAgent 快照 | `tinyagent-snapshot/` + `tinyagent-assessment.md` | 只读拉取留档，未运行其代码 |

本轮无浏览器工具：浏览器主路径留待 Astra（下表）；stub 不冒充浏览器证据。测试资料均为合成性质。

## 两种运行方式（勿混用）

| 入口 | Agent 模式 | 特征 |
|---|---|---|
| `scripts/serve-corpus.py`（正常） | **默认关闭** | 仅固定流程「选事项→查找依据→整理草稿」；`plan/run` 返回 503 |
| `scripts/demo-campus.py`（演示） | 显式注入模拟规划器 | 「模拟规划，非DeepSeek实时规划」按钮；非真实模型 |

固定流程标签恒为「固定流程（选事项→查找依据→整理草稿），非大模型 Agent」——不被伪称 LLM Agent。

## Astra 浏览器主路径检查表

| # | 操作 | 预期 |
|---|---|---|
| a 正常入口 | `serve-corpus.py --manifest … --corpus-root … --procedures examples/procedures/procedures.json` → `/workflow` | 表单可选事项/问题/条件；「运行固定流程」可用；无「运行模拟规划」按钮 |
| b 固定流程 | 选「缓考申请」+ 问题 + 年级=2023 → 运行 | 步骤显示 选事项→查找依据→整理草稿 真实状态；工具轨迹 2 次（search_policy、build_checklist_draft）；草稿带引用 |
| c 手动保存 | 草稿区「进入办理页核对并手动保存（带入本次条件）」 | 跳 `/procedures?procedure_id=…&admission_year=2023…`；保存需手动触发；本页 Network 无 localStorage 写、无自动保存请求 |
| d 缺输入 | 清空问题或事项 | 返回 `awaiting_input` + 待补充项提示，不自动猜测、不挂起 |
| e 缺模板 | 正常入口不带 `--procedures` → `/workflow` | 固定流程区显示清楚回退（改用 /search、/ask 摘录）；`workflow.run` 503 |
| f Agent 默认关 | 正常入口 → `/api/v1/agent/plan/run` | 503 `AGENT_NOT_CONFIGURED`；`/api/v1/agent/status` `agent_mode=off`、`remote_planner=false` |
| g 演示模拟规划 | `demo-campus.py` → `/workflow` | 「运行模拟规划（演示）」按钮 + 「模拟规划，非DeepSeek实时规划」标注；事件只列工具名/状态，无模型 Thought |
| h 条件不放宽 | 模拟规划内试图改条件（演示不暴露；接口层） | 工具层拒绝「不得放宽或改写」，业务未被调用 |

## 工具与边界（诚实口径）

- 只读两工具：`search_policy`、`build_checklist_draft`。**未暴露**保存/删除待办、Shell、eval、任意 URL、文件读取、学校登录、生成式问答。
- 预算：≤4 轮规划、≤6 次工具执行；重复动作 `no_progress` 停止；单调时钟时限。
- **不输出模型 Thought/隐藏推理**；事件只记工具名/状态/次数。
- **不调用真实模型**：规划器为脚本化模拟；草稿来自模板 + 语料引用核查，非生成。
- 同步本地工具不支持中途取消（`cancellable_note` 如实说明）。

## T022-R1 整理（随本任务完成）

1. ask 页相关事项依当前配置：已配置→给入口（带结果快照链接）；未配置→「本次运行未配置对应指南」，无死入口。
2. 未配置生成器文案：改「需显式 `--generator deepseek` 开启并配密钥，仅配密钥不自动启用」。
3. 首页「关键词恒可用」→「语料索引就绪后可用」。
4. 状态接口非预期失败→「读取失败/未知（HTTP x）」，不与「未配置」混同。

## 边界

- **真实 Agent 未接入**（`planner_live_verified=false`）；不称「已集成 TinyAgent」或「真实 Agent 已接入」。
- TinyAgent 参考源码仅留档 `tinyagent-snapshot/`，未进入 `src/`、未运行其示例。
- 真实学校语料、真实 DeepSeek 规划不在本轮范围。
