# T001 环境与项目基线盘点报告

执行者：Mimo（Claude Code）。执行时间：2026-09-12。任务修订：v1。submission_revision：2。响应验收单 T001-R1。

---

## 0 修订记录（响应 T001-R1）

| 验收问题 | 修正内容 | 涉及章节 |
|---|---|---|
| F1 Docker 路径错误及状态证据不足 | 修正 Docker 可执行文件路径为 `D:\devSoft\Docke\resources\bin\docker.exe`；补充所有工具的真实 Get-Command 定位；Docker Daemon 改标 unknown 并说明连接失败详情 | 3.4, 3.7 |
| F2 已安装工具与未验证计算环境混淆 | 可行性对照表中 FAISS/BGE、WSL 内 Python、Docker Compose 部署改为"候选路线/理论可行，尚未实测"；内存描述修正为"接近方案中约 32 GiB 建议"并注明 TotalVisibleMemorySize 口径 | 2, 3.7 |
| F3 验证与隐私表述收窄 | 安全章节收窄为按文件名检查的事实描述；V14 标明选取摘要；V13 改为引用 V07；V17 收窄结论 | 6, 8 |
| 用户新条件 | 学校确认为四川农业大学；导师不限定技术栈；Spring Boot 不再列入阻塞；更新 open_questions 和下一步建议 | 1, 7 |

---

## 1 确认方案复述

读取 `docs/README.md`、`docs/01-系统方案.md`、`docs/02-开发路线与实验设计.md`、`docs/04-前台体验与Agent方案.md`、`docs/collaboration/PROJECT_CONTEXT.md` 后，已确认的设计要点如下：

- **运行主机**：Windows 11 作为开发主机（已确认）。Celery Worker 计划放入 Linux/WSL2 容器。
- **后端路线**：路线 A（统一 Python + FastAPI）已确认。导师不限定技术方法，Spring Boot 不再列入待确认项。
- **RAG 系统**：自建 RAG，RAGFlow 仅作参考、不作为运行依赖。
- **学校**：四川农业大学。语料来自教务网及学校其他网站公开文档，由用户后续提供。
- **学生端功能（P1）**：语音输入、办事指南与材料清单、有限事项资格自查、政策版本对比、待办日期中心为必做功能。
- **Agent 策略**：固定办事工作流必须独立可用；TinyAgent 采用可替换适配层，接入失败不影响前台交付。
- **嵌入与检索**：BGE-base-zh-v1.5 为基线嵌入模型，FAISS CPU 稠密检索，Jieba + rank_bm25 稀疏检索，RRF 融合。

**仍属建议、尚未确认的选择**：
1. 具体语料——用户尚未提供，不自行抓取学校网站。
2. 具体 TinyAgent 仓库——未指定，默认以 mozilla-ai/tinyagent 为适配候选。
3. 每周可投入时间——影响阶段压缩策略。
4. 小程序账号与上线部署条件——未确认。
5. 模型 API（如 DeepSeek）的实际可用性与预算——未实测。

---

## 2 Windows 开发环境

| 字段 | 值 |
|---|---|
| 操作系统 | Microsoft Windows 11 家庭中文版 |
| 系统版本 | 10.0.26200 |
| 架构 | 64 位 |
| CPU | 12th Gen Intel(R) Core(TM) i7-12650H |
| 系统可见内存 | 约 31.74 GiB（`TotalVisibleMemorySize`，测量口径说明见下） |
| F 盘可用空间 | 约 118 GiB（总 477 GiB，已用 360 GiB） |
| GPU | NVIDIA GeForce RTX 4070 Laptop GPU，8188 MiB 显存 |

**内存说明**：31.74 GiB 来自 Win32_OperatingSystem 的 `TotalVisibleMemorySize` 字段，该字段反映操作系统可见的物理内存总量，接近方案中约 32 GiB 的配置建议。未验证实际装机容量（如任务管理器或 BIOS 标注值）。

F 盘有足够空间存放项目文件、模型权重和索引数据。GPU 为移动端 RTX 4070（8 GiB 显存），`nvidia-smi` 可访问，但未验证 CUDA Toolkit 安装或 PyTorch 兼容性——GPU 存在不等于所有 CUDA 计算可用。

---

## 3 工具环境

所有可执行文件路径通过 `Get-Command <tool> | Select-Object -ExpandProperty Source` 在当前执行环境中实时获取，非预设安装目录。

### 3.1 Python

| 字段 | 值 |
|---|---|
| 版本 | 3.12.7 |
| 解释器路径 | `D:\Anaconda\python.exe`（Get-Command 定位） |
| pip | 24.2（from D:\Anaconda\Lib\site-packages\pip） |
| venv | 可用（`import venv` 成功） |

