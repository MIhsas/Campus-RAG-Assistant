# T028 验证记录（revision 2，responds_to=T028-R1）

工作目录 `F:\Collage Paper`。本轮为**文档定向返工**：本地 mock/API 核对 + 代码到表述对照 + `--help`/路径核查；**零外部模型调用、无下载/安装**；未改产品代码、语料、gold；未跑全量/ASR/embedding/检索实验。v1 记录归档 `rev1/`；v1 交付文档归档 `docs/delivery/rev1/`。

## 1. 本地 API 核对（demo mock 演示服务，TestClient，零外部请求；退出码 0）

装配：`demo-campus` 的合成语料构建到**独立临时目录**（`build_combined_corpus(out_dir=<tmp>)`，不覆盖演示目录）+ `create_app` 显式注入 `CampusMockProvider`/合成模板/合成规则 + `demo_home=True`。未加载 ASR/向量模型。

| 核对项 | 请求 | **实测响应摘要** |
|---|---|---|
| 答辩原题（3a） | `POST /api/v1/ask` 「学生宿舍晚归如何处理」（无条件 / 年级2023 两组一致） | HTTP 200，`status=evidence_only`，`evidence_state=ok`，**evidence 5 条**（top3：cmp-defer-v1「本办法所称缓考…」、cmp-defer-v2 同句、syn-parse-txt「课程考核不合格…」）——**有命中但不回答该问题** |
| mock 不足分支（3b） | 「缓考申请模拟不足」+ `answer_mode=generated` | HTTP 200，`status=insufficient_evidence`，`insufficient_reason=【模拟输出】材料不足（mock）`，evidence 5 条保留 |
| mock 失败分支（3c） | 「缓考申请模拟失败」+ `answer_mode=generated` | **HTTP 502**，`{"code":"GENERATOR_ERROR","message":"生成执行失败（RuntimeError）；可改用原文摘录（answer_mode=extractive）重试","request_id":…}` ——显式报错+提示，**非自动回退**（用户显式改点摘录） |
| 办事降级（§4） | `POST /api/v1/procedures/proc-review-grade/draft`，filters 年级=2023 | HTTP 200，`status=insufficient`，**saveable=false**，2 条 issue（来源「不符合当前筛选条件」——syn-parse-docx-001/f28ee3e4、b304f406 为 2024 专属**必要引用**被筛除），步骤 g2/g3 = failed |
| 办事对照（§4） | 同上 `proc-apply-defer`，年级=2023 | HTTP 200，`status=ready`，saveable=true，issues=[] |
| demo 首页面板（§1） | `GET /` 文本解析 | 仅引用 `/api/v1/search/status`、`/api/v1/ask/status` 两个接口；**无** capability-status 六接口面板（demo 首页≠正常首页） |
| 生成校验性质 | `qa.providers.validate_generation`（不受支持文本 + 合法 E1） | 返回 **kind="answer"**（normalized 1 段）——**结构校验确认**（段落非空+引用 ID∈实发证据集；不含语义蕴含判断） |
| 规划出站字段 | `deepseek_planner.build_planner_messages` 构造 | user 消息含：用户问题 ✓、适用条件（年级=2023）✓、有界观察（hit_count）✓；system 含工具声明 ✓——出站范围表述以此为准 |

> 探针脚本：`step2_code/backend/.cache/t028r1/probe_api.py`（临时脚本，非产品代码）。

## 2. 代码到表述对照（返工单四点）

