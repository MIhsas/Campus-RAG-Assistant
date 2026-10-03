# 资料与 GitHub 调研

基础调研日期：2026-09-10；TinyAgent 与语音补充日期：2026-09-12。来源以原始论文、项目官方仓库、模型卡和产品文档为主。本轮核对仓库说明及相关文档，没有克隆部署这些项目，也没有做性能或全面安全审计；以下“适合本项目”的判断是设计分析。用户已确认 RAGFlow 仅作为参考。

## 1 对现有开题报告的评审

报告的可保留主线是中文 BGE、BM25、RRF、原文溯源、后台知识管理和消融实验。主要问题是实现承诺多于数据与评价设计，并混用了若干概念。

| 原文位置与表述 | 问题 | 建议修改 |
|---|---|---|
| 1.3 承载全校高并发的工业级系统 | 缺用户量、负载模型、硬件与服务等级定义 | 改为实现可部署系统并在指定负载下评估性能 |
| 2.1 已设计并实现结构化重构算法 | 当前项目没有代码，属于计划阶段 | 改为“拟设计并验证”；完成后再写实现结果 |
| 2.1/3.2 点赞点踩构建 RLHF 闭环 | 反馈收集没有奖励模型或策略训练 | 改为“用户反馈驱动的知识库与检索优化闭环” |
| 2.1 将短问题重构为标准长文本 | 扩写可能引入新事实且增加调用成本 | 只做必要指代消解、术语规范化，原查询保留 |
| 2.1 标签前置过滤提高速度 | 不确定标签硬过滤可能直接丢失正确证据 | 权限严格过滤，明确范围约束，推断主题软排序 |
| 2.2/3.2 RRF 重排序 | 容易与 cross-encoder 重排序混淆 | 写为排名融合，可选模型重排序单列 |
| 3.2 FAISS 向量数据库 | FAISS 本身是相似度检索库 | 分开说明向量索引、元数据持久化和业务权限 [S3] |
| 3.2 PyMuPDF 统一处理多模态 PDF/Word | 不同格式与扫描、流程图需要不同处理分支 | 文本 PDF、DOCX、OCR/表格分别验证 [S7][S15] |
| 3.2 队列杜绝崩溃、答案绝对可靠 | 不可由队列或提示词保证 | 改为有界排队、超时降级及有证据支持的准确性目标 |
| 3.2 直接操作向量切片 | 可能造成原文、BM25、向量和历史引用不一致 | 改原文或审核后的结构化版本，再构建索引快照 |
| 3.4 Python 后端又由 Spring Boot 负责业务 | 职责不明确，存在双后端学习与维护成本 | 选择统一后端，或明确 Java/Python 服务边界 |
| 3.4 Windows 与 Celery | 官方不支持 Windows | Worker 使用 Linux/WSL2 容器 [S12] |
| 3.2 DeepSeek-V3.2 固定型号 | 模型别名与供给会变化 | 实验配置记录实际模型标识和执行日期 [S13] |
| 3.3 文字称图 2，实际标图 3 | 图号和引用不一致 | 最终修订时统一编号，并核对所有图表引用 |

此外，“彻底消除黑箱”“保障事实准确性”等绝对表述应改为可测量目标。引用来源能提高可核查性，不能自动证明模型对原文理解正确。

## 2 参考文献的明显问题

原报告 1.2 用文献 [10] 支持 Cormack 等 2009 年 RRF，但列表 [10] 是 UQA-RAG，引用对象不匹配。应补入真正的原始论文：

Cormack G V, Clarke C L A, Buettcher S. Reciprocal rank fusion outperforms condorcet and individual rank learning methods. SIGIR 2009: 758–759. [官方研究条目](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/)

其他需要针对性修改的地方：

- BGE 原模型或方法描述应引用官方模型卡、FlagEmbedding 与相应论文，而不是仅用另一篇应用论文证明模型来源。
- FAISS 的结构与能力应引用官方论文/文档，不应仅靠一般 RAG 应用论文支撑。
- DeepSeek API 当前型号应以执行时官方文档为准，应用领域论文不能证明当前产品型号。
- 列表中“27e66220”“71404940-1404940”等疑似把卷号和文章号粘连，需按期刊页面规范整理。
- 关于 LangChain 的历史顺序及特定企业/医院应用，原文缺直接支撑；建议删除无关历史叙事，聚焦可核查方法。

本轮未逐条核验原报告全部 16 篇参考文献，不能据此认定其中某篇不存在。后续论文定稿前应逐条核对作者、题名、年份、期刊、卷期、文章号与 DOI，并确认正文论断确实由文献支持。

