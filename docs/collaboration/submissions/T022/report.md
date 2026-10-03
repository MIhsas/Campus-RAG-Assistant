# T022 统一运行入口与配置状态 — 实施报告

身份：task_id=T022、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**（零外部模型调用；未下载新模型、未读取/打印密钥）。

## 概述

将已验收能力整合到**一个推荐正常运行入口** `scripts/serve-corpus.py`：指定语料包 + 按需显式开启本地向量模型/ASR/生成器/办事模板/自查规则（全部默认关闭，无任何隐式合成/mock 装载）；首页如实展示当前能力并区分“已配置/已验证”；启动、状态刷新、摘录零生成请求。`demo-campus.py` 保留为明确的离线模拟演示。顺手完成 T021-R1 三处整理。

## 功能交付（对照任务书）

1. **统一入口**（serve-corpus.py 优先扩展，未新造脚本串）：`--manifest/--corpus-root` + 可选 `--embedding-model-dir`、`--asr-model-dir`、`--procedures`、`--self-check`、`--generator deepseek|off`。模型目录仅本地、不自动下载；显式请求缺配置 → 明确“已降级”（仅 BM25/文字提问/摘录可用），不静默当成功。生成器复用既有 DeepSeek 适配器与环境变量密钥——密钥不进 CLI/配置 JSON/状态响应/日志，启动不探测。
2. **配置优先级与命令**：显式 CLI > 无隐式默认；密钥仅本地环境变量。README 与 `config-combos.md` 提供不含密钥的配置示例与**含空格路径已引用**的可复制 PowerShell 命令。
3. **已配置 vs 已验证**：启动配置报告分列（如“向量检索：已配置”与“模型加载完成/加载失败”分开；生成器“已配置（身份…；未验证服务连接）”）；语料成功/错误沿用现有可见错误信息。
4. **首页能力状态**（home.html 中性“校园助手”）：实时调用现有状态接口聚合——语料成功/错误数与**真实/合成/混合**标记、检索模式、生成器身份与配置状态、ASR 状态、模板/规则是否配置、是否有可比较版本；声明来源为当前服务状态（非硬编码）。未配置卡片明确解释（“不代表学校事项无模板/规则”），不诱导。合成演示问题仅存在于 demo-campus 的演示首页（home-demo.html，`demo_home=True`）。
5. **零生成请求**：启动/状态刷新/摘录不调用生成器（计数桩实测 0）；生成器启用后仅用户点击“生成答案”才调用（实测 1）；识别文本确认后仍手动提问（T020 语义未变）。用户本机历史/待办未触碰。
6. **依赖与用途说明**：README 增加配置组合表（最小/检索增强/ASR/办事自查/生成器 + 对应依赖）与两种用途区分；不为整合升级已装依赖。
7. **T021-R1 三处整理**：登记输出启动命令 PowerShell 引号（项目根含空格可直接复制）；`is_synthetic` 仅接受 JSON 布尔值（拒绝字符串/数字/null，不 bool() 强转、原值保留）；跨度测试改为 API evidence 与解析块独立对照（非自证切片）。

## 验证摘要（装配与状态真实性，真实命令见 verification.md）

- `tests/test_run_entry.py` 9 项（默认全关、显式注入、缺配置降级消息、生成器零调用/显式可达、中性 vs 演示首页、R1 三整理）+ `test_pdf_corpus.py` 11 + `test_demo_campus.py` 5 = **25 passed**。
- `scripts/demo-run-configs.py` 六组合实测 **全一致**（C1 最小 / C2 向量三模式含一次 dense 查询 / C3 ASR 状态 / C4 模板规则 / C5 生成器计数桩零调用与显式可达 / C6 缺配置降级），产出 `config-combos.md` 表与 Windows 命令。
- JS 语法 8 页通过；未重测底层解析/ASR 质量/全部检索算法；无依赖变化无需 pip check（requirements 未动）。

## 修改与新增文件

- 修改：`scripts/serve-corpus.py`（统一入口）、`scripts/register-corpus.py`（R1×2）、`scripts/demo-campus.py`（demo_home）、`src/campus_assistant/main.py`（demo_home 开关与首页选择）、`src/campus_assistant/static/home.html`（中性+能力状态）、`tests/test_pdf_corpus.py`（跨度对照）、`README.md`
- 新增：`src/campus_assistant/static/home-demo.html`、`tests/test_run_entry.py`、`scripts/demo-run-configs.py`
- 清单见 `changed-files.json`；未修改：Astra 文档、旧语料/gold、核心算法、用户本机存储。

## 已知限制

- **无浏览器工具**：浏览器主路径留待 Astra（demo-notes 检查表 a—f）。
- 合成语料/现有本地模型验证装配与状态真实性；真实语料路径仍需用户提供，不造真实库。
- “已配置”不等于连接/模型已验证——首页与启动报告均如实标注。

完成后停止，等待 Astra 验收。T023 未发布。
