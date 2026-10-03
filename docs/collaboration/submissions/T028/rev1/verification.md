# T028 验证记录

工作目录 `F:\Collage Paper`。任务验收范围=核对文档链接、关键代码映射、启动参数与指标一致性 + 三条文档→实现抽查；**未重跑全量/UI/ASR/检索实验，未执行真实模型冒烟**；零外部模型调用、无下载/安装。普通文档任务未新增测试套件（按任务书）。

## 1. 交付文档与链接核查（真实命令，退出码 0）

```bash
# 6 个交付文件存在 + README 相对链接解析 + 15 条关键代码路径存在（内联 python 核查脚本）
# docs/delivery/{README,system-design,thesis-outline,evidence-matrix,defense-script,windows-runbook}.md 全部 OK
# README.md 内相对链接（5 条）0 断链；代码路径抽查 15 条全部存在
# code-path spot-check: 15 paths exist | link/code/metric issues: 0
```

覆盖代码路径含：`api/ask.py`、`qa/deepseek.py`、`api/procedures.py`、`procedures/service.py`、`api/agent.py`、`agent/{workflow,tools,deepseek_planner}.py`、`retrieval/{service,filters}.py`、`evaluation/run.py`、`scripts/{serve-corpus,demo-campus,live-smoke-planner,register-corpus}.py`。

## 2. 启动参数与真实 `--help` 一致性

```bash
./.venv/Scripts/python.exe scripts/serve-corpus.py --help   # --manifest --corpus-root --port --embedding-model-dir --asr-model-dir --generator --planner --procedures --self-check
./.venv/Scripts/python.exe scripts/demo-campus.py --help    # --port --record-api --asr-model-dir
./.venv/Scripts/python.exe -m campus_assistant.evaluation.run --help  # --manifest --corpus-root --questions --top-k --mode --model-path
./.venv/Scripts/python.exe scripts/live-smoke-planner.py --help  # --mode {dry-run,live,mock} --mock-base-url --out
./.venv/Scripts/python.exe scripts/register-corpus.py --help    # --input --meta --out-dir
```

runbook 中全部命令参数与上述实录逐一相符；含空格路径 `F:\Collage Paper` 已按 PowerShell 引用规则书写。演示命令零收费口径：`demo-campus.py` 为纯本地合成+模拟（无外部请求路径）。

## 3. 实验表格与 T027 revision 3 机器结果一致性（真实命令，退出码 0）

```bash
# 读取 docs/collaboration/submissions/T027/results/aggregate.json 与文档主表逐位比较
# machine: bm25 (0.95, 0.95, 0.925) | dense (0.9, 0.9, 0.705833) | hybrid (0.95, 0.95, 0.891667)
# doc table matches T027-R3 accepted values: True
```

交付包（README/thesis-outline）主表与 T027-R3 验收值一致；4 道材料不足题“空检索率 0”表述一致；T025 partial 口径在 README/thesis/defense 三处一致。

## 4. 三条文档→实现抽查（真实 grep）

| 抽查 | 文档主张 | 实现命中 |
|---|---|---|
| 问答 | 摘录默认、生成仅显式、DeepSeek 适配 | `api/ask.py` `answer_mode` 默认 extractive（行 38）；`qa/deepseek.py::generate`（行 186） |
| 办事 | 逐引用核对 + saveable 门 | `procedures/service.py::_check_citation`（77）、`build_draft`（111）、saveable 判定（132） |
| 规划 | 服务端产物判定 + 越权参数拒绝 | `agent/workflow.py::_finish_verdict`（77）、`run_planner_loop`（380）；`agent/tools.py` forbidden 拒绝（83—89） |

## 5. T027-R3 勘误落实（不改历史原始产出）

- Dense rev2→v2.1 变化表述：交付包内统一为“**R 升、H 不变**”（evaluation-report 历史文件不动，勘误在 `evidence-matrix.md` §9 与 README 声明）。
- “医院证明或学院书面说明”在交付包内表述为**析取/备选**（历史“合取口径”标注为笔误）。
- 标注性质：交付包内统一声明“执行模型辅助标注（非独立教师/盲评）”。

## 6. 真实核查 / 未运行项（如实）

**真实核查**：第 1—5 节全部为本轮实际执行（链接/路径/参数/指标/抽查/勘误）。
**未运行**：全量 pytest、UI/ASR/检索实验、真实模型冒烟（任务明确排除）；**浏览器演示未实操**（无浏览器能力）——defense-script.md 为预期操作单，其中各步骤的可见结果引用的是历史任务（T016—T023 等）浏览器验收证据，已注明所属任务与范围，**不冒充当前新测**。

## 7. 未验证项（交付包内同样列明）

真实学校语料效果、planner_live_verified（false）、生成/规划质量、统计显著性、可靠拒答——见 `evidence-matrix.md` §8。
