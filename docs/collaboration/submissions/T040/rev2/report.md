# T040 真实资料限定生成冒烟 — 实施报告（report.md，submission_revision=2）

身份：task_id=T040、**task_revision=B-v1、submission_revision=2、responds_to=T040-B、stage=B_not_started、status=partial**、**external_model_calls=0**、live_verified=false、planner_live_verified=false。
授权依据：用户 2026-10-09 对“四题、官方端点、deepseek-flash、≤4 次尝试、max_tokens=1500、零重试、首次技术失败即停”回复“授权”；无人民币上限指定，不虚构金额或价格。
A 阶段九件已归档 `rev1/`（原样）；原 A 四件材料（dry-run/input-hashes/核对表/原计划）在原位保持原字节。A/B 证据分层不混。

## 1. B 阶段实际结果：前置缺密钥拒绝，零外部请求

**B 未执行（not_attempted×4）**。`--live` 入口实际执行一次（run-1）：

- 前置核对 **A 身份通过**：A 材料 SHA 三处一致（提交件==rev1==缓存原件）、input-hashes 输入/源文件未漂移、当前管线四题正式 E 与 build_messages 与 A 一致（请求 UUID 不作差异）。
- **缺 DEEPSEEK_API_KEY 被拒**：执行环境（进程、含非沙箱）无任何 DEEPSEEK*/CAMPUS* 变量；Windows User/Machine 级密钥亦不存在；仓库无 .env（机制=环境变量，见 windows-runbook）。按工单 §3/§6：缺密钥 → **零请求、非零退出**，如实提交，不暗改输入、不向用户索取密钥文本。
- 实际计数：external_http_attempts=**0**；四题 outcome=not_attempted；`live-results.json` 为拒绝记录（run-1 原样保留）。
- 环境核查仅变量名/存在性，未读取或输出任何密钥值/全量环境/HTTP headers。

**待配置后即可执行**：将 `DEEPSEEK_API_KEY` 配置进会话环境（勿经聊天传递），重跑 `--live` 一次即按已授权范围执行（脚本已就绪，勿改题/模型/地址/次数）。

## 2. 本地实施与验证（已完成部分）

- 新增 `step2_code/backend/scripts/live-smoke-real-qa.py`：最小单次执行入口，默认 dry-run、显式 `--live` 才发请求；复用现有 create_app、`/api/v1/ask` generated 管线、DeepSeekAnswerProvider 与引用结构校验；AttemptRecordingProvider 在**发送位置**计数（连接失败同样占次）并仅记录已观察供应商状态（未知=null）；官方配置门核对**实际 provider 只读属性**（endpoint/model/max_tokens/timeout）；NO_PROXY 保留既有项补 api.deepseek.com（仅本进程）；输出目录非空拒绝覆盖；失败即停、业务不足可继续、零证据本地短路不计尝试；无重试/解析修复再请求/换模型/地址/补跑路径。
- 新增 `step2_code/backend/tests/test_live_smoke_real_qa.py`：4 项本地 mock（发送位计数+HTTP/连接失败即停+not_attempted；业务不足可继续+paragraph→E/generation_meta/双状态完整记录；前置失败零请求+非官方目标拒绝；零证据短路零尝试）。**4 passed，exit 0**（首跑 2 failed 为测试查询未命中合成语料的 fixture 问题，修正测试后通过；未改计数/停止逻辑）。mock 明确标记，不冒充真实生成质量。
- 未改产品代码/适配器/生成提示/检索筛选评分器/prepare-real-qa-smoke.py/旧 live-smoke-deepseek.py 合成语料门/gold/冻结/结果/聚合/语料/模板/用户意见/历史材料/Astra 文件；无下载安装、无 commit/push、未跑全量/UI/ASR/Agent/三模式/向量/旧矩阵。

## 3. 停止语义与记录（就绪待用）

工单语义已实现并在 mock 验证：技术失败（HTTP/连接/超时/空输出/非法 JSON/截断/引用不合法）首次即停、未执行题 not_attempted、失败保留不自修再试；业务 insufficient_evidence 可继续；/ask 条数与外部 HTTP 次数分开；本地 HTTP 状态与供应商 HTTP 状态分开，未知为 null；不伪造 usage/价格/供应商字段。真实执行后应产出 live-results/live-answers-full/live-review-notes 三件（本次仅有拒绝记录与如实空记录，见各文件内注）。

## 4. 逐段核对框架（无评价对象）

核对方法与语义边界已锁定于 [live-review-notes.md](./live-review-notes.md)：q10 两前提比例分开、不按年份废止；u03 按已核实来源原文、不从 db05e0 补；q08 f1 缺口保留、合理不足可接受、E 不支持即不判忠实；u04 不推测办理部门、不保证拒答。三栏（本次证据支持/gold 覆盖/用户语义确认）独立记录，不合并成准确率；用户 109/3/2 与模板 33 项确认不变，不代签。

## 验证摘要（详见 verification.md）

mock 4 passed（exit 0）；dry-run 前置 exit 1（缺密钥拒绝，预期）；--live run-1 exit 1（同因，零外部请求）；A 身份核对通过。**已知记录瑕疵**：run-1 的 ask_calls=0 未计入前置 4 次本地 extractive（外部次数 0 准确）；脚本已修正，记录刷新重跑被执行环境权限分类器拦截、按其指引未换途径重试，run-1 原样保留不伪造。

完成后停止，等待 Astra 验收；不推进 T041。
