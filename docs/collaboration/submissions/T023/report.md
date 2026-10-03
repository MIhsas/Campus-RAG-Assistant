# T023 受限任务编排与 TinyAgent 适配验证 — 实施报告

身份：task_id=T023、task_revision=v1、**submission_revision=2、responds_to=T023-R1**、status=ready_for_review、**tinyagent_integration_kind=reference、planner_live_verified=false、external_model_calls=0**（零外部模型调用；无模型下载；密钥零暴露）。rev1 已归档为 `*.rev1.*`；针对返工单的修复说明见 `fix-report.md`。

## 概述

把既有「查政策 + 办理草稿」接成受限工具流程，落实 docs/04 的 Agent 可替换层：可替换 Planner 契约 + 只读工具注册表（`search_policy` / `build_checklist_draft`）；固定工作流（选事项→检索→草稿）与显式注入的模拟规划器共用同一套工具；页面如实展示实际步骤与引用。核对 Datawhale TinyAgent 源码/许可/适配范围，结论为**仅参考、自研受限编排**。T023-R1 三处返工（规划器跨请求状态、年份放宽、失败残留旧结果）已修复，随单校正根 README 许可声明调查。

## 功能交付（对照任务书 + 返工单）

1. **TinyAgent 核查与适配结论**（`tinyagent-assessment.md` + `tinyagent-snapshot/` 含根 README）：只读拉取官方文件，记录 commit（main HEAD `a5ae08d…`）、SHA-256 与上游 blob SHA。**许可（T023-R1 校正）**：仓库根 README 第 193—197 行 LICENSE 段声明 **CC BY-NC-SA 4.0**（署名-非商业性使用-相同方式共享，注记默认 CC 4.0、子项目可另选协议）；GitHub license=null/无独立 LICENSE ≠ 无任何许可声明（rev1 绝对推断已撤回）。对 `content/TinyAgent` 具体代码的适用范围如实保留疑问，不作绝对结论。适配结论不变：无可直接复用的运行时代码（强耦合 + 许可适用存疑），仅参考「工具声明式注册 + 动作→工具→观察循环」的接口形状；模型层（InternLM2Chat + transformers + `.cuda()`）与工具层（硬编码 `google_search` + serper.dev）必须替换。**「参考 TinyAgent，自研受限编排」，不写「已集成」**；未运行其示例、未下载 InternLM、未开默认工具；不据其声称 Windows CPU+DeepSeek 已兼容。

2. **可替换编排接口**（`agent/planner.py`）：`Planner` 协议为未来 DeepSeek 适配器连接契约（仅设计）。本轮唯一实现 `ScriptedPlanner` 为**无状态**脚本规划器（T023-R1：按 `round_no` 取动作，同一实例跨请求/跨运行完全隔离），全程标注「模拟规划，非DeepSeek实时规划」。

3. **只读工具注册表**（`agent/tools.py`）：仅 `search_policy`（复用 retrieval.service）、`build_checklist_draft`（复用 procedures.service 引用核查与 saveable 门）。不 HTTP 自调、不复制业务、不触生成问答。范围条件只来自用户快照，规划器不得放宽（传异条件先拒）；事项 ID 须来自当前已配置列表。不暴露待办保存/删除、Shell、eval、任意 URL、文件读取、登录。未知工具/非法参数在调用业务前拒绝。

4. **固定流程与模拟规划器共用工具**（`agent/workflow.py`）：固定流程标签含「非大模型 Agent」；普通服务 `planner=None`（Agent 模式关）；模拟规划仅 `demo-campus.py` 显式注入。不新写真实 DeepSeek 规划接口。

5. **预算与停止**：≤4 轮 / ≤6 次工具；无进展重复停止；单调时钟时限在步骤间检查（`cancellable_note` 说明同步工具不可中途取消）；事件只记工具名/状态/次数，不输出模型 Thought；缺必要输入返回 `awaiting_input`。

6. **工作流页/API**（`static/workflow.html` + `/api/v1/agent/*`）：真实步骤与引用展示；草稿保留手动保存（链接携带**提交时条件快照**）、页内不写 localStorage；缺模板给清楚回退。**T023-R1 页面修复**：① 年份严格校验（非空非法值提示并停止提交，不截断、不静默转不限；留空=不限）；② 新请求开始即清空旧依据/草稿/办理入口，失败（422/无效 JSON/网络异常）共用清理并明确「本次未生成新结果」；③ 成功结果显示「本次提交快照」行，不依赖会变化的输入框。

7. **T022-R1 整理**（rev1 已完成）：ask 相关事项依当前配置、生成器文案显式开关、首页「语料索引就绪后可用」、状态失败显示「读取失败/未知」。

## 验证摘要（真实命令见 verification.md / fix-report.md）

- `tests/test_agent_workflow.py` **20 passed**（18 + T023-R1 隔离回归 2：同一实例/同一 client 连续两次运行均独立执行且结果属各自快照）。
- `check-workflow-behavior.cjs` **3 场景**（vm stub 层级，非真实浏览器）：年份 2023/空白/abc、2023abc；成功→422 与网络异常共用清理；快照绑定。
- JS 语法 9 页通过；本地调用轨迹 6 类运行（含同一实例两连跑）真实产出。
- 按返工单未重跑全量/ASR/embedding/真实 DeepSeek；工厂装配未改无需补 run_entry。

## 修改与新增文件（rev2 增量）

- 修改：`src/campus_assistant/agent/planner.py`（无状态化）、`src/campus_assistant/static/workflow.html`（年份校验+清理+快照行）、`tests/test_agent_workflow.py`（隔离回归 2 项）、`scripts/trace-agent-run.py`（共享实例两连跑用例）
- 新增：`scripts/check-workflow-behavior.cjs`（stub 因果链检查）
- 提交件：`fix-report.md` 新增；四件更新至 rev2；`tinyagent-assessment.md` 许可校正；`tinyagent-snapshot/root-README.md` 补存；`call-trace.json` 重生成；`changed-files.json` 更新。rev1 全部归档保留。
- 未修改：Astra 文档、旧语料/gold、既有 service 判断算法、main.py/demo-campus.py/serve-corpus.py 装配、用户本机存储。

## 已知限制

- **真实 Agent 未接入**（planner_live_verified=false）；不宣称自然语言规划效果已验证。
- **无浏览器工具**：三条修复链的交互证据为 vm stub 层级（check-workflow-behavior.cjs），**不冒充浏览器验证**，浏览器复验由 Astra 补做。
- TinyAgent 子目录代码许可适用范围疑问如实保留；不复制源码、不引依赖。
- 测试资料为合成性质，不代表真实校园效果。

完成后停止，等待 Astra 验收。T024 未发布。
