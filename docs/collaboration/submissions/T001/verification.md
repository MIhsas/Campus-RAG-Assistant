# T001 验证记录

执行时间：2026-09-12。工作目录：`F:\Collage Paper`。submission_revision：3。响应验收单 T001-R2。

---

## V01 工作区确认

- **命令**：`ls -la`（Git Bash）
- **退出码**：0
- **输出摘要**：
  ```
  CLAUDE.md
  docs/
  step1/
  step2_code/
  step3_/
  ```
- **说明**：确认当前目录为 `F:\Collage Paper`，包含预期的五个顶层条目。

---

## V02 Git 仓库状态

- **命令**：`git status`
- **退出码**：128
- **输出**：`fatal: not a git repository (or any of the parent directories): .git`
- **说明**：项目未初始化为 Git 仓库。按任务要求不初始化，如实记录。

---

## V03 操作系统信息

- **命令**：`powershell -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select-Object Caption, OSArchitecture, Version | Format-List"`
- **退出码**：0
- **输出**：
  ```
  Caption        : Microsoft Windows 11 家庭中文版
  OSArchitecture : 64 位
  Version        : 10.0.26200
  ```
- **说明**：输出中中文字符在 Git Bash 中显示为乱码，但字段值可从结构解析。

---

## V04 CPU 型号

- **命令**：`powershell -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object Name | Format-List"`
- **退出码**：0
- **输出**：`Name : 12th Gen Intel(R) Core(TM) i7-12650H`

---

## V05 物理内存

- **命令**：PowerShell 脚本（通过 stdin heredoc 执行）
  ```powershell
  $os = Get-CimInstance Win32_OperatingSystem
  $mem = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
  Write-Output "Memory_GiB: $mem"
  ```
- **退出码**：0
- **输出**：`Memory_GiB: 31.74`
- **说明**：31.74 GiB 来自 `TotalVisibleMemorySize`，是操作系统可见的物理内存总量，不等同于 BIOS 或任务管理器标注的实际装机容量。

---

## V06 F 盘可用空间

- **命令**：`df -h .`（Git Bash）
- **退出码**：0
- **输出**：
  ```
  Filesystem  Size  Used Avail Use% Mounted on
  F:          477G  360G  118G  76% /f
  ```
- **说明**：F 盘约 118 GiB 可用。

---

## V07 GPU 信息

- **命令**：`nvidia-smi --query-gpu=name,memory.total --format=csv,noheader`
- **退出码**：0
- **输出**：`NVIDIA GeForce RTX 4070 Laptop GPU, 8188 MiB`
- **可执行文件路径**：`C:\Windows\system32\nvidia-smi.exe`（Get-Command 定位）
- **说明**：仅通过 nvidia-smi 核查，未验证 CUDA Toolkit 安装或 PyTorch 兼容性。GPU 存在不等于 CUDA 计算可用。

---

## V08 Python 检查

- **命令**：`python --version`
- **退出码**：0
- **输出**：`Python 3.12.7`

- **命令**：`python -c "import sys; print(sys.executable)"`
- **退出码**：0
- **输出**：`D:\Anaconda\python.exe`
- **说明**：来自 Anaconda 安装，非 Windows Store 别名。

- **命令**：`python -m pip --version`
- **退出码**：0
- **输出**：`pip 24.2 from D:\Anaconda\Lib\site-packages\pip (python 3.12)`

- **命令**：`python -c "import venv; print('venv available')"`
- **退出码**：0
- **输出**：`venv available`

---

## V09 Git 版本与路径

- **命令**：`git --version`
- **退出码**：0
- **输出**：`git version 2.54.0.windows.1`

- **命令**：`powershell -NoProfile -Command "Get-Command git | Select-Object -ExpandProperty Source"`
- **退出码**：0
- **输出**：`C:\Program Files\Git\mingw64\bin\git.exe`

---

## V10 Node.js 版本与路径

- **命令**：`node --version`
- **退出码**：0
- **输出**：`v24.15.0`

- **命令**：`powershell -NoProfile -Command "Get-Command node | Select-Object -ExpandProperty Source"`
- **退出码**：0
- **输出**：`D:\nodejs\node.exe`

---

## V11 Docker 检查

### V11a 客户端版本

- **命令**：`docker --version`
- **退出码**：0
- **输出**：`Docker version 28.4.0, build d8eb465`

### V11b 可执行文件路径

- **命令**：`powershell -NoProfile -Command "Get-Command docker | Select-Object -ExpandProperty Source"`
- **退出码**：0
- **输出**：`D:\devSoft\Docke\resources\bin\docker.exe`

### V11c 守护进程状态

- **命令**：`docker info --format '{{json .ServerVersion}}'`
- **退出码**：1
- **输出**：
  ```
  ""
  error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/info": open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
  ```
- **说明**：Docker 命名管道不存在，当前上下文无法连接 Docker Desktop 守护进程。无法确定是守护进程未启动、Docker Desktop 引擎未初始化或其他原因。inventory 中 Docker Daemon 标为 `unknown`。

