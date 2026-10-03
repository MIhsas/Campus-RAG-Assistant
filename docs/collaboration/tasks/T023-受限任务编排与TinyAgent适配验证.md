# T023 受限任务编排与TinyAgent适配验证

日期：2026-09-27；task_revision=v1。Astra发布，MiMo v2.6 Pro执行；前置T022-R1通过。

## 目标与证据边界

把既有“查政策+办理草稿”接成一个受限工具流程，开始落实docs/04的Agent可替换层。先证明工具共享、参数约束、有限执行和结果可见；本轮不新增远端推理调用，不宣称自然语言规划效果已验证。

候选TinyAgent明确为Datawhale tiny-universe/content/TinyAgent，不要误用其他同名仓库或本机其他项目。Astra已核对官方Agent.py及LLM.py：示例采用ReAct，示例模型类依赖本地InternLM并调用CUDA；不能直接据此声称Windows CPU+DeepSeek已兼容。

官方入口：https://github.com/datawhalechina/tiny-universe
代码：https://github.com/datawhalechina/tiny-universe/blob/main/content/TinyAgent/tinyAgent/Agent.py
模型层：https://github.com/datawhalechina/tiny-universe/blob/main/content/TinyAgent/tinyAgent/LLM.py

## 实施

1. 获取与审阅上述候选的最小代码快照，记录commit/文件哈希、来源、许可及实际复用范围；不运行原仓库示例、不下载InternLM或开启其默认工具。给出简短适配结论：直接可复用哪些接口、必须替换哪些耦合。若最终只有参考其思路，就明确“参考TinyAgent，自研受限编排”；只有实际运行了适配代码才写“已集成”，禁止将预留接口说成完成。
2. 定义可替换Planner/AgentAdapter与工具注册表，本轮只开放 search_policy 和 build_checklist_draft 两个只读工具。工具直接调用已有service，复用mode/filters/证据核查，不HTTP自调、不复制业务、不调generated问答。范围条件来自用户明确提交的快照，规划器不能放宽。办事ID必须来自当前已配置事项列表；不向规划器暴露保存/删除待办、Shell、eval、任意URL、文件读取或学校登录能力。
3. 固定工作流与模拟规划器共用工具：固定流程明确选事项→检索→草稿；模拟规划器显式注入，用脚本化动作证明调用循环与结果回传，并全程标“模拟规划，非DeepSeek实时规划”。普通服务默认关闭Agent模式；固定流程不应被伪称LLM Agent。不要新写一套真实DeepSeek规划接口，本轮只设计后续连接契约。
4. 运行预算沿用方案上限：最多4轮规划、6次工具执行；无进展重复动作及时停止，未知工具/不合法参数在调用业务前拒绝。记录实际工具名、状态与次数，不输出模型Thought/隐藏推理。总时限使用单调时钟检查，不谎称线程超时即取消底层计算；本轮工具无远端模型调用，明确正在执行的同步工具能否取消。部分成功保留结果并说明未完成部分；缺必要事项或条件返回awaiting_input/表单提示，不能瞎猜或一直挂起等人。
5. 提供轻量工作流页/API或嵌入既有办事页，让用户看到“查找依据→整理草稿”的实际步骤状态和结果引用；不造假进度。草稿仍需用户进入既有办理页核对并手动保存，不自动写localStorage；链接保留用户条件。模拟规划仅在显式演示入口启用。没配置工具所需模板时给出清楚回退入口。
6. 随手校正T022-R1非阻断文案与入口：相关事项依当前配置、生成器开启说明、索引未就绪及接口状态读取失败的表达。

## 验证（聚焦，不做大矩阵）

一次正常“检索→缓考草稿”，对照直接service结果及引用；模拟未知工具/循环停止；条件未被放宽；缺模板/缺必要输入明确回退；加载与运行均不自动保存待办、不调用真实模型。测试用本地显式模拟规划器，报告工具调用次数与事件，不当作真实模型质量。受影响旧页面只跑必要回归，不跑全量、ASR、embedding评测。

允许网络读取官方仓库和下载小型源码快照；不新增模型下载、付费调用、系统服务或全局依赖。允许改新编排模块、工具适配层/API/页面、必要工厂显式开关、demo及测试README；不改旧语料/gold和既有service判断算法，不修改Astra文档。避免为集成教程增加大型框架。

## 交付与停止

docs/collaboration/submissions/T023/：report.md、verification.md、submission.json、changed-files.json、demo-notes.md，另附tinyagent-assessment.md（来源/许可/适配决策）与本地调用轨迹。记录tinyagent_integration_kind（reference/adapted等，含解释）、planner_live_verified=false、external_model_calls=0。

task_id=T023、task_revision=v1、submission_revision=1、status=ready_for_review。工作流与模拟验证完成不等于真实Agent接入完成。交付后停止，等待Astra验收，不推进T024。
