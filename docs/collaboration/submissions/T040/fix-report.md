# T040-R2 修复报告（fix-report.md，submission_revision=3）

身份：task_id=T040、task_revision=B-v1、submission_revision=3、responds_to=**T040-R2**、stage=B_not_started、status=partial、external_model_calls=0、live_verified=false、planner_live_verified=false。
范围：仅修 [T040-R2](../../reviews/T040-R2.md) 两项因果链 + 同批整理；修改面=`live-smoke-real-qa.py`、`test_live_smoke_real_qa.py`、T040 提交材料。**不执行 --live、不发真实请求**；A/产品/gold/冻结/语料/模板/用户意见/Astra 文件未改。

## 必修1：输出目录前置门（P1）——根因与修复

**根因**：`run_b()` 在 `execute_live_loop()` 之后才调用 `write_outputs()` 检查非空目录。默认目录已有 run-1 时配置密钥重跑，会先执行 4 次生成再拒绝覆盖，消耗预算却无审计（探针实证 mock post=4 后才报错）。

**修复**：`run_b()` 起始处（任何生成/发送之前）检查并准备本轮输出目录——**已有非空目录立即 raise 非零退出、零 post**；目录缺失则创建以保证“无可用输出路径不开始付费调用”；最终写入时的防覆盖保留（双保险）；已有输出一律不删除。live 路径另加守卫：out_dir 缺失或计数客户端未装配 → 拒绝开始付费调用、零发送。**未来真实恢复必须使用新的明确输出目录**，不复用已有 T040-B/run-1、不删原件腾位置。

**验证**（业务链 1 + 原探针）：非空目录 + 可用 mock → `test_output_gate_refuses_before_any_send` 通过（run_b 抛 RuntimeError、fake.calls=[]、旧文件不变、未写新审计）；Astra 探针 `nonempty_output_before_send` **pass**（mock_post_calls=0、error 非空、old_file_unchanged、new_audit_written=false）。

## 必修2：实际发送计数（P2）——根因与修复

**根因**：`AttemptRecordingProvider.generate()` 入口递增，但适配器先构造 messages/headers 再 post——发送前本地异常（如 build_messages 失败）被误计为外部 1 次（探针实证 post=0 而 reported=1）。

**修复**：新增 `SendCountingClient`——**外部 HTTP 次数只在本脚本装配的客户端 post 发送处计数**（经适配器 `client` 注入参数传入，不改产品适配器、不做全局猴子补丁）：发送前检查总预算（≤4）并递增一次；**连接失败计 1**（已尝试发送）；**发送前本地异常/零证据计 0**。`AttemptRecordingProvider` 改为 provider 调用层审计（`provider_calls` 另列，不作外部次数；供应商状态仅记已观察值）。`execute_live_loop` 每题分列 `attempts`（外部发送）与 `provider_calls`；保持每题最多一次、零重试、首次技术失败即停、零证据本地短路。自定义工厂未装配计数客户端时占位拒绝发送，不谎报计数。

**验证**（业务链 2 + 原探针）：`test_presend_failure_zero_post_zero_count` 通过（build_messages 注入发送前异常 → fake.calls=[]、external=0、provider_calls=1、失败即停）；Astra 探针 `counter_matches_actual_send` **pass**（mock_post_calls=0 == reported=0）。原 4 项 mock 保持通过（连接失败计 1、HTTP 失败即停、业务不足可继续、前置拒绝零请求）。

## 同批整理（不加新矩阵）

1. **run-1 勘误（不重写原机读文件）**：run-1 的 `live-results.json` 实为 `questions={}`、`stop=null`——**并非**机器记录四条 not_attempted。正确表述=「四题均未执行（run-1 机器记录未列题目条目）」。revision 2 报告中“not_attempted×4”及 live-answers-full.json 逐题行是**事后编写的人读描述**、不是 run-1 机器记录内容——以本勘误为准；run-1 原件与 rev2 归档字节保持。**代码已修**：此后前置失败/守卫拒绝的记录一律补齐四题 `not_attempted` 条目与停止原因（含预置字段 attempts/provider_calls=0）。
2. **缺密钥表述收敛**：不再断言“本机任何位置均不存在”。正确表述=「本次执行进程环境及列明位置检查（进程环境含非沙箱、Windows User/Machine 级查询、仓库 .env）未发现可用配置；另一终端/应用进程的环境不自动共享」。Astra 本轮未读密钥未查环境，缺密钥结论来自 run-1 记录与 MiMo 报告。全程未读取/打印密钥值、全量环境、headers 或原始异常。
3. **权限分类器拒绝历史保留**：revision 2 记录的“记录刷新重跑被自动权限审查拒绝”历史保留；本轮未再触发该动作。此后若自动审查拒绝，记录具体动作与原因后停止该动作，不换工具/命令/路径规避。

## 验证执行（详见 verification.md）

`tests/test_live_smoke_real_qa.py`：**6 passed，exit 0**（4 原项 + 2 新业务链）；Astra `T040-B-preflight-probe.py` 原样运行 **exit 0**（两项 pass；旧失败记录已保全至 `rev2/T040-B-preflight-probe-failed-preserved.json`，SHA `94e3944f…`）。mock/探针仅为注入式本地证据，**不是模型质量证据**。未跑全量/UI/向量/三模式/A 原准备；零真实请求。

## 保全与边界

- revision 2 提交件归档 `rev2/`（8 件，live-results `34cbf5f9…` 与原件一致）；run-1 原件（`T040-B/live-results.json`）全程未改；rev1/ 与 A 缓存、A 四件材料未覆盖。
- 未改产品适配器/生成提示/检索筛选评分器、A 脚本/A 四件、语料/manifest、gold/冻结/results/aggregate、模板、用户意见、历史及 Astra 文件（探针输出写入为工单明确要求的例外）。
- 后续真实调用恢复条件（本轮不执行）：Astra 关闭两项代码问题；用户将 `DEEPSEEK_API_KEY` 配置到实际运行 Claude Code/Python 的进程环境（另一已运行终端的设置不自动传入；必要时从已配置环境重启执行窗口；**不让用户粘贴聊天密钥**）。原授权不变：q08→q10→u03→u04、官方端点/deepseek-flash、≤4 次真实 HTTP、每题≤1、1500/30s、零重试、技术失败即停；不额外探测、不补跑、不以模型答错为由再请求。
