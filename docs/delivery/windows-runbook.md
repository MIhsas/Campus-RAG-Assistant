# Windows 运行说明（windows-runbook.md）

> T028 交付包 → **T041 当前状态更新**（2026-10-11）｜命令经真实 `--help` 与本地运行核对（见 `submissions/T028/verification.md`；T041 复核 §2a 参数）。路径含空格（`F:\Collage Paper`）已按 PowerShell 规则加引号。**默认演示零收费**；外部模型仅在显式开关 + 用户点击时可达。密钥仅以占位符说明——**不在本文档读取或粘贴任何本地密钥文件**。

## 0. 环境

- Windows 11，项目根 `F:\Collage Paper`，后端 `F:\Collage Paper\step2_code\backend`（含 `.venv`、`models\`）。
- 本地模型（可选组件，均不自动下载）：向量 `models\bge-small-zh-v1.5`；ASR（如已获取）本地 FunASR 目录。
- 所有命令先 `Set-Location 'F:\Collage Paper\step2_code\backend'`。

## 1. 离线演示（推荐先跑，零收费、零外部请求）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-campus.py --port 8030
# 浏览器打开 http://127.0.0.1:8030/
```

- 实际参数（`--help` 已核对）：`--port`、`--record-api`（输出本地 API 记录 JSON 后退出）、`--asr-model-dir`（显式指定才启用真实本地识别）。
- 演示内容：合成组合语料 + **标记 mock 生成器**（输出含“【模拟输出，非真实 DeepSeek 回答】”）+ **模拟规划器**（“模拟规划，非DeepSeek实时规划”）+ 演示问题首页。
- 状态口径：demo 的生成/规划是**模拟**；不代表真实模型能力。

## 2. 正常运行入口（指定语料包后 BM25/摘录/预览即用；可选组件默认不启用）

**2a. 真实资料主线（答辩/演示推荐；BM25 + 真实模板，零外部请求）**——整段可复制，含空格路径用单引号包裹（T041 按源码 `--help` 复核：`--manifest --corpus-root` 必填、`--port --procedures` 可选，与下式一致）：

```powershell
# 在 step2_code\backend 目录下执行（路径含空格已用引号；PowerShell 反引号续行）
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2\manifest.json' `
  --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2' `
  --procedures 'F:\Collage Paper\data\procedures\sicau-transfer-2026-v1\procedures.json' `
  --port 8010
# 浏览器打开 http://127.0.0.1:8010/  （search / ask / procedures / preview）
```

- 当前默认真实包=**v1.2**（T038，首批 20 份/原始 1182 文件）；历史 v1.1 包保留只读（历史实验输入）。

- 该命令**只开 BM25+模板**；向量/ASR/生成器/规划器均为独立可选开关（见 2b），**不默认隐式开启**。
- `data/corpora/` 与 `models/` **不在 Git 仓库**：克隆仓库≠完整可运行——需本机另有真实包目录（20 份文件+manifest）与 `models\bge-small-zh-v1.5`（仅向量模式需要）。演示机准备清单见本文 §0。

**2b. 最小与完整可选组合**：

```powershell
# 最小运行（仅 BM25 检索 + 摘录 + 预览；零外部请求）
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest 'F:\Collage Paper\step2_code\backend\examples\parse-corpus\manifest.json' `
  --corpus-root 'F:\Collage Paper\step2_code\backend\examples\parse-corpus'

# 完整可选组合（按需删减；可选组件默认不启用，BM25/摘录/预览无需开关）
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest '<语料包>\manifest.json' --corpus-root '<语料包>' `
  --embedding-model-dir 'F:\Collage Paper\step2_code\backend\models\bge-small-zh-v1.5' `
  --asr-model-dir '<本地 ASR 模型目录>' `
  --procedures '<模板.json>' --self-check '<规则.json>' `
  --generator deepseek --planner deepseek
