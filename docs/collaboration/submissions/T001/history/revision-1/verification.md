# T001 验证记录

执行时间：2026-09-12。工作目录：`F:\Collage Paper`。

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
- **说明**：约 31.74 GiB 可见内存。直接内联 `$` 变量在 Git Bash 中会被吞掉，改为 heredoc 方式执行。

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
- **说明**：仅通过 nvidia-smi 核查，未验证 CUDA Toolkit 安装或 PyTorch 兼容性。

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

## V09 Git 版本

- **命令**：`git --version`
- **退出码**：0
- **输出**：`git version 2.54.0.windows.1`

---

## V10 Node.js 版本

- **命令**：`node --version`
- **退出码**：0
- **输出**：`v24.15.0`

---

## V11 Docker 检查

- **命令**：`docker --version`
- **退出码**：0
- **输出**：`Docker version 28.4.0, build d8eb465`

- **命令**：`docker info 2>&1 | head -20`
- **退出码**：0
- **输出摘要**：客户端信息正常（Version 28.4.0，含 Compose v2.39.2 插件），但未出现 `Server Version` 字段。
- **说明**：Docker Desktop 已安装，守护进程当前未运行。按任务要求未启动守护进程。

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
- **说明**：Ubuntu 和 docker-desktop 两个发行版已安装，均处于 Stopped 状态。未启动、未安装或更新任何发行版。

---

## V13 NVIDIA 工具

- **命令**：`nvidia-smi`（已在 V07 中验证）
- **退出码**：0
- **说明**：nvidia-smi 可访问，GPU 信息已记录。未运行 CUDA Toolkit 或其他 GPU 计算验证工具。无 NVIDIA 工具不等于没有 GPU；有 nvidia-smi 不等于所有 CUDA 功能可用。

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

- **命令**：`find docs -type f -exec ls -la {} \;`
- **退出码**：0
- **输出**：列出 7 个方案文档和协作文件（详见 report.md 第 4.3 节）。

---

## V15 文件 SHA-256 哈希

- **命令**：`sha256sum "step1/基于RAG技术的校园教务智能问答系统设计与实现开题报告v2.0.docx" "step1/基于RAG技术的校园教务智能问答系统设计与实现开题报告v2.0.pdf"`
- **退出码**：0
- **输出**：
  ```
  fe0ab70d5110f00e6d78d84477b2accab3e0d6ce58e8c150ebdd2ddf6a81ca72  ...docx
  2bdace49c6e26766373ac48c9314549bee96c0386cfdecd247293e97cbcee6da  ...pdf
  ```

- **命令**：`sha256sum docs/01-系统方案.md docs/02-开发路线与实验设计.md docs/03-资料与GitHub调研.md docs/04-前台体验与Agent方案.md docs/README.md docs/collaboration/PROTOCOL.md docs/collaboration/STATUS.md`
- **退出码**：0
- **输出**：完整哈希已记录在 report.md 和 inventory.json 中。

---

## V16 校园政策文件搜索

- **命令**：`find . -type f \( -name "*.docx" -o -name "*.pdf" -o -name "*.xlsx" -o -name "*.doc" -o -name "*.xls" -o -name "*.txt" -o -name "*.pptx" \) | grep -v "submissions"`
- **退出码**：0
- **输出**：仅 `step1/` 下的两个开题报告文件。
- **说明**：本项目目录范围内未发现校园政策文件。不扩大为系统级结论。

---

## V17 .env 文件检查

- **命令**：`find . -name ".env" -o -name "*.env"`
- **退出码**：0
- **输出**：（空）
- **说明**：项目目录下未发现 .env 或环境配置文件。

---

## V18 JSON 解析验证

- **首次尝试（失败）**：`python -c "import json; json.load(open('...inventory.json')); print(...)"`
  - **退出码**：1
  - **错误**：`UnicodeDecodeError: 'gbk' codec can't decode byte 0xad`
  - **原因**：Windows 默认使用 GBK 编码读取文件，JSON 文件含中文字符（UTF-8）导致解码失败。

- **修正命令**：`python -c "import json; d=json.load(open('docs/collaboration/submissions/T001/inventory.json', encoding='utf-8')); print('inventory.json: valid, task_id=%s' % d['task_id'])"`
- **退出码**：0
- **输出**：`inventory.json: valid, task_id=T001`

- **命令**：`python -c "import json; d=json.load(open('docs/collaboration/submissions/T001/submission.json', encoding='utf-8')); print('submission.json: valid, status=%s, files=%d' % (d['status'], len(d['files'])))"`
- **退出码**：0
- **输出**：`submission.json: valid, status=ready_for_review, files=4`

---

## V19 交付文件完整性

- **命令**：`ls -la docs/collaboration/submissions/T001/`
- **退出码**：0
- **输出**：
  ```
  report.md
  verification.md
  inventory.json
  submission.json
  ```
- **说明**：四个交付文件均存在。
