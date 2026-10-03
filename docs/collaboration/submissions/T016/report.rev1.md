# T016 办事清单与本机待办 — 实施报告

身份：task_id=T016、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**（仅本地开发与验证，无任何外部模型调用）。

## 概述

交付完整闭环：选择事项与适用范围 → 带引用办理步骤草稿 → 明确保存到本机待办 → 勾选进度/个人备注/提醒日期 → 刷新恢复 → 核对当前依据。合成资料功能原型（非学校现行办事指南），沿用 FastAPI 与静态页面，无数据库/账户/TinyAgent/语音/前端框架迁移。

## 功能交付（对照任务书）

### 模板与后端（合成模板显式注入）

- **`examples/procedures/procedures.json`**：两个 `is_synthetic=true` 事项——缓考申请（4 步）、成绩复核（3 步）。全部引用经程序化生成并逐条核对：document_id/block_id/字符区间/原文 quote/文档 sha256 来自 parse-corpus 实际文本（跨度切片一致性已验证）。不编造材料/部门/截止日期；未说明项标注“资料未说明，请向办理部门核实”；“考试前”“公布后10个工作日”等相对期限保留原文，不造绝对日期。
- **`procedures/service.py` + `api/procedures.py` + main.py 注册**：GET `/api/v1/procedures`、POST `.../draft`（filters 同搜索，复用 T011 筛选准入）、POST `.../verify`。模板位置由工厂参数 `procedures_path` 注入，默认不加载（测试/演示显式启用，不混入未来真实语料运行）。
- **逐条核对**：每条引用检查 文档存在 → 内容哈希 → 原文跨度切片一致 → 筛选准入。必要引用任一失败 → `saveable=false`（“资料不足/依据需更新”），**不输出冒充完整的可保存清单、不放宽筛选**；可选引用失败降级为“资料未说明”。
- **2023 不混入 2024 专属 DOCX**：缓考申请的材料引用（DOCX 表“需医院证明”）为可选——2023 下显示“资料未说明”而非 2024 内容，草稿仍可保存；成绩复核的必要来源均在 2024 专属 DOCX 中——2023 下明确拒绝（saveable=false），合适范围（2024/不限）下两事项均可演示。

### 页面（`static/procedures.html`，与任务书“同页”选项一致）

事项卡片、四项筛选（T011-R1 保留规则）、草稿步骤（原文展开、查看原文、合成标记、未说明项）、保存门槛（不可保存时按钮禁用+原因）；我的待办：进度勾选、个人备注、个人新增步骤、个人提醒日期（标签“个人提醒”、升序排列无日期置后、已过期/今日/以后按浏览器本地日期）、上移/下移排序、删除个人步骤与整清单、未完成/已完成筛选、**核对当前依据**。政策步骤（原文引用、不可改写）与个人步骤明确标签区分；保存前零持久化、防重复提交（另存需明确点击）；存储不可用不显“保存成功”；上限 20 份提示先删除、不静默丢弃。核对变化只加“请复核”横幅，**不覆盖勾选/备注**，可看新草稿另存新清单。导航与 /search、/ask、/preview 互通。

### T015-R1 三项小整理（已合并并实测）

pageshow 同步历史开关与提示；模拟不足演示题改为“缓考申请模拟不足”（实测命中 5 条证据进 mock 不足分支）；复制按钮按状态为“复制回答与来源”/“复制问题与摘录”。

## 验证摘要（聚焦，真实运行）

- **新增后端测试 12 项全过**：两事项引用有效（跨度逐条核对）、2023/2024 不混入、隔离夹具哈希变化/缺失 → 不可保存、verify unchanged/changed/unavailable/版本变化、筛选不放宽、路由与工厂（默认 503）。
- **本地 API 演示**（`api-demo.json`，7 次调用）与**引用核对表**（`citation-crosscheck.md`）：缓考 2023/2024 可保存、成绩复核 2024 可保存/2023 拒绝、verify 双分支。
- **JS**：4 页语法 + procedures 行为 7 场景（草稿/保存门槛/零持久化防重复/刷新恢复零请求/进度备注个人步骤排序删除筛选/核对保留进度/存储容错）+ ask 13、search 14 回归不破。
- 与既有问答/检索共存（共享筛选仅复用未改动；factory 仅新增可选参数）。未重跑全量 pytest/模型下载/编码/评测（无共享回归风险）。

## 修改与新增文件

- 新增：`examples/procedures/procedures.json`、`src/campus_assistant/procedures/`（2）、`api/procedures.py`、`static/procedures.html`、`tests/test_procedures.py`、`scripts/check-procedures-behavior.cjs`、`scripts/demo-procedures-api.py`
- 修改：`main.py`（工厂参数+路由/页面）、`demo.py`、`static/ask.html`、`static/search.html`、`static/preview.html`、`scripts/demo-ask-page-mock.py`、两份 README
- 清单见 `changed-files.json`；未修改：Astra 文档、旧题集/gold、T014 证据、既有系统方案。

## 已知限制

- **无浏览器工具**：真实浏览器闭环未执行，stub/mock 证据不冒充；已提供 [demo-notes.md](./demo-notes.md) 可运行步骤交 Astra 补验。
- 合成模板仅覆盖语料所载内容（材料/部门/联系方式多为“资料未说明”），不代表学校指南准确率。
- 本机待办限单浏览器 localStorage；无云同步/导出（设计如此）。
- 核对当前依据为本地比对（哈希/模板版本/筛选），不做通用政策同步。

完成后停止，等待 Astra 验收。T017 未发布。
