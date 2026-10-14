# T040 A/B 阶段执行日志（continuation-progress.md）

日期：2026-10-09。执行：MiMo（Claude Code 新窗口）。工作区 `F:\Collage Paper`，Windows 11 / Git Bash。
解释器：`F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe`。
授权：仅 T040 A 阶段（`docs/collaboration/tasks/T040-真实资料生成质量质检准备.md`）。按小步骤追加更新。

## 范围与边界（继承自任务书/提示词）

- 只读输入：真实包 v1.2、冻结题集 v2.0（q08/q10/u03/u04 原样）、T039 review-supplement、现有 create_app//ask/证据包管线/build_messages。
- 允许写：`scripts/prepare-real-qa-smoke.py`、`tests/test_prepare_real_qa_smoke.py`、`submissions/T040/`、`.cache/real-qa-smoke/T040-A/` 新目录、`docs/delivery/README.md` 仅顶部纠偏。
- 零外部请求、不读取密钥、不开发/开放 --live、不改产品/提示/适配器/gold/冻结/语料/模板/用户意见/Astra 文件；不跑全量/UI/ASR/Agent/向量/三模式；无下载安装、无 commit/push。

## 本窗口实际步骤记录

### 步骤 1：读取与现状盘点（已完成）

已读：CLAUDE.md 顶部授权、STATUS.md、PROTOCOL.md（前一会话已读，沿用）、任务书 T040 全文、T040-MiMo提示词。
代码核对（只读）：`main.py`（create_app/模块级默认 app 在 import 时按 CAMPUS_GENERATOR/CAMPUS_PLANNER/CAMPUS_ASR 建 provider——预检脚本需导入前于本进程关三标志）、`api/ask.py`（POST /api/v1/ask、extractive→evidence_only、generated 无 provider 时 503）、`qa/evidence.py`（E1..En/整条进出/预算 5 条 6000 字符）、`qa/deepseek.py`（build_messages 纯文本；provider_from_env 先查 CAMPUS_GENERATOR 再查 DEEPSEEK_API_KEY；默认 deepseek-flash/1500/30s）、`api/search.py`（SearchFilters 兼容冻结 conditions 的 null/字符串）、`retrieval/service.py`（execute_search 签名）、现有脚本 sys.path 模式与测试 importlib 加载模式。
数据核对（只读）：四题 query/conditions 从 v2.0 提取一致（q08/q10 无条件；u03 as_of_date=2026-10-03；u04 student_type=本科）；manifest 关键文档元数据：bed3ac（2019-11-07 已核实）、db05e0（日期未知）、83eb（scope 未知）、ddf417/q08 源、287dcca/q10 源。
scratch 临时文件放 `.cache/real-qa-smoke/_scratch/`（不占用 T040-A 输出目录）。

下一步：编写 prepare-real-qa-smoke.py 与少量业务测试，运行测试与一次真实本地 dry-run。

### 步骤 2：准备脚本与业务测试（已完成）

新增 `step2_code/backend/scripts/prepare-real-qa-smoke.py`（仅 dry-run/准备；无 --live/付费分支；导入 main 前于本进程关 CAMPUS_GENERATOR/CAMPUS_PLANNER/CAMPUS_ASR 三标志、导入后恢复；显式 answer_provider=None；四题走 POST /api/v1/ask extractive 收集正式 E；build_messages 构造未来 messages；金标准只做离线支持性对照；输出目录非空拒绝覆盖；失败非零退出）。
新增 `step2_code/backend/tests/test_prepare_real_qa_smoke.py`（5 项：标志守卫恢复、非空目录拒覆盖、messages 与 builder 一致+gold 注入被拒、零证据本地短路计划、合成语料小闭环+合成混入守卫）。

命令（cwd=backend）：

```text
python -m pytest tests/test_prepare_real_qa-smoke.py -q
# 首跑 2 failed（poisoned 用例 match 与守卫实际错误不符；合成 fixture 触发污染守卫）→ 修正测试后
# 5 passed，退出码 0（修复的是测试断言/fixture，未改守卫逻辑）
```

### 步骤 3：一次真实本地 dry-run（已完成）

命令（cwd=`F:\Collage Paper`）：

