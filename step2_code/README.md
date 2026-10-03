# 校园教务智能问答系统 — 后端

四川农业大学毕设项目。统一 Python/FastAPI 路线。

## 当前范围

- 健康检查接口（T002）
- 语料登记校验（T003）
- 文档正文解析（T004）
- 语料预览页（T005）
- 正文分块与来源映射（T006）
- BM25 离线检索基线（T007）
- 检索评测基线与问题集契约（T009）
- 向量与混合检索闭环（T010）
- 适用条件筛选与检索收尾（T011）
- 引用式问答接口与证据整理（T012，离线摘录 + 生成器契约）
- DeepSeek 生成适配与本地联调（T013，mock 全链路验证，未调用真实服务）
- 问答页体验与本机历史（T015）
- 办事清单与本机待办（T016，合成模板 + 原文引用核对）

无数据库、RAG 问答生成或前端框架。适用条件筛选是证据检索的资料准入，不是资格判断或政策答案。T013 的 mock 联调结果**不是真实 DeepSeek 回答**；真实服务冒烟待用户确认密钥、费用上限与授权后执行（live_verified=false）。

## 目录结构

```
step2_code/
  backend/
    src/campus_assistant/         # 应用代码
      corpus/validate.py          # 语料登记校验
      corpus/parse.py             # 文档正文解析
      corpus/chunk.py             # 正文分块（T006）
      retrieval/tokenize.py       # CJK 二元组 + ASCII 分词
      retrieval/bm25.py           # BM25 索引
      retrieval/filters.py        # 适用条件筛选（T011）
      retrieval/service.py        # 共享三模式检索管线（T012）
      retrieval/embedding.py      # BGE 向量编码服务（仅本地加载）
      retrieval/dense.py          # 向量检索索引
      retrieval/hybrid.py         # RRF 混合检索
      retrieval/search.py         # BM25 检索 CLI
      qa/evidence.py              # 证据包与字符预算（T012）
      qa/providers.py             # AnswerProvider 契约与校验（T012）
      qa/deepseek.py              # DeepSeek 生成适配（T013）
      evaluation/models.py        # 问题集契约
      evaluation/metrics.py       # 评测指标
      evaluation/run.py           # 评测 CLI（支持 --mode）
      api/corpus.py               # 语料预览 API
      api/ask.py                  # 引用式问答 API（T012）
      static/preview.html         # 预览页
      static/search.html          # 三模式证据搜索页（含筛选）
      static/ask.html             # 证据整理页（T012）
    tests/                        # 测试
    examples/                     # 合成示例语料
    pyproject.toml                # 项目配置
    requirements.lock.txt         # 精确锁定版本
    .venv/                        # 虚拟环境（已忽略）
```

## 快速开始

详见 `backend/README.md`，包含：

- 安装与启动命令
- 语料校验 CLI（`python -m campus_assistant.corpus.validate`）
- 文档解析 CLI（`python -m campus_assistant.corpus.parse`）
- 正文分块 CLI（`python -m campus_assistant.corpus.chunk`）
- BM25 检索 CLI（`python -m campus_assistant.retrieval.search`）
- 预览页（`/preview`）
- 分块策略与 BM25 说明
- 检索评测 CLI（`python -m campus_assistant.evaluation.run`，支持 `--mode bm25|dense|hybrid`）
- 三模式搜索页（`/search`，关键词/语义/混合切换 + 校区/类型/年级/日期筛选）
- 适用条件筛选说明与筛选 API 演示（`scripts/demo-filter-search.py`，夹具 `examples/filter-demo/`）
- 证据整理页与 /ask API（`/ask`，extractive 摘录 + AnswerProvider 契约；演示 `scripts/demo-ask.py`）
- DeepSeek 生成适配（`qa/deepseek.py` + `env.example`；mock 演示 `scripts/demo-deepseek-mock.py`，live 冒烟 `scripts/live-smoke-deepseek.py`）

## 后续计划

- 数据库、API 扩展
- 真实语料接入与评测
