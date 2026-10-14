# T040 真实资料生成质量质检准备 — A 阶段实施报告（report.md）

身份：task_id=T040、task_revision=v1、submission_revision=1、**stage=A_ready_for_review**、status=ready_for_review、**external_model_calls=0**、**live_verified=false**、planner_live_verified=false。
范围：仅 A 阶段本地准备；真实调用 B 未授权未执行；不推进 T041。零外部请求、不读取密钥、不探测网络/账户；未改产品/提示/适配器/gold/冻结/results/aggregate/语料/模板/用户意见/历史证据/Astra 文件；无下载安装、无 commit/push。

## 1. 固定四题与人工核对标准

从冻结题集 `data/evaluations/sicau-rag-pilot-eval-v2/questions.json`（dataset 2.0）**原样读取** q08/q10/u03/u04 的 query/conditions（不添加文件选择/候选、不改变问题）。四道核对标准（任务书 §1）已逐题写入 [generation-review-sheet.md](./generation-review-sheet.md)，**初值全部“待真实运行/待核对”**；本表不含模型答案、不代签。完整原引与出处链接 [T039 review-supplement](../T039/review-supplement.md)。

| 题 | 核对重点 | 不可冒称 |
|---|---|---|
| q08 | 简洁说明带小抄属于作弊；回答避免把“将……修改为”当作结论，证据仍原字保留 | 提示存在不等于真实回答已改善 |
| q10 | 普通 50/50 与开展互评 40/10/50 的前提分别核对；引用是否支持主体与各比例 | 不按年份宣布 2016 已废止；合法 E 编号不等于语义正确 |
| u03 | as_of=2026-10-03；2019 已核实来源中的 30 分钟禁入与逾时后果 | 不从日期未知来源补答案、不宣称现行性认证 |
| u04 | 本科筛选下 83eb 未进严格依据；已有命中可能不相关，需核对是否推测办理部门 | 不把候选或 gold 放进上下文，不保证模型会拒答 |

金标准只做**离线支持性对照**（机器辅助、非人工结论），绝不插入 messages 或补充检索未发出的证据。实际证据不足即记录缺口，不修数据或改条件补齐。

## 2. 本地预检与出站材料（零外部请求）

- **预检脚本** `step2_code/backend/scripts/prepare-real-qa-smoke.py`（仅 dry-run/准备；无 --live、无付费分支）：导入 `campus_assistant.main` 前仅在**自身进程**内暂时关闭 CAMPUS_GENERATOR/CAMPUS_PLANNER/CAMPUS_ASR 三个启用标志、导入后恢复（main 模块级默认 app 按标志建 provider；该处理不等于证明 import 不读取真实配置，仅为最小必要处理）；`create_app` 显式 `answer_provider=None`（另不启用 planner/ASR/向量/模板），仅真实包 v1.2、BM25、top_k=5、现证据预算（5 条/6000 字符）。
- **四次 `answer_mode=extractive`** 走现有 `POST /api/v1/ask` 收集正式 E 证据包：evidence_state 全部 `ok`，各 5 条 E、预算内无跳过。证据切片=原块 [char_start,char_end) 逐字一致；无合成混入；**候选未混入**（u03 无 db05e0 日期未知源、u04 无 83eb scope 未知源）。
- **未来 messages**：调用现有 `qa.deepseek.build_messages(query=…, evidence=…, filters=…)` 从**这次实际证据**构造（纯文本；不实例化 HTTP provider、不读取 DEEPSEEK_API_KEY、不发送 HTTP）。与 builder 输出逐字一致；gold 零泄漏（不在证据里的 gold 文本不在 messages 里）。
- **字段归属三分**（dry-run.json `field_classes`）：实际 API 结果（extractive E 包）/ 未来计划（未发送 messages）/ 离线人工标准（核对重点与金标准对照）。字符数均标注为**字符**（≠token 数、≠费用）。
- **输入 SHA 对照**（input-hashes.json）：questions `4e39229e…`、freeze `8c289b2a…`、manifest `b05c3755…`、review-supplement `d82f4c99…` 等与 T039 冻结身份一致；含四题条目哈希与管线源文件哈希。
- **零证据/缺口处置**：本次四题均有证据（计划各 1 次外部尝试）；零证据规则已写入计划（本地短路、外部尝试为零）。金标准离线对照记录 **q08 f1（2 源）缺口**——top-5 块未覆盖 gold 跨度，按任务要求记录缺口不补数据；q10 f1/f2、u03 f1 有真实跨度命中；u04 无 gold（不足题），已有命中**可能不相关**，未假称已验证拒答。
- 输出新目录 `.cache/real-qa-smoke/T040-A/`（非空不覆盖，复跑 exit 1 已实证）；四件材料复制到本提交目录。

## 3. 未来 B 阶段计划（仅计划，见 live-smoke-plan.md）

现有适配器当前默认（**当前代码计划参数**，非重新访问官网/确认服务可用）：官方 `https://api.deepseek.com/chat/completions`、model=`deepseek-flash`、max_tokens=1500、timeout=30s、**零重试**。一次、固定四题、**≤4 次外部 HTTP 尝试**、每题至多一次、**首次技术失败即停**、不补跑凑成功、**零证据不调用**。出站=公开资料中的问题+适用条件+选定正式证据+现有系统提示；**不发送**用户复核记录/gold/候选/个人待办/全库/API 密钥/本机路径。B 记录应含完整答案、E 映射、status/真实审计与实际尝试次数；业务不足与技术失败分开；逐段引用支持性待人工核对。不伪造价格/预计 usage；max_tokens≠费用上限；密钥仅未来本地环境配置。

**不得运行 B。** A 由 Astra 先验收，用户随后决定真实调用与费用约束；未授权不询问/读取密钥。

## 验证摘要（详见 verification.md）

5 项业务测试通过（exit 0）；一次真实本地 dry-run exit 0（四题快照一致、证据切片/准入正确、messages 与 builder 一致且无 gold、generator_configured=false、外部请求 0）；非空目录拒覆盖 exit 1（预期）。未跑全量/UI/ASR/Agent/向量/三模式/T030-T039 矩阵；不重跑评测。

## 未验证与限制

- **真实生成未验证**（live_verified=false）：模型是否忠于证据、能否拒答、答案质量均待 B 阶段人工核对；提示存在≠回答改善。
- 学校政策现行性未认证；q10 不按年份断言废止；u04 scope 未知/严格不足保留；db05e0 日期未知只候选查看。
- 人工核对栏初值均为“待真实运行/待核对”，无任何模型答案或签署。

完成后停止，等待 Astra 验收；不执行 B，不推进 T041。