```text
python step2_code/backend/scripts/prepare-real-qa-smoke.py
# PREPARE OK: 4 题 dry-run 完成；外部请求 0；写入 .cache/real-qa-smoke/T040-A/ 四件；退出码 0
# stderr: 1 条 PDF 解析警告（Ignoring wrong pointing object）原样出现，非失败

python step2_code/backend/scripts/prepare-real-qa-smoke.py   # 再跑验证不覆盖
# FAIL: 输出目录非空，拒绝覆盖；退出码 1（预期）
```

实际结果（详见 dry-run.json）：
- 四题 query/conditions 与冻结一致（回显校验通过）；extractive/evidence_only；evidence_state 全部 ok、各 5 条 E、预算内无跳过。
- 证据切片=原块 [char_start,char_end) 逐字一致；无合成混入；**候选未混入**（u03 无 db05e0、u04 无 83eb）。
- messages 与 build_messages 一致、gold 零泄漏；generator_configured=false；外部请求 0。
- 金标准离线对照：q10 f1/f2、u03 f1 均有真实跨度命中；**q08 f1（2 源）缺口——已记录，不修数据补齐**；u04 无 gold（不足题）。
- 输入 SHA：questions `4e39229e…`/freeze `8c289b2a…`/manifest `b05c3755…`/review-supplement `d82f4c99…` 与 T039 冻结身份一致。

下一步：材料复制到 submissions/T040/、report/verification/submission/changed-files、docs/delivery/README.md 顶部纠偏。

### 步骤 4：提交材料与文档收尾（已完成）

- 四件 dry-run 材料复制到 `docs/collaboration/submissions/T040/`（与 `.cache/real-qa-smoke/T040-A/` 原件逐一同哈希）；scratch 临时文件已清理。
- `docs/delivery/README.md` 顶部纠偏：新增「当前状态（截至 T038/T039）」表（v1.2 包/T039 n=21 基线/人工 109/3/2+模板 33 确认+四项待定向复核+现行性未认证）；T035 速览表与基线数字标注为历史快照；其余内容按 T035 原样，未扩写交付八件/论文。
- report.md（A 阶段实施报告）、verification.md（测试与 dry-run 实测+缺口如实）、submission.json（submission_revision=1、stage=A_ready_for_review、external_model_calls=0、live_verified=false）、changed-files.json（10 项实测哈希）写毕。

### 步骤 5：终检（已完成）

```text
python -c "<changed-files 10 项哈希 + 冻结身份 + deliverables + 材料同哈希>"
# 哈希 10/10 匹配；questions 4e39229e…/freeze 8c289b2a…/aggregate fcecdc9c…/manifest b05c3755… 身份未变
# submission: T040 / 1 / A_ready_for_review / ready_for_review / ext_calls 0 / live False
# deliverables 9 项齐备；T040-A 原件 4 件与提交副本同哈希；退出码 0
```

### 补记（同日）：收到与上一轮相同的 T040 A 阶段指令

核对落盘状态：submissions/T040/ 9 件齐备、submission.json=T040/1/A_ready_for_review/ready_for_review/external_model_calls=0/live_verified=false、dry-run 四题 evidence_state=ok（q08 f1 缺口保留）。**未重复执行、未重跑脚本/测试**（材料已提交且脚本对非空输出目录本就拒覆盖）。继续等待 Astra 验收。

## 提交状态（本窗口最终）

**task_id=T040、submission_revision=1、stage=A_ready_for_review、status=ready_for_review、external_model_calls=0、live_verified=false、planner_live_verified=false。** 提交目录 `docs/collaboration/submissions/T040/`（9 件）。已知缺口：q08 f1（2 源）gold 跨度未被 top-5 覆盖（记录不补）；真实生成/拒答/现行性均未验证。未执行 B、未推进 T041、无 commit/push、无下载安装、未改 Astra 文件与冻结数据。**按授权停止，等待 Astra 验收。**

---

# T040 B 阶段（task_revision=B-v1，responds_to=T040-B）

授权依据：用户 2026-10-09 对“四题、官方端点、deepseek-flash、≤4 次尝试、max_tokens=1500、零重试、首次技术失败即停”回复“授权”（见 STATUS.md 最新段与 B 工单）。无人民币上限指定，不虚构价格。

## B 步骤记录

### B-1：读取工单并归档 A（已完成）

已读：T040-B-MiMo提示词、STATUS.md 最新段、tasks/T040-B-真实资料限定生成冒烟.md、reviews/T040-R1.md（背景）。
旧 live-smoke-deepseek.py 只读参考其计数/官方配置门/失败即停语义（不修改）。

