# T001 环境与项目基线盘点报告

执行者：Mimo（Claude Code）。执行时间：2026-09-12。任务修订：v1。

---

## 1 确认方案复述

读取 `docs/README.md`、`docs/01-系统方案.md`、`docs/02-开发路线与实验设计.md`、`docs/04-前台体验与Agent方案.md` 后，已确认的设计要点如下：

- **运行主机**：Windows 11 作为开发主机（已确认）。Celery Worker 计划放入 Linux/WSL2 容器。
- **后端路线**：默认推荐路线 A（统一 Python + FastAPI），但导师是否要求 Spring Boot 尚未确认。
- **RAG 系统**：自建 RAG，RAGFlow 仅作参考、不作为运行依赖。
- **学生端功能（P1）**：语音输入、办事指南与材料清单、有限事项资格自查、政策版本对比、待办日期中心为必做功能。
- **Agent 策略**：固定办事工作流必须独立可用；TinyAgent 采用可替换适配层，接入失败不影响前台交付。
- **嵌入与检索**：BGE-base-zh-v1.5 为基线嵌入模型，FAISS CPU 稠密检索，Jieba + rank_bm25 稀疏检索，RRF 融合。

**仍属建议、尚未确认的选择**：
1. 学校名称——未提供，语料来源未明确。
2. 导师是否要求 Spring Boot——决定采用路线 A 还是路线 B。
3. 具体 TinyAgent 仓库——未指定，默认以 mozilla-ai/tinyagent 为适配候选。
4. 每周可投入时间——影响阶段压缩策略。
5. 小程序账号与上线部署条件——未确认。
6. 模型 API（如 DeepSeek）的实际可用性与预算——未实测。

---

## 2 Windows 开发环境

| 字段 | 值 |
|---|---|
| 操作系统 | Microsoft Windows 11 家庭中文版 |
| 系统版本 | 10.0.26200 |
| 架构 | 64 位 |
| CPU | 12th Gen Intel(R) Core(TM) i7-12650H |
| 物理内存 | 31.74 GiB |
| F 盘可用空间 | 约 118 GiB（总 477 GiB，已用 360 GiB） |
| GPU | NVIDIA GeForce RTX 4070 Laptop GPU，8188 MiB 显存 |

内存满足方案建议的 16 GiB 最低起点，且超过 32 GiB 建议值。F 盘有足够空间存放项目文件、模型权重和索引数据。GPU 为移动端 RTX 4070（8 GiB 显存），可用于嵌入计算和小规模模型推理，但大模型本地部署需评估显存。

---

## 3 工具环境

### 3.1 Python

| 字段 | 值 |
|---|---|
| 版本 | 3.12.7 |
| 解释器路径 | `D:\Anaconda\python.exe` |
| pip | 24.2（from D:\Anaconda\Lib\site-packages\pip） |
| venv | 可用 |

Python 来自 Anaconda 安装，非 Windows Store 别名。可直接用于创建虚拟环境和安装项目依赖。

### 3.2 Git

| 字段 | 值 |
|---|---|
| 版本 | git version 2.54.0.windows.1 |
| 项目 Git 状态 | 未初始化为 Git 仓库 |

当前项目目录 `F:\Collage Paper` 不是 Git 仓库（`git status` 报错 `fatal: not a git repository`）。按任务要求不初始化。

### 3.3 Node.js

| 字段 | 值 |
|---|---|
| 版本 | v24.15.0 |

可用于管理端 Vue 3 开发和微信小程序开发工具。

### 3.4 Docker

| 字段 | 值 |
|---|---|
| 客户端版本 | 28.4.0 |
| Compose 插件 | v2.39.2-desktop.1 |
| 守护进程状态 | 未运行（`docker info` 无 Server Version 输出） |

Docker Desktop 已安装，但守护进程当前未启动。按任务要求未启动。

### 3.5 WSL

| 字段 | 值 |
|---|---|
| WSL 版本 | 2 |
| 已安装发行版 | Ubuntu（Stopped）、docker-desktop（Stopped） |

WSL2 已安装 Ubuntu 发行版，当前未运行。方案建议文档处理 Worker 放在 Linux 环境中，WSL2 可作为本地 Linux 运行环境。但 **WSL2 的存在不等于用户已同意使用**，具体路线需用户明确。

### 3.6 NVIDIA 工具

`nvidia-smi` 可访问，报告 GPU 为 NVIDIA GeForce RTX 4070 Laptop GPU，显存 8188 MiB。未通过 CUDA Toolkit 或其他工具进一步验证计算能力。

