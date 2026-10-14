# T040 真实资料限定生成冒烟 — 实施报告（report.md，submission_revision=3，responds_to=T040-R2）

身份：task_id=T040、task_revision=B-v1、**submission_revision=3、responds_to=T040-R2、stage=B_not_started、status=partial**、**external_model_calls=0**、live_verified=false、planner_live_verified=false。
用户原四题授权仍有效、预算未消耗（真实外部次数 0）；本轮为本地定向返工，**不执行 --live、不发真实请求**。A 阶段与 revision 2 证据分层不混；详见 [fix-report.md](./fix-report.md)（两处根因/修复/验证）。

## 1. 当前事实状态

- **B 仍未开始**：run-1 因缺密钥被前置拒绝，真实外部次数 0。**勘误**（原机读文件不改）：run-1 的 `live-results.json` 为 `questions={}`、`stop=null`——是「四题均未执行、机器记录未列题目条目」，而非四条 not_attempted 记录；revision 2 报告曾写“not_attempted×4”、live-answers-full.json 逐题行均为事后人读描述，以本勘误为准。此后前置拒绝记录将补齐四题状态与停止原因（代码已修）。
- **缺密钥表述收敛**：本次执行进程环境及列明位置检查（进程环境含非沙箱、Windows User/Machine 级查询、仓库 .env）**未发现可用配置**；另一终端/应用进程环境不自动共享。不作全位置绝对断言；全程未读取/打印密钥值、全量环境、headers 或原始异常。
- A 身份保持（revision 2 前置核对通过：材料/输入 SHA 未漂移、四题 E/messages 与 A 一致）；run-1/A 四件/rev1 均字节保持。

## 2. 本轮返工（T040-R2 两项必修，已修并验证）

- **必修1 输出目录前置门**：`run_b()` 任何生成/发送之前检查并准备输出目录——非空立即拒绝（零 post）；最终防覆盖保留；已有输出不删除；无可用输出路径不开始付费调用；恢复真实执行必须用新的明确目录（不复用 T040-B/run-1）。
- **必修2 实际发送计数**：外部 HTTP 次数只在本脚本装配的计数客户端 **post 发送处**计数（经适配器 client 注入，不改产品适配器/不打全局补丁）：发送前查预算（≤4）递增一次、连接失败计 1、发送前本地异常/零证据计 0；provider 调用数另列；每题最多一次、零重试、失败即停语义保持。
- **验证**：6 项测试通过（4 原 + 2 新业务链），exit 0；Astra 原探针原样运行 **exit 0**（两链 pass）。mock/探针为注入式本地证据，**不是模型质量证据**。详见 [verification.md](./verification.md)。

## 3. 未来真实调用恢复条件（本轮不执行）

① Astra 关闭两项代码问题；② 用户将 `DEEPSEEK_API_KEY` 配置到**实际运行 Claude Code/Python 的进程环境**（另一已运行终端的设置不自动传入；必要时从已配置环境重启执行窗口；不让用户粘贴聊天密钥）。原授权固定：q08→q10→u03→u04、官方端点/deepseek-flash、≤4 次真实 HTTP、每题≤1、1500 输出 token/30s、零重试、技术失败即停；不额外探测、不补跑、不以模型答错为由再请求。四题支持性核对框架（q10 两前提/u03 已核实来源/q08 缺口合理不足/u04 不推测）见 live-review-notes.md，无评价对象。

## 验证摘要

6 passed（exit 0）；探针 exit 0；revision 2 提交与 run-1 归档字节核验一致（rev2/live-results `34cbf5f9…` == 原件）；产品/适配器/提示/gold/冻结/语料/模板/用户意见/Astra 文件未改；零 commit/push、无下载安装。**真实生成质量、四题支持性、学校现行有效性均未验证；live_verified=false、planner_live_verified=false。**

完成后停止，等待 Astra 验收；不运行 live、不推进 T041。