A 九件（report/verification/submission/changed-files/continuation-progress/dry-run/input-hashes/generation-review-sheet/live-smoke-plan）已复制至 `submissions/T040/rev1/`（新目录，未覆盖既有归档）；dry-run.json 归档哈希 `31babb70…` 与原件一致。原 A 四件材料在原位保持原字节。

下一步：新增 live-smoke-real-qa.py 与 mock 测试。

### B-2：执行脚本与 mock 测试（已完成）

新增 `step2_code/backend/scripts/live-smoke-real-qa.py`（默认 dry-run、显式 --live 才发请求；AttemptRecordingProvider 在发送位置计数并记录已观察供应商状态；复用 /ask generated 管线与 DeepSeekAnswerProvider/validate_generation；前置核对 A 材料 SHA/输入 SHA/四题 E/messages 一致（UUID 不作差异）+ 实际 provider 只读属性官方值门；缺密钥/配置不符/材料漂移零请求非零退出；失败即停/业务不足可继续/零证据短路不计尝试）。
新增 `step2_code/backend/tests/test_live_smoke_real_qa.py`（4 项 mock：发送位计数+技术失败即停+连接失败也占次；业务不足可继续+完整记录；前置失败零请求+非官方目标拒绝；零证据短路零尝试）。

```text
python -m pytest tests/test_live_smoke_real_qa.py -q   （cwd=backend）
# 首跑 2 failed（查询未命中合成语料致零证据短路，断言前提不成立）→ 测试查询改为与语料同词后
# 4 passed，退出码 0（修改测试 fixture，未改计数/停止逻辑）
```

下一步：dry-run 前置核对 → --live 单次执行。

### B-3：dry-run 前置核对与 --live 入口执行（结果：缺密钥拒绝，零外部请求）

```text
python step2_code/backend/scripts/live-smoke-real-qa.py            # dry-run 前置
# a_identity_ok: true（A 材料 SHA 三处一致、输入 SHA 未漂移、四题 E/messages 与 A 一致）
# config_check: 失败——DEEPSEEK_API_KEY 不存在/为空：零请求拒绝；exit 1

python step2_code/backend/scripts/live-smoke-real-qa.py --live     # 授权入口执行一次（run-1）
# 前置拒绝（缺密钥）；external_http_attempts=0、零外部请求；exit 1
# 写入 .cache/real-qa-smoke/T040-B/live-results.json（拒绝记录）
```

环境核查（仅变量名/存在性，未读取或输出任何值）：进程环境（含非沙箱）无 DEEPSEEK*/CAMPUS* 变量；Windows User/Machine 级 DEEPSEEK_API_KEY 亦不存在；仓库无 .env（机制=环境变量，见 windows-runbook）。按工单 §3/§6：**缺密钥 → 零请求非零退出，如实提交 partial（stage=B_not_started）**，不冒称 B 已执行。

已知记录瑕疵（如实保留）：run-1 记录 ask_calls=0 未计入前置 4 次本地 extractive 核对（外部次数 0 准确）；脚本已修正该计数。记录刷新重跑被执行环境权限分类器拦截（多次瞬时错误后拒绝），按其指引未换途径重试；run-1 记录按原样保留，不覆盖不伪造。

下一步：提交 revision 2（partial）四件 + live 记录三件。

### B-4：revision 2 提交收尾与终检（已完成）

- live-results.json（run-1 拒绝记录）复制到提交目录；live-answers-full.json 如实无答案记录；live-review-notes.md 核对框架与语义边界锁定。
- report/verification/submission/changed-files 更新为 revision 2（B_not_started/partial）。
- 终检：changed-files 8 项哈希全部匹配；A 四件材料提交件==rev1==缓存三处同哈希；rev1 九件齐备；submission=2/B-v1/T040-B/B_not_started/partial/external_model_calls=0；冻结身份未变（questions 4e39229e…/manifest b05c3755…）。

## 提交状态（B 阶段最终）

**submission_revision=2、task_revision=B-v1、responds_to=T040-B、stage=B_not_started、status=partial、external_model_calls=0、live_verified=false、planner_live_verified=false。** 阻断原因：执行环境缺 DEEPSEEK_API_KEY（零外部请求、四题 not_attempted）。配置密钥进会话环境后重跑 --live 一次即按已授权范围执行。**按授权停止，等待 Astra 验收；不推进 T041。**

---

# T040-R2 定向返工（submission_revision=3，responds_to=T040-R2）

## R2-1：读取与保全（已完成）