### 3.7 原生 Windows vs WSL2 可行性对照

| 能力 | 原生 Windows | WSL2 (Ubuntu) |
|---|---|---|
| Python / FastAPI 开发 | ✅ 可用（Anaconda） | ✅ 可用 |
| Celery Worker | ❌ 官方不支持 Windows | ✅ 支持 |
| Redis | ⚠️ 需 Docker 或 Windows 移植版 | ✅ 原生支持 |
| FAISS / BGE 嵌入计算 | ✅ 可用（有 GPU） | ✅ 可用 |
| Docker Compose 部署 | ✅ Docker Desktop 已安装 | ✅ 可用 |
| 微信小程序开发工具 | ✅ 原生 Windows 应用 | ❌ 需 Windows 运行 |

**结论**：原生 Windows 可完成大部分开发，但 Celery Worker 必须在 Linux 环境运行。WSL2 已安装但未启动，不擅自使用。

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

项目当前没有业务代码，仅有设计文档。原报告中提及的 Spring Boot 开发计划（2026 年 5—12 月）不能假设已完成。

### 4.3 docs（方案文档）

| 文件 | 字节数 | SHA-256 | 类别 |
|---|---:|---|---|
| `01-系统方案.md` | 26,700 | `1673c694ae1c0febc19e46f2840a659ba0c209d1554e10d5046c827789f362a6` | 系统方案 |
| `02-开发路线与实验设计.md` | 19,184 | `8248ccd3ed22e82449b2cb5cb9f8a2dc30339ace27fe9f597644ba57a88b572d` | 开发路线 |
| `03-资料与GitHub调研.md` | 12,764 | `97016f477fa934a0870f0db19b2c410d64a3e1520a27aba81fd120f8dca76b64` | 调研记录 |
| `04-前台体验与Agent方案.md` | 21,629 | `1d4e59f0648838e9e4d94f730f69f84a293bb38c424c5a1be172e9d4cf5d7ab1` | 前台方案 |
| `README.md` | 2,358 | `915d25a1c38b4b54074e4c18365348a67337eabf27f3abb7fbc532a0b7ecd990` | 入口文档 |
| `collaboration/PROTOCOL.md` | 3,566 | `75405df87e34f38549adb103e15c02ef64029222a156f15e89112d1d42192d01` | 协作协议 |
| `collaboration/STATUS.md` | 662 | `fd0c486145fe2bd04d75623de9eb6c824b27fb102481edd07b14a005b5cd2c26` | 任务状态 |

---

## 5 校园政策知识库盘点

在本项目目录范围内（`F:\Collage Paper`），**未发现**学校手册、教务通知、管理办法或其他权威校园政策文件。仅有的 `step1/` 文件是课题开题报告，属于项目设计资料而非校园知识语料。

未扫描用户完整文件系统或其他目录，不扩大结论为"电脑上完全不存在"。

---

## 6 安全与隐私

- 项目目录下未发现 `.env` 文件、密钥文件或模型服务配置。
- 本次盘点未读取或打印任何环境变量、凭据或个人信息。
- `step1/` 文件名中包含课题名称，不包含学生姓名、学号或其他个人标识。

---

## 7 下一步建议与前置条件

| 建议 | 前置条件 |
|---|---|
| 项目隔离环境方案（venv + requirements） | Python 3.12 已可用，可直接执行 |
| 本校语料收集与盘点（M0） | 需用户提供学校名称或权威材料来源 |
| 确认导师技术栈要求 | 需用户与导师沟通，决定路线 A 或 B |
| 离线解析与检索基线（M1） | 依赖 M0 语料到位 |
| Docker 环境准备 | Docker Desktop 需手动启动；Celery Worker 需 WSL2 或 Linux 容器 |

**不执行上述任何步骤，仅记录为后续规划参考。**

---

## 8 已知限制

1. Docker 守护进程当前未运行，仅确认客户端安装。
2. WSL2 Ubuntu 已安装但未启动，未验证其内部工具链。
3. GPU 信息仅通过 `nvidia-smi` 获取，未验证 CUDA 计算能力或 PyTorch 兼容性。
4. 未扫描项目目录以外的文件系统，不声称完整了解系统所有软件。
5. PowerShell 部分命令在 Git Bash 环境下需通过脚本文件执行，直接内联 `$` 变量会被 shell 吞噬。
