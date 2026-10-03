# Campus RAG Assistant

四川农业大学毕业设计：校园教务资料检索、引用式问答与办事辅助系统。当前采用 Windows / Python / FastAPI 后端和原生 HTML 页面。

## 功能

- TXT、DOCX、文本型 PDF 解析、原文定位与预览。
- BM25、本地 BGE 向量检索、RRF 混合检索及适用条件筛选。
- 证据摘录、可选 DeepSeek 生成问答、引用跳转与本机历史。
- 办事草稿与本机待办、条件自查、政策版本对比。
- 可选本地语音识别；固定工作流与受限工具规划。

RAGFlow 和 TinyAgent 作为设计参考；没有集成其运行时代码。生成段落的引用编号经过结构校验，但这不保证答案的语义正确性或可靠拒答。

## 开始使用

后端要求 Python 3.12。依赖、启动及可选模型配置见 [后端运行说明](step2_code/backend/README.md) 和 [Windows 运行手册](docs/delivery/windows-runbook.md)。本地模型与虚拟环境不随仓库提供。

在已按说明准备环境后，可运行本地演示：

```powershell
Set-Location '.\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-campus.py --port 8030
```

打开 `http://127.0.0.1:8030/`。该入口使用合成语料、明确标记的模拟生成器和模拟规划器，不调用真实模型服务。正常语料入口为 `scripts/serve-corpus.py`，可选组件须显式开启。DeepSeek 模式会把相应问题、证据或规划上下文发送到外部服务；密钥仅在本地配置，不能提交到仓库。

## 文档与目录

- [当前交付文档](docs/delivery/README.md)：系统设计、论文底稿、证据矩阵和答辩脚本。
- [协作状态](docs/collaboration/STATUS.md)：任务及验收记录；历史文档可能描述当时状态，应以当前验收为准。
- `step2_code/backend/`：产品代码、测试和合成示例。
- `tools/sicau_capture/`：独立资料采集工具，说明见[工具 README](tools/sicau_capture/README.md)。工具存在不表示其采集资料已经进入 RAG 语料或经过政策有效性审核。
- `docs/collaboration/submissions/`：分阶段交付与实验记录。

T027 检索实验基于 13 份合成文档、24 道题，不代表真实校园准确率。T028 交付包已验收；历史真实规划冒烟仍为 partial，`planner_live_verified=false`。

本次 Git 快照不包含原始开题报告、采集数据、模型权重、虚拟环境、缓存和本地密钥。真实资料接入及质量验证按后续工单执行。
