# T018 统一演示入口与问答办事联动 — 实施报告（submission_revision=2）

日期：2026-09-27。task_id=T018、task_revision=v1、submission_revision=2、responds_to=T018-R1、status=ready_for_review、**external_model_calls=0**。

> 修订记录：revision 2 为 T018-R1 定向返工（条件恢复兼容 HTMLCollection、事项预选走公共选择逻辑、测试桩校正、隔离/首页说明校正），详见 [fix-report.md](./fix-report.md)。revision 1 历史副本：`report.rev1.md` 等 4 件。下文为任务整体实施说明（rev1 内容保持），其中“不读取真实生成器配置”的表述以 fix-report 的校正为准。

## 概述

把问答、证据搜索、办事与待办、版本对比、原文预览接入同一个离线演示服务（统一首页 + 单条启动命令），并建立“提问 → 相关办事事项 → 带条件草稿”的明确入口。复用既有业务（检索/生成/对比算法零改动），不引入新框架/数据库。

## 功能交付（对照任务书）

1. **统一离线演示入口** `scripts/demo-campus.py`：单条命令服务全部功能；`--record-api` 模式输出本地 API 演示记录（10 路由全 200）。
2. **组合演示语料**：启动时将 parse-corpus 与 comparison-corpus 重建组合到 `.cache/demo-campus-corpus/`——保留原文档 ID、文件内容与哈希（逐字节校验），两份原始夹具与 gold 只读不动；文档 ID 冲突显式报错；每次启动干净重建。
3. **标记 mock 生成器**：显式注入 `CampusMockProvider`，模拟回答带【模拟输出，非真实 DeepSeek 回答】；演示 app 不向真实服务发请求（表述已按 T018-R1 校正，不声称整个导入链的运行时隔离）。
4. **统一首页 `/`**：五功能入口 + 三条可点击演示问题（URL 预填）+ 状态行实时读取当前服务（非写死）；五页“首页”回链。说明文案限定 demo-campus 启动方式（rev2 校正）。
5. **问答→办事联动**：结果带“相关事项入口”（显式关键词映射，稳定 procedure_id，无匹配不推荐，标注不代表符合办理条件），链接携带**该结果**的问题与筛选快照（不含答案原文/密钥）。
6. **办事页带入**（rev2 修复后）：等选项加载后用 HTMLCollection 兼容方式恢复条件、缺失选项保留并提示；公共 `selectProcedure` 预选事项（卡片点击与 URL 共用）；显式“已带入条件”横幅；仍需手动生成草稿——不自动保存/调模型。
7. **历史快照**：历史结果的事项入口携带历史条件并注明“按当前加载资料重新生成指南”；重试/失败转摘录/历史行为未动。
8. **答辩演示脚本**：[demo-notes.md](./demo-notes.md)（Windows 单条启动 + 5—8 分钟逐步脚本 + Astra 检查表）。

## 验证摘要（rev2 聚焦 + rev1 证据保留）

- **rev2**：JS 语法 6 页、`check-procedures-behavior.cjs` 11 场景（含强化因果链：带入 2023+成绩复核→预选→手动生成提交正确 procedure_id/filters、加载零请求）、`tests/test_demo_campus.py` 5 passed（说明校正后仍绿）。详见 [verification.md](./verification.md) 与 [fix-report.md](./fix-report.md)。
- **rev1 证据保留**：`campus-demo.json` 10 路由全 200；ask 17 场景、procedures 基础 9 场景；组合语料 ID/哈希/冲突测试。本轮未改 ask 与后端，未重复其测试。

## 修改与新增文件（累计）

- rev1：`scripts/demo-campus.py`、`static/home.html`、`tests/test_demo_campus.py`、`main.py`、五页导航/联动、两个行为脚本、README。
- rev2：`static/procedures.html`、`scripts/check-procedures-behavior.cjs`、`scripts/demo-campus.py`/`static/home.html`/`tests/test_demo_campus.py`（说明校正）。
- 清单见 `changed-files.json`；未修改：Astra 文档、原语料夹具/gold、已验收算法、ask 页面与后端。

## 已知限制

- **无浏览器工具**：rev1/rev2 的真实浏览器复验均留待 Astra（rev1 已由 Astra 复现并定位 P1；rev2 修复的复验路径见 fix-report）。stub 不冒充浏览器证据。
- mock 输出不是 DeepSeek 实时回答；T014 一次限定真实冒烟为独立历史证据。
- 组合语料为合成虚构政策；不代表学校真实政策准确率。

完成后停止，等待 Astra 验收。T019 未发布。