```

实际参数（`--help` 已核对）：`--manifest --corpus-root`（必填）、`--port`（默认 8040）、`--embedding-model-dir`、`--asr-model-dir`、`--generator {off,deepseek}`、`--planner {off,deepseek}`、`--procedures`、`--self-check`。

**可选组件与密钥（占位符）**：

| 开关 | 依赖 | 密钥/环境变量（占位） | 状态口径 |
|---|---|---|---|
| `--generator deepseek` | httpx（既有） | `CAMPUS_GENERATOR=deepseek`、`DEEPSEEK_API_KEY=<本地密钥占位>`、可选 `DEEPSEEK_BASE_URL`/`DEEPSEEK_MODEL` | 配置后“已配置（连接未验证）”；用户点击“生成答案”才调用 |
| `--planner deepseek` | httpx（既有） | `CAMPUS_PLANNER=deepseek`、`DEEPSEEK_API_KEY=<本地密钥占位>` | 配置后“已配置（未联调验证）”；用户点击规划按钮才调用 |
| `--embedding-model-dir` | torch/sentence-transformers | 无 | 加载成功会单独报告“模型加载完成”（≠配置即验证） |
| `--asr-model-dir` | funasr + kaldi-native-fbank + av | 无 | 首次转写时才加载模型 |

启动输出的配置报告区分 **已配置 / 已验证（加载或连接）**；缺配置显示“已降级”并说明仍可用功能，不静默当成功。启动**不探测**模型服务；启动/状态/摘录**零生成、零规划请求**。

## 3. 语音输入（可选）

- 正常入口：加 `--asr-model-dir '<目录>'`；演示入口：`demo-campus.py --asr-model-dir '<目录>'`。
- 页面需用户点击录音/上传；静音与空转写显式提示（“未识别到有效语音”），不覆盖已有问题输入。

## 4. 评测与冒烟工具（离线；外部调用均需显式授权）

**实验复现边界（T035-R1 更正）——两个实验脚本会覆盖既有实验/冻结文件，当前冻结工作区禁止例行执行**：

- `scripts/evaluate-source-selection.py`：默认直接覆盖既有 `data/evaluations/sicau-rag-source-selection-v1/experiment.json`；虽支持 `--out` 改实验 JSON 输出位置，但 **freeze.json 仍固定写入该既有目录**（源码写入点：EXP_DIR/freeze.json）——**只传 --out 也不能保护历史冻结**；selection-map.json 为读取输入。
- `scripts/evaluate-overlap-chunks.py`：固定覆盖既有 `data/evaluations/sicau-rag-overlap-v1/frozen-config.json` 与 `experiment.json`；**没有输出目录参数**。
- 两脚本**没有统一的安全输出参数**；本文不虚构参数、不修改脚本。日常核对**只读已保存结果**（`experiment-index.md` 列出产物路径与输入哈希）。
- 如确需复现（开发用途）：**仅在独立的完整项目副本中执行**，运行前先核对脚本源码解析出的全部输出路径（含冻结文件写入点）落在副本内，确认原工作区历史证据为只读；否则不得执行。**prepare/assemble 同样禁止在冻结数据上例行执行**（assemble 会重写语料/manifest，仅开发重建夹具用）。

（下列命令为**开发用途、禁止在当前冻结工作区例行执行**，仅供独立副本中参照：）

```powershell
# 禁止在当前工作区直接运行——会覆盖既有 experiment.json/freeze.json
& .\.venv\Scripts\python.exe scripts\evaluate-source-selection.py
# 禁止在当前工作区直接运行——会覆盖既有 frozen-config.json/experiment.json
& .\.venv\Scripts\python.exe scripts\evaluate-overlap-chunks.py
```


```powershell
# 评测复现（推荐路径：直接读取现成冻结数据 examples/evaluation-v2/；零外部调用）
#   ——不要把 assemble 当作复现前置：它会重写语料/manifest，仅用于开发重建夹具
& .\.venv\Scripts\python.exe -m campus_assistant.evaluation.run --manifest examples\evaluation-v2\corpus\manifest.json --corpus-root examples\evaluation-v2\corpus --questions examples\evaluation-v2\questions.json --top-k 5 --mode bm25

# 〔开发用途，勿在冻结数据上例行执行〕合成评测集构建/标注辅助
# & .\.venv\Scripts\python.exe scripts\build-eval-v2.py assemble
# & .\.venv\Scripts\python.exe scripts\build-eval-v2.py dump-blocks --out blocks.json

# 三模式离线评测（本地 BGE；零外部调用）
& .\.venv\Scripts\python.exe -m campus_assistant.evaluation.run --manifest examples\evaluation-v2\corpus\manifest.json --corpus-root examples\evaluation-v2\corpus --questions examples\evaluation-v2\questions.json --top-k 5 --mode dense --model-path models\bge-small-zh-v1.5