Python 来自 Anaconda 安装，非 Windows Store 别名。可直接用于创建虚拟环境和安装项目依赖。未验证全部项目依赖是否可安装。

### 3.2 Git

| 字段 | 值 |
|---|---|
| 版本 | git version 2.54.0.windows.1 |
| 可执行文件 | `C:\Program Files\Git\mingw64\bin\git.exe`（Get-Command 定位） |
| 项目 Git 状态 | 未初始化为 Git 仓库 |

当前项目目录 `F:\Collage Paper` 不是 Git 仓库（`git status` 报错 `fatal: not a git repository`）。按任务要求不初始化。

### 3.3 Node.js

| 字段 | 值 |
|---|---|
| 版本 | v24.15.0 |
| 可执行文件 | `D:\nodejs\node.exe`（Get-Command 定位） |

可用于管理端 Vue 3 开发和微信小程序开发工具。

### 3.4 Docker

| 字段 | 值 |
|---|---|
| 客户端版本 | 28.4.0 |
| 可执行文件 | `D:\devSoft\Docke\resources\bin\docker.exe`（Get-Command 定位） |
| Compose 插件 | v2.39.2-desktop.1（`docker info` 客户端部分输出） |
| 守护进程状态 | **unknown**（当前上下文无法连接守护进程） |

使用 `docker info --format '{{json .ServerVersion}}'` 查询时退出码 1，错误信息为：
```
error during connect: Get "http://.../dockerDesktopLinuxEngine/v1.51/info": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```
Docker 命名管道不存在，说明当前上下文无法与 Docker Desktop 守护进程建立连接。可能原因包括 Docker Desktop 未启动或引擎未初始化。按任务要求未启动；不推断全局运行状态。

### 3.5 WSL

| 字段 | 值 |
|---|---|
| 可执行文件 | `C:\Windows\system32\wsl.exe`（Get-Command 定位） |
| WSL 版本 | 2 |
| 已安装发行版 | Ubuntu（Stopped）、docker-desktop（Stopped） |

WSL2 已安装 Ubuntu 发行版，当前未运行。方案建议文档处理 Worker 放在 Linux 环境中，WSL2 可作为本地 Linux 运行环境的候选路线。但 **WSL2 的存在不等于用户已同意使用**，具体路线需用户明确。

### 3.6 NVIDIA 工具

| 字段 | 值 |
|---|---|
| 可执行文件 | `C:\Windows\system32\nvidia-smi.exe`（Get-Command 定位） |

GPU 信息见第 2 节及验证记录 V07。nvidia-smi 可访问，但未运行 CUDA Toolkit 或 PyTorch 验证——有 nvidia-smi 不等于所有 CUDA 计算功能可用。

### 3.7 原生 Windows vs WSL2 可行性对照

| 能力 | 原生 Windows | WSL2 (Ubuntu) |
|---|---|---|
| Python / FastAPI 开发 | 候选路线——Anaconda 已安装，未实测项目依赖 | 候选路线——未验证内部 Python 环境 |
| Celery Worker | 不适用——官方不支持 Windows | 候选路线——未实测 |
| Redis | 候选路线——需 Docker 或 Windows 移植版，未实测 | 候选路线——未实测 |
| FAISS / BGE 嵌入计算 | 候选路线——GPU 存在但未验证 CUDA/PyTorch | 候选路线——未实测 |
| Docker Compose 部署 | 候选路线——Docker Desktop 已安装但守护进程当前无法连接 | 候选路线——未实测 |
| 微信小程序开发工具 | 候选路线——原生 Windows 应用，未验证 | 不适用——需 Windows 运行 |

**说明**：以上仅基于已安装工具的存在性做理论可行分析，不代表已实测通过。实际可行性需在后续环境搭建任务中逐一验证。

---

## 4 项目文件盘点

### 4.1 step1（原开题报告）

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `基于RAG技术的校园教务智能问答系统设计与实现开题报告v2.0.docx` | 370,586 | `fe0ab70d5110f00e6d78d84477b2accab3e0d6ce58e8c150ebdd2ddf6a81ca72` |
| `基于RAG技术的校园教务智能问答系统设计与实现开题报告v2.0.pdf` | 596,316 | `2bdace49c6e26766373ac48c9314549bee96c0386cfdecd247293e97cbcee6da` |

原开题报告是项目设计资料，属于课题定位和需求描述文档，**不属于校园政策知识库**。

### 4.2 step2_code 与 step3_

- `step2_code/`：空目录，无实际代码文件。
- `step3_/`：空目录，无实际文件。

项目当前没有业务代码，仅有设计文档。