| 文档表述（修订后） | 代码/实测依据 |
|---|---|
| 答辩步骤按实际界面/响应（ask 页 E 编号包；宿舍题=有命中不答；mock 不足/失败分支；成绩复核+2023 降级） | 第 1 节实测响应摘要 |
| 引用=结构校验（哈希/跨度/准入）≠语义正确性；无可靠拒答保证 | `qa/providers.py::validate_generation`（结构性，实测 kind=answer）；T027 不足题全命中实测 |
| 默认离线 vs DeepSeek 出站范围（生成/规划分别列） | `qa/deepseek.build_messages`（问题/证据/条件）与 `agent/deepseek_planner.build_planner_messages`（快照/工具声明/观察）实际消息构造；架构图补 EXT 节点与出站边 |
| 比较= difflib.SequenceMatcher 顺序匹配（非严格 LCS） | `comparison/service.py`（`_lcs_pairs` 内 SequenceMatcher；相似度 ratio 同源） |
| asr 路径：`asr/{audio,adapter}.py` + 路由 `api/asr.py` | 目录实测（`asr/api.py` 不存在） |
| 冻结评测复现≠ assemble 前置 | `build-eval-v2.py assemble` 会 rmtree/重写语料+manifest（源码）；runbook 分列“评测复现（读冻结数据）”与“开发用途” |
| 答辩主线 ≈9—10 分钟 | defense-script v2 分段计时合计 ≈9 分 50 秒；其余移〔备选〕 |

## 3. 路径与参数核查（真实命令）

- **路径审计（范围说明，T028-R2 修正）**：对交付文档中**字面写出的 `.py/.cjs` 路径**逐条解析（17 条）——全部存在、0 缺失。该审计**不等于文档全部条目的存在性结论**：模块表括号写法（如 `corpus/*`、`retrieval/*`）与少数行内路径未逐一展开核对；T028-R2 收尾已补查并修正 ASR 行（`asr/api.py` 不存在 → `asr/{adapter,audio}.py` + `api/asr.py`），其余括号展开项经模块表逐行目视与本轮补查确认存在。
- **`--help` 复核**（未变，沿用实录）：serve-corpus（10 参数）、demo-campus（3）、evaluation run（6）、live-smoke-planner（3）、register-corpus（3）——runbook 一致。
- **指标一致性**（沿用）：文档主表与 `T027/results/aggregate.json` 逐位一致（0.95/0.95/0.925、0.9/0.9/0.705833、0.95/0.95/0.891667）。

## 4. T027-R3 两项文字勘误（在交付包声明，历史产出未动）

evidence-matrix §9 与 README：Dense「R 升、H 不变」；“医院证明或学院书面说明”为析取/备选表述（历史“合取口径”系笔误）；标注为执行模型辅助。

## 5. 真实核查 / 未运行项

**真实核查**：第 1—4 节全部本轮执行（本地 API 响应、代码对照、路径/参数/指标核查）。
**未运行**：全量测试、UI/ASR/embedding/检索实验、真实模型冒烟；**浏览器未实操**（defense-script v2 各“预期可见”以本地 API 实测为准，浏览器交互细节为历史任务证据并已注明）。

## 6. 未验证项（不变）

真实校园效果、planner_live_verified=false、生成/规划质量、可靠拒答、统计显著性——见 `evidence-matrix.md` §8。

## 7. T028-R2 非阻断收尾（五项，不另开返工循环）

1. 架构图 CMP2 节点「条号对齐/LCS」→「条号对齐+SequenceMatcher顺序匹配」（与正文一致）。
2. evidence-matrix ASR 行 → `asr/{adapter,audio}.py` + 路由 `api/asr.py`；本文件「全量路径审计」改为**范围限定表述**（字面路径 17 条 0 缺失；括号写法未逐一展开的范围如实声明）。
3. defense-script 开头实测声明收窄：仅**本次返工涉及的指定 API 案例**实测（宿舍题/mock 不足与失败/办事降级/demo 首页接口/结构校验/出站字段）；其余步骤来自代码与历史证据；探针注入直接 finish 脚本，不能证明标准 demo 规划流程，且未运行固定/模拟规划闭环、未验证页面可见性。
4. system-design 用户流程「材料不足时明确不足」→「**无证据短路或生成器返回不足状态时**明确不足（非空不相关证据不保证识别不足）」；defense-script/本文件中成绩复核失效引用改称**必要引用**（删「可选」——saveable=false 即必要引用未过核对）。
5. 演示时长：办事对照（20 秒）移入备选（B5），主线 9 段合计 590 秒（9 分 50 秒）；不作实测计时主张。

本轮仅改交付文档与提交说明；未改历史 rev1/rev2 副本、未改产品代码、未重跑测试、无外部调用。