### V11d Docker Compose（R2 修订新增）

- **命令**：`docker compose version`
- **退出码**：0
- **输出**：`Docker Compose version v2.39.2-desktop.1`
- **可执行文件路径**：`D:\devSoft\Docke\resources\bin\docker-compose.exe`（Get-Command 定位）
- **说明**：独立于 V11a/V11c，仅验证 Compose 插件版本，未涉及守护进程连接。

---

## V12 WSL 检查

- **命令**：`wsl --status`
- **退出码**：0
- **输出**（Unicode 编码显示异常，内容解析）：默认发行版 Ubuntu，WSL 版本 2。

- **命令**：`wsl --list --verbose`
- **退出码**：0
- **输出**：
  ```
  NAME              STATE     VERSION
  * Ubuntu          Stopped   2
    docker-desktop  Stopped   2
  ```
- **可执行文件路径**：`C:\Windows\system32\wsl.exe`（Get-Command 定位）
- **说明**：Ubuntu 和 docker-desktop 两个发行版已安装，均处于 Stopped 状态。未启动、未安装或更新任何发行版。

---

## V13 NVIDIA 工具

引用 V07 结果：`nvidia-smi` 可访问，GPU 为 NVIDIA GeForce RTX 4070 Laptop GPU（8188 MiB）。可执行文件路径 `C:\Windows\system32\nvidia-smi.exe`（Get-Command 定位）。未运行 CUDA Toolkit 或其他 GPU 计算验证工具。

---

## V14 项目文件盘点

- **命令**：`find step1 -type f -exec ls -la {} \;`
- **退出码**：0
- **输出**：
  ```
  -rw-r--r-- 370586 Apr 13 21:19 step1/...开题报告v2.0.docx
  -rw-r--r-- 596316 Apr 13 21:19 step1/...开题报告v2.0.pdf
  ```

- **命令**：`find step2_code -type f` / `find step3_ -type f`
- **退出码**：0
- **输出**：（空，无文件）
- **说明**：step2_code 和 step3_ 为空目录。

- **命令**：`find docs -type f | sort`
- **退出码**：0
- **说明**：完整 docs 目录含多个文件（方案文档、协作文件、submissions、reviews、tasks）。此处选取方案级与协作入口文件共 10 个记录在 report.md 和 inventory.json 中。不冒充完整遍历输出。

---

## V15 文件 SHA-256 哈希（R2 修订：实际重新计算）

本轮修订期间对记录范围内全部 12 个文件（step1 的 2 个 + docs 选取的 10 个）统一执行 `wc -c` 和 `sha256sum`，结果如下。命令一次性完成，无手动复制旧值。

### step1 文件（2 个）

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `...开题报告v2.0.docx` | 370,586 | `fe0ab70d5110f00e6d78d84477b2accab3e0d6ce58e8c150ebdd2ddf6a81ca72` |
| `...开题报告v2.0.pdf` | 596,316 | `2bdace49c6e26766373ac48c9314549bee96c0386cfdecd247293e97cbcee6da` |

### docs 选取文件（10 个）

| 文件 | 字节数 | SHA-256 |
|---|---:|---|
| `01-系统方案.md` | 27,048 | `7626bed129f556cefd40cca88fdd875bd45bd39956422e72b36a1048608d39f7` |
| `02-开发路线与实验设计.md` | 19,476 | `e5a7c781b8c6b76adbe228e1d15de175b6368b151585ec8e30a95600c378d362` |
| `03-资料与GitHub调研.md` | 12,764 | `97016f477fa934a0870f0db19b2c410d64a3e1520a27aba81fd120f8dca76b64` |
| `04-前台体验与Agent方案.md` | 21,629 | `1d4e59f0648838e9e4d94f730f69f84a293bb38c424c5a1be172e9d4cf5d7ab1` |
| `README.md` | 2,521 | `42f4377c6537c145bd6eb506491a922d2db13e2ec1be29025bfc6ecc5df8eb40` |
| `collaboration/PROTOCOL.md` | 3,566 | `75405df87e34f38549adb103e15c02ef64029222a156f15e89112d1d42192d01` |
| `collaboration/STATUS.md` | 948 | `3f9aa30177089ed6bdcbd9200015d0961d4dfbaef7a6c936c8e0f8fe8657ce54` |
| `collaboration/PROJECT_CONTEXT.md` | 937 | `6e03495eb56cace1503fc62eb5b0d60da36daa2ee81703a151bfcd099e292465` |
| `collaboration/reviews/T001-R1.md` | 4,952 | `ba08778da4816c6a31936d99d599a129655048e4616ec042037bef9b44388ecc` |
| `collaboration/reviews/T001-R2.md` | 3,587 | `c3ae12f570103061679de3bfb28f94ab931da002b785bb2fb9591256c6b010ca` |

### 与前版（revision-2）的差异