### 4.3 docs（方案文档）

以下选取方案与协作入口文件记录。`docs/` 目录在盘点期间新增了协作相关文件（reviews、submissions 等），以下仅列选取的方案级文件。

| 文件 | 字节数 | SHA-256 | 类别 |
|---|---:|---|---|
| `01-系统方案.md` | 26,700 | `1673c694ae1c0febc19e46f2840a659ba0c209d1554e10d5046c827789f362a6` | 系统方案 |
| `02-开发路线与实验设计.md` | 19,184 | `8248ccd3ed22e82449b2cb5cb9f8a2dc30339ace27fe9f597644ba57a88b572d` | 开发路线 |
| `03-资料与GitHub调研.md` | 12,764 | `97016f477fa934a0870f0db19b2c410d64a3e1520a27aba81fd120f8dca76b64` | 调研记录 |
| `04-前台体验与Agent方案.md` | 21,629 | `1d4e59f0648838e9e4d94f730f69f84a293bb38c424c5a1be172e9d4cf5d7ab1` | 前台方案 |
| `README.md` | 2,467 | `6045e79f1854533cebcc34cda1853000e256cf7a5f28579bda7909f441e99f4b` | 入口文档 |
| `collaboration/PROTOCOL.md` | 3,566 | `75405df87e34f38549adb103e15c02ef64029222a156f15e89112d1d42192d01` | 协作协议 |
| `collaboration/STATUS.md` | 861 | `b1cfff4576dd1dc8fc5dab1aa80920811f27cd03c5b19d853413230c8c8bd6c1` | 任务状态 |
| `collaboration/PROJECT_CONTEXT.md` | 937 | `6e03495eb56cace1503fc62eb5b0d60da36daa2ee81703a151bfcd099e292465` | 已确认项目条件 |
| `collaboration/reviews/T001-R1.md` | 4,952 | `ba08778da4816c6a31936d99d599a129655048e4616ec042037bef9b44388ecc` | 验收记录 |

注意：STATUS.md、README.md 和 PROJECT_CONTEXT.md 在首次提交后由 Astra 更新，哈希值已同步更新。PROTOCOL.md 和方案文件未变更，哈希保持不变。

---

## 5 校园政策知识库盘点

在本项目目录范围内（`F:\Collage Paper`），**未发现**学校手册、教务通知、管理办法或其他权威校园政策文件。仅有的 `step1/` 文件是课题开题报告，属于项目设计资料而非校园知识语料。

未扫描用户完整文件系统或其他目录，不扩大结论为"电脑上完全不存在"。

已确认学校为四川农业大学，语料来源为教务网及学校其他网站公开文档，由用户后续提供。不自行抓取或编造。

---

## 6 安全与隐私

- 按文件名模式 `.env`、`*.env` 在项目目录下搜索，未发现匹配文件。
- 本次盘点**未读取、扫描或审计**项目内的凭据、密钥、模型服务配置或敏感文件内容。上述搜索仅限特定文件名模式，不代表全面安全审计。
- 未读取或打印任何系统环境变量。
- `step1/` 文件名中包含课题名称，不包含学生姓名、学号或其他个人标识。

---

## 7 下一步建议与前置条件

| 建议 | 前置条件 | 状态 |
|---|---|---|
| 项目隔离环境方案（venv + requirements） | Python 3.12 已可用，可直接执行 | 条件已具备 |
| 本校语料收集与盘点（M0） | 学校已确认（四川农业大学），需用户提供具体材料 | 等待用户材料 |
| 离线解析与检索基线（M1） | 依赖 M0 语料到位 | 受 M0 阻塞 |
| Docker 环境准备 | Docker Desktop 需手动启动并验证守护进程连接；Celery Worker 需 WSL2 或 Linux 容器 | 待实测 |

**不执行上述任何步骤，仅记录为后续规划参考。**

---

## 8 已知限制

1. Docker 守护进程在当前执行上下文无法连接（命名管道不存在），仅确认客户端安装和版本，无法判断守护进程是否已安装但未启动或其他原因。不启动 Docker 以验证。
2. WSL2 Ubuntu 已安装但未启动，未验证其内部工具链（Python、pip、Docker 等）。
3. GPU 信息仅通过 `nvidia-smi` 获取，未验证 CUDA Toolkit 安装或 PyTorch/tensorflow GPU 兼容性。
4. 未扫描项目目录以外的文件系统，不声称完整了解系统所有软件。
5. 可行性对照表（3.7 节）基于已安装工具的理论分析，不代表已实测通过。
6. PowerShell 部分命令在 Git Bash 环境下需通过脚本文件执行，直接内联 `$` 变量会被 shell 吞噬。
