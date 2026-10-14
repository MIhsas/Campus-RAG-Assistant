# T040 未来 B 阶段调用计划（live-smoke-plan.md，本次只写计划）

> **状态：A 阶段本地准备完成；真实调用 B 未授权、未执行、未验证。**
> 以下参数是**当前代码计划参数**（deepseek.py 默认值），不是重新访问官网
> 或确认服务可用的结论。不伪造价格/预计 usage；max_tokens 不是费用上限。

## 1. 计划参数（现有适配器当前默认）

| 项 | 值 |
|---|---|
| 端点 | `https://api.deepseek.com/chat/completions`（官方；base+`/chat/completions`） |
| model | `deepseek-flash` |
| max_tokens | 1500 |
| timeout | 30 秒 |
| 重试 | **零重试**（适配器无自动重试） |
| 系统提示 | 现有 SYSTEM_PROMPT（SHA256 `1fbcede5d70b3d2b…`，不改写） |

## 2. 尝试约束（一次、四题、≤4 次外部 HTTP 尝试）

1. 固定四题 q08/q10/u03/u04，每题至多 **1 次**外部尝试，合计 **≤4 次**。
2. **首次技术失败即停**（HTTP 错误/超时/连接失败），不补跑凑成功。
3. **零证据本地短路**：证据包为空的题不调用外部、外部尝试为零。
4. 业务不足（模型返回 insufficient_evidence）与技术失败分开记录。
5. 密钥仅未来本地环境配置；不出现在报告/命令/日志；未授权不询问/读取密钥。

## 3. 出站内容清单（本次实际构造的材料，未发送）

### q08（计划尝试 1 次）

- 出站=问题：考试时带小抄算什么行为？
- 出站=适用条件：`{"campus": null, "student_type": null, "admission_year": null, "as_of_date": null}`
- 出站=选定正式证据：E1, E2, E3, E4, E5（messages user 内容共 1786 字符；**字符数≠token 数**）
- 出站=现有系统提示（SHA256 `1fbcede5d70b3d2b…`）
- **不发送**：用户复核记录、gold、未核实候选、个人待办、全库、API 密钥、本机路径。

### q10（计划尝试 1 次）

- 出站=问题：本科毕业论文（设计）成绩由哪几部分组成、各占多少？
- 出站=适用条件：`{"campus": null, "student_type": null, "admission_year": null, "as_of_date": null}`
- 出站=选定正式证据：E1, E2, E3, E4, E5（messages user 内容共 1800 字符；**字符数≠token 数**）
- 出站=现有系统提示（SHA256 `1fbcede5d70b3d2b…`）
- **不发送**：用户复核记录、gold、未核实候选、个人待办、全库、API 密钥、本机路径。

### u03（计划尝试 1 次）

- 出站=问题：考试开始多久后迟到考生不得进入考场？
- 出站=适用条件：`{"campus": null, "student_type": null, "admission_year": null, "as_of_date": "2026-10-03"}`
- 出站=选定正式证据：E1, E2, E3, E4, E5（messages user 内容共 2105 字符；**字符数≠token 数**）
- 出站=现有系统提示（SHA256 `1fbcede5d70b3d2b…`）
- **不发送**：用户复核记录、gold、未核实候选、个人待办、全库、API 密钥、本机路径。

### u04（计划尝试 1 次）

- 出站=问题：学籍基本信息有误需要更正时，学生本人去哪里办理？
- 出站=适用条件：`{"campus": null, "student_type": "本科", "admission_year": null, "as_of_date": null}`
- 出站=选定正式证据：E1, E2, E3, E4, E5（messages user 内容共 2107 字符；**字符数≠token 数**）
- 出站=现有系统提示（SHA256 `1fbcede5d70b3d2b…`）
- **不发送**：用户复核记录、gold、未核实候选、个人待办、全库、API 密钥、本机路径。

## 4. B 阶段记录要求（届时执行，本次不填）

- 每题记录：完整答案、E 映射（paragraph→evidence_ids）、status（generated/insufficient_evidence/错误码）。
- 真实审计：model/request_id/usage/latency/max_tokens（供应商未返回的字段为 null，不伪造）。
- 实际尝试次数与停止原因；业务不足与技术失败分开。
- 逐段引用支持性、答案忠于证据与否——**待人工核对**（generation-review-sheet.md）。

## 5. 授权与边界声明

- 本计划**未获授权执行**：A 阶段由 Astra 先验收，用户随后决定真实调用与费用约束。
- 不探测供应商/账户/网络；不因本机已有密钥发请求；T014/T025 旧授权不延续。
- `live_verified=false`、`external_model_calls=0`；真实模型是否忠于证据/能否拒答都待验证。