已读 STATUS.md、T040-R2 返工单、B 工单（背景）、T040-B-preflight-probe.py/.json（只读）。revision 2 八件归档 rev2/（live-results `34cbf5f9…` 与原件一致）；探针旧失败记录保全 rev2/T040-B-preflight-probe-failed-preserved.json（`94e3944f…`）；run-1 原件未改。

## R2-2：两项必修（已完成）

- 必修1 输出目录前置门：run_b 起始检查/准备输出目录，非空立即 raise 零发送；最终防覆盖保留；live 守卫（无输出路径/计数客户端未装配不开始付费调用）。
- 必修2 发送位点计数：SendCountingClient 经 client 注入（无全局补丁/不改适配器），post 处查预算（≤4）递增（连接失败计 1、发送前异常/零证据计 0）；provider_calls 另列；失败即停/每题≤1/零重试保持。
- 同批：前置/守卫拒绝记录补齐四题 not_attempted+停止原因；run-1 勘误与缺密钥表述收敛写入 fix-report/report/verification。

## R2-3：验证与提交（已完成）

```text
python -m pytest tests/test_live_smoke_real_qa.py -q    （cwd=backend）
# 首跑 5 passed/1 failed（新链2断言笔误 fake.calls==0 应为 ==[]）→ 修正后
# 6 passed，退出码 0

python docs/collaboration/reviews/T040-B-preflight-probe.py   （cwd=根目录，原样运行）
# nonempty_output_before_send: mock_post_calls=0、error 非空、旧文件不变、未写新审计 → pass
# counter_matches_actual_send: post=0 == reported=0 → pass
# 总判 pass=true，退出码 0（旧失败记录已保全，探针/断言/通过标准未改）
```

终检：changed-files 哈希匹配；rev2/run-1/A 四件/rev1 字节保持；submission=3/T040-R2/B_not_started/partial/external_model_calls=0。**提交后停止；不运行 live、不推进 T041，等待 Astra 核查。**

---

# T040-B-恢复执行（submission_revision=4）

## B-恢复1：密钥就绪与保全（已完成）

执行进程 DEEPSEEK_API_KEY 存在性=False（既有进程未继承）→ 按 2026-10-09 配置补充授权，仅读取 User 级该一条变量装入执行 Python 的同一 PowerShell（未打印值、未查其他位置/注册表/进程/.env），存在性=True。revision 3 九件归档 rev3/；T040-B-resume-1 确认无已有输出。

## B-恢复2：真实运行一次（已完成）

```text
powershell（装入 User 级密钥后，cwd=backend）:
.\.venv\Scripts\python.exe .\scripts\live-smoke-real-qa.py --live --out-dir '.\.cache\real-qa-smoke\T040-B-resume-1'
# 前置门全过（A 身份/E/messages 一致、实际官方配置 deepseek-flash/1500/30s、新输出目录、安全摘要先行）
# q08→q10→u03→u04 各发送 1 次：external_http_attempts=4、provider_calls=4、ask_calls=8、零重试
# completed_all，无技术失败/not_attempted；供应商审计 4×HTTP 200、finish_reason=stop、request_id/usage/latency 入档
# 退出码 0
```

## B-恢复3：逐段核对与提交（已完成）

q10 三段：P1/P2 逐字获实发 E1/E2 支持（50/50 与 40/10/50 分列、未按年份宣布废止）、P3 基本支持（「不纳入比例」适度推断留人工）；f1/f2 gold 覆盖。u03：bed3ac 逐字支持、f1 覆盖、未从 db05e0 补。q08：拒答忠于实发 E（E5 属违纪非作弊、无小抄认定表述）——合理不足，f1 缺口保持不兜底。u04：拒答忠于实发 E、未推测部门、83eb 未混入。用户确认四题均「未确认」，不代签。
新产物（e607654b…/96416950…）与 T040-B-resume-1 原件同哈希；旧 live 三件保全于 rev3/；run-1 缓存未改（34cbf5f9…）。
report/verification/live-review-notes/submission/changed-files 更新完毕。

## 提交状态（最终）

**submission_revision=4、responds_to=T040-B-恢复执行、task_revision=B-v1、stage=B_executed、status=ready_for_review、external_model_calls=4、live_verified=false（待 Astra 认定）、planner_live_verified=false。** **提交后停止：不重跑、不 commit/push、不改产品/语料/模板/gold/冻结/实验/用户记录/Astra 文件、不推进 T041。**
