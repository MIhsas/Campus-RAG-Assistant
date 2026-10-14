# T038 演示说明（demo-notes.md）

## v1.2 启动命令（Windows PowerShell，含空格路径引号；step2_code\backend 下）

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\serve-corpus.py' --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2\manifest.json' --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2' --procedures 'F:\Collage Paper\data\procedures\sicau-transfer-2026-v1\procedures.json' --port 8010
# 打开 http://127.0.0.1:8010/search 与 /ask（候选区在正式结果下方）；模板可选装配
```

- 默认 BM25；向量/ASR/生成器独立可选不隐式开启。**日期区间核查≠现行有效认证**。

## 主路径短检查表（约 6 分钟；本轮无浏览器工具，未代签——交 Astra 复验）

| # | 操作 | 预期 |
|---|---|---|
| 1 | /search 问「考试迟到」+ 查询日期=2026-10-03 → 搜索 | 严格结果（v1.2：bed3ac 已准入，5/20）；结果下方出现「查看未核实资料（独立候选）」区，**不自动请求** |
| 2 | 勾选「日期未核实」（学生类型未核实不可选，灰显原因说明）→ 点「查看候选原文」 | 候选列表（日期未知资料，如考场规则 db05e0）；每条标未核实维度/来源适用范围/原文跳转；顶部恒有「未通过…不作为已确认适用的答案依据」 |
| 3 | 先改顶部查询日期再点「查看候选原文」 | 请求仍带**结果快照**的 2026-10-03（不是改动后的控件值） |
| 4 | 候选加载失败（断网模拟） | 「候选加载失败」，正式结果保留，可「按候选快照重试」 |
| 5 | /search 问「学籍基本信息有误去哪里办理」+ 学生类型=本科 → 搜索 | 严格结果为空态/无准入（83eb scope 未知被排除）；勾选「学生类型未核实」→ 候选含 83eb 指南（卡片标「来源适用范围：未标注（含本科与否未核实）」） |
| 6 | 发起新搜索 / /ask 重提 | 旧候选区清空；迟到返回的旧候选不挂到新结果 |
| 7 | /ask 同 5 操作 | 候选区独立于正式证据（E 编号/复制/历史保存均不含候选） |

## 已完成自动化证据（真实 API / 桩，分层）

- **真实 API**（`candidate-api-demo.json`，`scripts/demo-t038-candidates.py`，v1.2 包，in-process）：严格准入 4→5（bed3ac 准入、db05e0 仍排除）；date 候选 15 份、student_type 候选 2 份（含 83eb）；契约 422×4（空维度/非法维度/无对应筛选/未知 document_id）；严格 search/ask 无候选字段。
- **后端测试**：`tests/test_uncertain_sources.py` 11 passed（候选准入/双未知规则/已知冲突不放宽/campus 严格/422/空候选/交集不回退/提示规则）；受影响既有 85 passed。
- **页面行为桩**（非浏览器）：check-search-behavior 23 场景、check-ask-behavior 40 场景（含候选快照/显式请求/旧响应不串/不进正式结果与历史）；JS 语法 9 页。
- **未执行**：真实浏览器、真实生成质量（mock 仅证明传参）、ASR/Agent、全量测试。

## 人工口径

用户意见 109 确认/3 需修订/2 未确认**原样保留**；本任务不代关闭争议。u03/u04 gold 未改（可答性翻转另单）。
