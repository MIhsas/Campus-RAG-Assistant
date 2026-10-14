# T040 真实资料限定生成冒烟 — 实施报告（report.md，submission_revision=4，responds_to=T040-B-恢复执行）

身份：task_id=T040、task_revision=B-v1、**submission_revision=4、responds_to=T040-B-恢复执行、stage=B_executed、status=ready_for_review**、**external_model_calls=4**、live_verified=false（待 Astra 认定）、planner_live_verified=false。
依据：T040-R3（两项本地修复验收通过）+ 恢复执行单 + 用户原四题授权（有效、预算本轮前 0/4）。本轮真实运行一次，未改代码/产品/数据；详见 [live-review-notes.md](./live-review-notes.md)（逐段核对）与 [verification.md](./verification.md)（命令与退出码）。

## 1. 执行事实（T040-B-resume-1，一次运行）

- **密钥**：当前执行进程未继承；按 2026-10-09 配置补充授权，仅读取 User 级 `DEEPSEEK_API_KEY` 一条变量装入执行 Python 的同一 PowerShell（未打印值、未查其他位置），存在性=True 后执行。
- **命令**（cwd=backend，详见 verification）：`.\.venv\Scripts\python.exe .\scripts\live-smoke-real-qa.py --live --out-dir '.\.cache\real-qa-smoke\T040-B-resume-1'`，**exit 0**。
- **前置门全部通过**：A 身份/E/messages 与 A 一致；实际 provider 配置=官方授权值（`https://api.deepseek.com/chat/completions`/deepseek-flash/max_tokens=1500/timeout=30s，取自实际只读属性）；输出目录 T040-B-resume-1 为新目录无已有输出；安全摘要先于请求输出。
- **执行结果**：q08→q10→u03→u04 各尝试 1 次、各发送 1 次；**external_http_attempts=4**（发送位点计数）、provider_calls=4、/ask 8（前置 extractive 4+generated 4）；四题全部完成（`completed_all`），无技术失败、无 not_attempted、零重试。供应商审计为已观察值：4 次 HTTP 200、finish_reason=stop、request_id/usage/latency 如实入档（prompt 1344/1379/1667/1690、completion 107/171/53/57 tokens、811—1359ms）；未测价格，max_tokens≠费用上限。

## 2. 逐题结果与核对摘要（三层分列：脚本自动记录/执行者辅助核对/用户确认）

| 题 | outcome | 摘要 | E 支持性 | gold 覆盖 | 用户确认 |
|---|---|---|---|---|---|
| q08 | business_insufficient | 模型认定摘录无「小抄」认定表述；E5「携带规定以外的物品…」属违纪而非作弊——拒答 | 拒答忠于实发 E（合理不足，可接受） | **f1 缺口保持**（2 源均未发）；不借常识兜底 | 未确认 |
| q10 | answered（3 段） | 一般 50/50、互评 40/10/50 分别表述；开题报告两级制（通过或不通过）单独记载 | P1/P2 **支持**（E1/E2 逐字）；P3 基本支持（「不纳入比例」系对「单独记载」的适度推断，留人工核对） | f1、f2 均覆盖（实发 E1/E2） | 未确认 |
| u03 | answered（1 段） | 「考试开始30分钟后考生禁止进入考场，逾时考生作缺考处理。」 | **支持**（bed3ac/ebab438f 逐字）；未从 db05e0 补信息 | f1 覆盖（已核实 2019-11-07 源） | 未确认 |
| u04 | business_insufficient | 摘录未含学籍更正办理规定，无法回答 | 拒答忠于实发 E；**未推测办理部门**、83eb 未混入 | 不足题无 gold | 未确认 |

**未按年份宣布 2016 废止**；两前提未合并；合法 E 引用≠语义正确——逐段判读与出处见 live-review-notes.md。不重写模型答案/gold/提示，不代签用户意见。

## 3. 保全与边界

- revision 3 提交 9 件归档 `rev3/`；旧 live 三件已保全后替换为新输出副本；**run-1 缓存原件未改**（`34cbf5f9…`）；rev1/rev2、A 四件三处、历史全部保持。
- 新原始产物（live-results.json / live-answers-full.json，含完整 messages/审计/send_log/停止原因/未执行题=无）在 `.cache/real-qa-smoke/T040-B-resume-1/` 与提交目录同哈希。
- 未改产品/适配器/提示/检索筛选评分器/语料/模板/gold/冻结/实验/用户记录/Astra 文件；无 commit/push、无下载安装；未跑 mock/原 A 准备/实验（工单明确不重跑）。
- **真实答案质量与学校现行性仍待人工/后续验证**；live_verified=false 待 Astra 认定。4 题一次冒烟不证明校园总体准确率或可靠拒答。

完成后停止，无论结论如何不重跑；等待 Astra 验收；不推进 T041。