## 3 GitHub 项目选择

| 项目及入口 | 本次确认的用途 | 适合借鉴的部分 | 本项目采用方式 |
|---|---|---|---|
| [FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding) | BGE 嵌入、reranker、训练与评价工具 [S4] | 模型加载、查询输入要求、重排批处理 | 核心依赖；先选一个嵌入模型，精排可关闭 |
| [FAISS](https://github.com/facebookresearch/faiss) | 稠密向量相似度检索库 [S3] | 精确检索、向量归一化、ID 映射与索引持久化 | 核心依赖；小规模先用 CPU Flat 索引 |
| [rank_bm25](https://github.com/dorianbrown/rank_bm25) | Python BM25 实现，预处理由调用者负责 [S6] | 简洁、可解释的稀疏检索基线 | 核心依赖；不夸大为高性能倒排引擎 |
| [Docling](https://github.com/docling-project/docling) | 多格式、表格、OCR、结构化导出 [S7] | 复杂文档标准化与预览数据 | 候选解析器；先拿 5—10 份复杂材料试验 |
| [Ragas](https://github.com/vibrantlabsai/ragas) | 自动评价及测试数据辅助 [S8] | 忠实度等辅助指标、实验结果组织 | 评测辅助，不替代人工政策金标准 |
| [RAGFlow](https://github.com/infiniflow/ragflow) | 文档知识库和 RAG 应用平台 [S9] | 文档处理界面、证据呈现和知识发布体验 | 已确定仅参考，不作为运行依赖 |
| [Haystack](https://github.com/deepset-ai/haystack) | 模块化检索与生成管线框架 [S10] | 组件边界、检索与路由的组织方式 | 架构学习参考，不与其他编排框架同时引入 |
| [Dify](https://github.com/langgenius/dify) | 应用工作流和 RAG 平台 [S11] | 参数配置、调试和运营界面 | 体验参考或外部对照；不建议换皮提交 |

目前没有必要寻找名称恰好叫“校园教务 RAG 毕设”的整套代码作为底座。对这个课题，拥有可解释的检索管线、清楚的政策数据和自己的实验，比复用完整聊天平台更利于证明工作量与贡献。

### 3.1 复用与许可证

本次仓库页面显示 FAISS、Docling 为 MIT；rank_bm25、RAGFlow、Haystack 显示 Apache-2.0。Dify 的 LICENSE 明确写有附加条件，不能简单记为标准 Apache-2.0。[Dify LICENSE](https://github.com/langgenius/dify/blob/main/LICENSE)

实际引入时记录仓库、版本/commit、许可证和被复用文件；保留其版权说明。库代码许可与下载模型权重许可分别检查。这里是依赖记录要求，不是对任意后续发布方式的许可结论。没有逐一审查所有依赖或模型的许可证。

不以星标数作为技术选型依据，也不把访问时的星标或“最新版本”写成论文长期事实。固定实际使用版本，比追逐最新模型更重要。

### 3.2 建议阅读顺序

第一轮阅读 FAISS 基本检索、rank_bm25 的预处理要求、BGE 模型输入示例和 RRF 论文，完成最小检索实验。第二轮阅读 Docling 的结构化表示以及 RAGFlow 的知识管理交互。第三轮在测试题集具备后阅读 Ragas 指标定义，补充自动评价。

只有在自行维护管线明显困难时再决定是否增加 LangChain/Haystack；本课题的主流程可以直接由清晰的 Python 模块组合，框架名称不是必需的论文贡献。

## 4 来源目录与使用范围

以下资料访问于 2026-09-10。论文来源用于支持方法背景，仓库/文档用于确认组件能力；本项目的阈值、排期和架构选择是设计建议，不能归因于这些资料的实测结论。

| 编号 | 来源 | 支持的内容 |
|---|---|---|
| S1 | [Lewis 等，Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks，2020](https://arxiv.org/abs/2005.11401) | RAG 的参数记忆与外部检索结合；不是零幻觉保证 |
| S2 | [Cormack 等，RRF，SIGIR 2009](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/)；[作者 PDF](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf) | 排名融合方法与正确原始引用 |
| S3 | [FAISS 仓库](https://github.com/facebookresearch/faiss)；[FAQ](https://github.com/facebookresearch/faiss/wiki/FAQ) | 检索库定位、归一化内积、过滤限制 |
| S4 | [FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding)；[reranker 示例](https://github.com/FlagOpen/FlagEmbedding/blob/master/examples/inference/reranker/README.md) | 嵌入与模型重排序的区别及工具支持 |
| S5 | [BGE-base-zh-v1.5 模型卡](https://huggingface.co/BAAI/bge-base-zh-v1.5)；[BGE-M3 论文](https://arxiv.org/abs/2402.03216) | 基线模型配置；多功能模型作为可选比较方向 |
| S6 | [rank_bm25](https://github.com/dorianbrown/rank_bm25) | BM25 实现、调用者预处理和规模边界 |
| S7 | [Docling](https://github.com/docling-project/docling) | 文档格式、表格结构、OCR 与导出能力 |
| S8 | [Ragas 仓库](https://github.com/vibrantlabsai/ragas)；[Ragas 论文](https://arxiv.org/abs/2309.15217)；[Faithfulness 定义](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/) | 自动化评测和上下文忠实度的含义 |
| S9 | [RAGFlow](https://github.com/infiniflow/ragflow) | 开源知识库/RAG 平台的功能参考 |
| S10 | [Haystack](https://github.com/deepset-ai/haystack) | 模块化检索生成管线的架构参考 |
| S11 | [Dify](https://github.com/langgenius/dify)；[LICENSE](https://github.com/langgenius/dify/blob/main/LICENSE) | 应用平台参考及许可附加条件 |
| S12 | [Celery FAQ](https://docs.celeryq.dev/en/main/faq.html) | Windows 不受官方支持 |
| S13 | [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) | 模型和价格需要按实际运行时核对 |
| S14 | [FastAPI async / await](https://fastapi.tiangolo.com/async/) | I/O 并发与 CPU 计算并行的区别 |
| S15 | [PyMuPDF Features Comparison](https://pymupdf.readthedocs.io/en/latest/about.html) | 文档提取组件的能力核查入口 |

Ragas 原 explodinggradients/ragas 地址本轮访问重定向至 vibrantlabsai/ragas，故使用实际落地地址。微信官方 `wx.request` 和 `wx.login` 文档未成功抓取，不将其具体兼容性作为已经核验的结论；实施时须结合开发工具与真机验证。

## 5 需要验证的优化假设

| 假设 | 如何验证 | 不成立时的处理 |
|---|---|---|
| 混合召回改善课程代码与简称问题 | E1/E2/E3 的术语子集比较 | 调整词典或保留更简单方案 |
| 条款和表格结构保留改善复杂问题 | E3/E4，保持上下文预算相同 | 检查解析质量和金标准，再评估切分 |
| 时间与适用范围约束减少错答 | E4/E5，检查误拒答及过度追问 | 修订元数据规则，不武断加硬过滤 |
| 精排提升证据顺序 | E5/E6，比较 nDCG、答案与时延 | 默认关闭，保留实验结果 |
| 查询改写改善多轮省略 | E5/E7，仅多轮子集并检查术语漂移 | 只使用规则指代与确认字段 |

这五条是假设而非已验证成果。最终论文应报告哪些成立、哪些没有改善及其原因。

## 6 TinyAgent 与语音补充调研

访问日期：2026-09-12。具体接入、工具边界、前台功能与验收见[前台体验与 Agent 方案](./04-前台体验与Agent方案.md)。

| 编号 | 来源 | 对本项目的结论 |
|---|---|---|
| S16 | [SqueezeAILab/TinyAgent](https://github.com/SqueezeAILab/TinyAgent)；[论文](https://arxiv.org/abs/2409.00608) | 借鉴小模型函数调用思路；其预训练工具集不能直接等同校园工具，ToolRAG 不等于政策检索 |
| S17 | [mozilla-ai/tinyagent](https://github.com/mozilla-ai/tinyagent) | 未指定仓库时的轻量 Python 适配候选；工具调用与取消须通过本项目测试 |
| S18 | [FunASR](https://github.com/modelscope/FunASR) | 中文短音频识别候选，语音功能提升为 P1；具体模型/运行时支持和识别效果需分别验证 |

不移植 macOS 桌面自动化，不把全部问题交给 Agent。普通提问保留直接 RAG，办事请求使用受限只读/草稿工具。TinyAgent 适配失败时，固定向导继续提供全部必做办事功能；实际未接入则论文仅写参考。

语音输入不依赖 Agent；识别后用户先确认文字。外部微信推送保留 P2，官方录音与订阅消息页面本轮抓取失败，不将未核实的平台条件写为已具备能力。
