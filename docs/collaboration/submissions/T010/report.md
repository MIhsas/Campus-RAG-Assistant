# T010 向量与混合检索闭环 — 实施报告

## 概述

本任务实现三种检索模式（BM25、Dense、Hybrid）的完整闭环，包括后端检索器、搜索 API 模式切换、前端模式选择器和统一评测 CLI。

## 新增模块

### 1. Embedding Service (`retrieval/embedding.py`)
- 加载 BAAI/bge-small-zh-v1.5 模型（CPU, float32）
- 文档批量编码（无查询前缀）
- 查询编码（加检索前缀 `为这个句子生成表示以用于检索相关文章：`）
- L2 归一化，维度从模型获取

### 2. Dense Index (`retrieval/dense.py`)
- NumPy 精确点积排序（归一化向量）
- 存储 chunks 深拷贝，结果独立
- score > 0 才返回，score desc + chunk_id asc 排序

### 3. Hybrid RRF (`retrieval/hybrid.py`)
- BM25 和 Dense 各取前 20 候选
- `rrf_score = Σ 1/(60+rank)`，缺失一路贡献 0
- 同分按 chunk_id 排序
- 输出附 bm25_rank/dense_rank/bm25_score/dense_score

### 4. 搜索 API 更新 (`api/search.py`)
- SearchRequest 新增 `mode: bm25|dense|hybrid`，默认 bm25
- SearchStatusResponse 新增 `available_modes` 和 `embedding_model`
- 不可用模式返回 503/RETRIEVER_UNAVAILABLE
- 响应带 mode 字段

### 5. 搜索页面更新 (`static/search.html`)
- 新增"关键词/语义/混合"三按钮选择器
- 未启用模型的选项禁用
- 结果标签动态显示"关键词匹配分/语义相似度/融合排序分"
- 混合结果展示 BM25/Dense 双路排名

### 6. 评测 CLI 更新 (`evaluation/run.py`)
- 新增 `--mode bm25|dense|hybrid` 和 `--model-path` 参数
- 输出含 mode、model、embedding_normalization、query_prefix、rrf_k

### 7. 下载脚本 (`scripts/download-embedding-model.py`)
- 从 Hugging Face 官方下载 BGE 模型到本地目录

### 8. 工厂更新 (`main.py`)
- `create_app` 新增 `embedding_model_path` 参数
- 配置时同时构建 BM25 + Dense 索引
- 模型加载失败仅让 dense/hybrid 不可用，BM25 和原文预览不受影响

## 三模式评测对比

| 模式 | Evidence Recall | Hit | MRR |
|---|---|---|---|
| BM25 | 1.0 | 1.0 | 0.917 |
| Dense (bge-small-zh) | 1.0 | 1.0 | 0.917 |
| Hybrid (RRF k=60) | 1.0 | 1.0 | 0.917 |

合成数据量小（8题），三种模式均达到完美召回。真实语料规模更大时预期会有差异。

## 测试结果

- 全量 pytest：374 passed, 1 skipped, 2 warnings
- pip check：通过
- JS 语法检查：preview.html/search.html 均 OK
- 搜索 API 新增 6 项测试（available_modes、mode default/explicit、dense/hybrid 503、invalid mode 422）

## 未验证项

- 浏览器模式切换完整流程（无浏览器工具）
- CPU 推理实际延迟