# 规划冒烟 CLI（默认 dry-run 零网络；--mode live 须另行授权 + 密钥）
& .\.venv\Scripts\python.exe scripts\live-smoke-planner.py --mode dry-run --out dry-run.json
```

- `evaluation/run` 实际参数：`--manifest --corpus-root --questions --top-k --mode {bm25,dense,hybrid} --model-path`。
- `live-smoke-planner` 实际参数：`--mode {dry-run,live,mock}`、`--mock-base-url`（仅 mock）、`--out`。**`--mode live` 当前无授权**；历史授权已耗尽且不延续。
- **T040 真实生成冒烟（`scripts/live-smoke-real-qa.py --live`）=历史已执行一次**（四题限定、4/4 发送用满、授权已结束）：**禁止无新用户授权例行重跑**；本文不提供“立即复现”指引，不做模型/服务探测。已存结果与核对见 `docs/collaboration/submissions/T040/` 与 [generation-casebook.md](generation-casebook.md)。
- `trace-agent-planner.py`、`smoke-mock-sample.py`、`eval-v2-*.py` 等为离线 mock/合并工具（无 `--help` 子命令的按脚本头部注释用法）。

## 5. 语料登记（真实资料接入时）

```powershell
& .\.venv\Scripts\python.exe scripts\register-corpus.py --input '<原文文件>' --meta '<元数据.json>' --out-dir '<新语料包目录>'
```

- 实际参数：`--input --meta --out-dir`。缺元数据会**明确列出**（不猜测）；`is_synthetic` 只接受 JSON 布尔值；输出含可复制启动命令（路径引号已处理）。

## 6. 状态口径速查（配置 ≠ 验证）

| 状态 | 含义 |
|---|---|
| 生成器“已配置” | 本地开关+密钥齐全；**连接未验证**（启动不探测） |
| `live_verified=true`（T040 认定） | **仅限历史四题一次真实生成链路/存档核查**；非语义认证/校园准确率/可靠拒答/浏览器闭环；原授权 4/4 已用满结束 |
| 规划器“已配置（未联调验证）” | 同上；`planner_live_verified=false`（真实链路冒烟 partial，完整流程未通过） |
| 向量“模型加载完成” | 本地模型实际加载成功（这是已验证） |
| 办事模板/自查规则“已配置” | 显式注入了本地文件；**任意文件注入≠语义/现行性验证**（当前 2026 真实转专业模板 1.2 已接入并经用户确认 33 项；学校政策现行性未认证） |
| 首页“读取失败/未知” | 状态接口异常——不等于“未配置” |

## 7. 常见故障定位

| 现象 | 处置 |
|---|---|
| 端口被占用 | `--port` 换端口；确认旧进程已退出 |
| 密钥/代理导致 TLS 失败（连官方接口时） | 仅当前进程设 `NO_PROXY=api.deepseek.com`（`env.example` 注释口径）；**不改系统代理** |
| dense/hybrid 不可用 | 检查 `--model-path`/`--embedding-model-dir` 是否为本地目录；配置报告会写“已降级，仅 BM25” |
| 生成/规划返回“配置不完整” | 检查环境变量名（`CAMPUS_GENERATOR`/`CAMPUS_PLANNER` + `DEEPSEEK_API_KEY`）；仅设密钥不等于开启 |
| 办事草稿“暂不可保存” | 属预期：模板引用与当前语料核对不过（哈希/跨度/准入），按提示核对 |
| ASR 提示“未识别到有效语音” | 音频过短/静音或模型未加载；重录或检查 `--asr-model-dir` |
| 中文输出乱码 | Windows 控制台用 UTF-8（脚本已做流包装）；PowerShell 建议 `chcp 65001` |

## 8. 数据位置与出站边界（无数据库）

语料包=磁盘目录（manifest+原文）；检索索引=进程内存（重启重建）；问答历史/办理待办=浏览器 localStorage（用户开关/手动保存，仅本机）；密钥=环境变量（不落日志/报告）。
**出站（仅开启生成/规划且用户点击时）**：生成=问题+选定证据摘录+适用条件；规划=用户快照+工具/事项声明+有界观察。**默认离线无任何出站；本地存储 ≠ 处理全程不出机。**