| 文件 | revision-2 字节数 | 当前字节数 | 变更原因 |
|---|---:|---:|---|
| `01-系统方案.md` | 26,700 | 27,048 | Astra 更新（非执行者） |
| `02-开发路线与实验设计.md` | 19,184 | 19,476 | Astra 更新（非执行者） |
| `README.md` | 2,467 | 2,521 | Astra 更新（非执行者） |
| `collaboration/STATUS.md` | 861 | 948 | Astra 多次更新（非执行者） |

其余 8 个文件字节数和哈希与 revision-2 一致。

### report 与 inventory 一致性校验

report.md 4.3 节表格中记录的字节数与 inventory.json 中 `project_files` 数组的 `bytes` 字段逐项比对：12 项全部匹配。SHA-256 同样逐项匹配（report 使用缩写，inventory 使用完整值）。

---

## V16 校园政策文件搜索

- **命令**：`find . -type f \( -name "*.docx" -o -name "*.pdf" -o -name "*.xlsx" -o -name "*.doc" -o -name "*.xls" -o -name "*.txt" -o -name "*.pptx" \) | grep -v "submissions"`
- **退出码**：0
- **输出**：仅 `step1/` 下的两个开题报告文件。
- **说明**：本项目目录范围内未发现校园政策文件。不扩大为系统级结论。

---

## V17 敏感文件名检查

- **命令**：`find . -name ".env" -o -name "*.env"`
- **退出码**：0
- **输出**：（空）
- **说明**：按文件名模式 `.env`、`*.env` 在项目目录下搜索，未发现匹配文件。此检查仅限特定文件名模式，**不代表全面安全审计**：未读取文件内容、未扫描其他凭据格式（如 `.pem`、`.key`、`credentials` 等）、未检查环境变量或密钥管理系统。

---

## V18 JSON 解析验证

- **首次尝试（失败）**：`python -c "import json; json.load(open('...inventory.json')); print(...)"`
  - **退出码**：1
  - **错误**：`UnicodeDecodeError: 'gbk' codec can't decode byte 0xad`
  - **原因**：Windows 默认使用 GBK 编码读取文件，JSON 文件含中文字符（UTF-8）导致解码失败。

- **修正命令**：`python -c "import json; d=json.load(open('docs/collaboration/submissions/T001/inventory.json', encoding='utf-8')); print('inventory.json: valid, task_id=%s, files=%d, tools=%d' % (d['task_id'], len(d['project_files']), len(d['tools'])))"`
- **退出码**：0
- **输出**：`inventory.json: valid, task_id=T001, files=12, tools=11`

- **命令**：`python -c "import json; d=json.load(open('docs/collaboration/submissions/T001/submission.json', encoding='utf-8')); print('submission.json: valid, revision=%d, status=%s' % (d['submission_revision'], d['status']))"`
- **退出码**：0
- **输出**：`submission.json: valid, revision=3, status=ready_for_review`

---

## V19 交付文件完整性

- **命令**：`ls -la docs/collaboration/submissions/T001/*.md docs/collaboration/submissions/T001/*.json`
- **退出码**：0
- **输出**：
  ```
  report.md (12134 bytes)
  verification.md
  inventory.json (5339 bytes)
  submission.json (5420 bytes)
  ```
- **说明**：四个交付文件均存在。history/revision-1/ 和 history/revision-2/ 保存了前两版快照。

---

## V20 项目文件与协作文件当前状态（R2 修订重写）

**CLAUDE.md**：
- **命令**：`sha256sum CLAUDE.md && wc -c < CLAUDE.md`
- **当前值**：1,618 字节，SHA-256 `423d0c4bddc32c500835d1680afdd1b900cd5a1a16dde7e8607e85ed12ddfac4`
- **说明**：Astra 在 T001-R1 验收期间已更新此文件（revision-2 快照中的 hash 已无法在此处重新获取，因快照复制时未同时记录基线）。本次记录当前值，**无法据此证明此前从未修改**。

**docs/collaboration/tasks/T001-环境与项目基线盘点.md**：
- **当前值**：7,147 字节，SHA-256 `004f395575a7d77062475549ce853c789aaf0e95ac815691cd769af8d74f1a7e`
- **说明**：此哈希与首次提交时 V15 记录一致。任务书未被 Mimo 修改；是否在 Mimo 执行期间由 Astra 修改，以 Astra 的变更记录为准。

**docs/collaboration/PROTOCOL.md**：
- **当前值**：3,566 字节，SHA-256 `75405df87e34f38549adb103e15c02ef64029222a156f15e89112d1d42192d01`
- **说明**：与首次提交时记录一致。Mimo 未修改此文件。

---

## V21 report 与 inventory 交叉验证（R2 修订新增）

- **方法**：用 Python 读取修订后的 report.md 和 inventory.json，逐项比对 `project_files` 中每个文件的 `bytes` 和 `sha256` 字段与 report.md 4.3 节表格中记录的值。
- **结果**：12 项全部匹配（字节数和 SHA-256 完全一致）。
- **说明**：report 和 inventory 来自同一次实际盘点计算，无手动复制差异。
