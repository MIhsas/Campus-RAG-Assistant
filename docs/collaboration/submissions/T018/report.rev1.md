# T018 统一演示入口与问答办事联动 — 实施报告

身份：task_id=T018、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**（全部本地开发与验证，零外部调用；mock 演示不是 DeepSeek 实时回答）。

## 概述

把问答、证据搜索、办事与待办、版本对比、原文预览接入同一个离线演示服务（统一首页 + 单条启动命令），并建立“提问 → 相关办事事项 → 带条件草稿”的明确入口。复用既有业务（检索/生成/对比算法零改动），不引入新框架/数据库。

## 功能交付（对照任务书）

1. **统一离线演示入口** `scripts/demo-campus.py`：单条命令服务全部功能；`--record-api` 模式输出本地 API 演示记录。
2. **组合演示语料**：启动时将 parse-corpus 与 comparison-corpus 重建组合到 `.cache/demo-campus-corpus/`——**保留原文档 ID、文件内容与哈希**（逐字节校验），两份原始夹具与 gold 只读不动；文档 ID 冲突显式报错（SystemExit）不静默覆盖；每次启动干净重建，避免第二份内容手工漂移。procedures 模板仍绑定原 parse-corpus ID，在组合语料上引用校验通过。
3. **标记 mock 生成器**：显式注入 `CampusMockProvider`（`mock:campus-demo`），所有模拟回答带【模拟输出，非真实 DeepSeek 回答】；演示入口**不读取真实生成器配置**（测试断言脚本不含 provider_from_env/CAMPUS_GENERATOR/DEEPSEEK_API_KEY）。
4. **统一首页 `/`**：五个功能入口卡片 + 三条可点击演示问题（URL 预填问题）+ 状态行**实时读取当前服务**（语料/检索模式/生成器身份，不写死“真实模型已连接”）；五页头部均有“首页”回链。
5. **问答→办事联动**：ask 页结果带“相关事项入口”卡片（缓考申请 `proc-apply-defer`、成绩复核 `proc-review-grade`，显式关键词映射**非 Agent 推理**，标注不代表符合办理条件；稳定 procedure_id 链接；无匹配不显示）。链接携带**该结果的问题与筛选快照**（URL 参数编码，不含答案原文/密钥）。
6. **办事页带入**：显式“已带入条件（来自问答结果快照）”横幅（含参考问题）；**等筛选选项加载后**恢复值，缺失选项保留为“（已不在当前选项）”并提示“已保留该条件”；仍需用户点击生成草稿——**不自动保存待办、不自动调用模型**。
7. **历史快照正确**：历史结果的事项入口携带**历史条件**（非当前控件值），并注明“将按当前加载资料重新生成指南”；更改控件不改写旧结果卡片快照；重试/失败转摘录/历史行为未动。
8. **答辩演示脚本**：[demo-notes.md](./demo-notes.md) 含 Windows 单条启动命令与 5—8 分钟逐步脚本（每步标注确定性功能/模拟生成/T014 历史真实服务证据）与 Astra 检查表。
9. 组合语料扩大检索候选属真实检索行为，演示建议使用清晰筛选条件；未伪造检索结果、未覆盖旧评测预期。正常业务启动入口（main:app、demo:app）保持原样。

## 验证摘要（聚焦，真实命令见 verification.md）

- `tests/test_demo_campus.py` **5 passed**：组合语料 ID/哈希逐字节保留且可解析（5 文档）、源夹具未动、ID 冲突显式报错、统一路由 6 页全 200、模板引用通过、版本对比可用、mock 带标记、入口不读真实配置。
- JS：6 页语法（home 新增）+ ask **17 场景**（+4：快照链接绑定/历史条件/无匹配不推荐/URL 预填）+ procedures **11 场景**（+2：带入恢复零自动请求与零写入/缺失选项保留提示）。
- 本地 API 演示 `campus-demo.json`：**10 个路由全部 200**（home/双 status/procedures/compare/ask 摘录+mock 生成/草稿/预览）。
- 未重跑 embedding、全量测试或旧评测（算法未改动）；共享代码仅路由新增（`/`）与页面增量，均经上述聚焦回归。

## 修改与新增文件

- 新增：`scripts/demo-campus.py`、`static/home.html`、`tests/test_demo_campus.py`
- 修改：`main.py`（`/` 路由）、`static/ask.html`（首页链接/预填/相关事项卡片）、`static/procedures.html`（首页链接/快照带入）、`static/search.html`、`static/preview.html`、`static/compare.html`（首页链接）、`scripts/check-ask-behavior.cjs`、`scripts/check-procedures-behavior.cjs`、`README.md`
- 清单见 `changed-files.json`；未修改：Astra 文档、原语料夹具/gold、已验收检索/生成/对比算法。

## 已知限制

- **无浏览器工具**：跨页闭环未由真实浏览器执行；[demo-notes.md](./demo-notes.md) 提供 Astra 可运行入口与逐步检查表（a—g）；stub 不冒充真实浏览器证据。
- mock 生成器输出仅为标记演示文本，**不是 DeepSeek 实时回答**；T014 的一次限定真实冒烟为独立历史证据。
- 组合语料为合成虚构政策；不代表学校真实政策或办事指南准确率。

完成后停止，等待 Astra 验收。T019 未发布。
