# T017 政策版本对比 — 实施报告

身份：task_id=T017、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**（零外部模型调用）。

## 概述

交付“选择同一政策两个版本 → 新增/删除/修改/未变条款 → 两侧原文与适用范围 → 复制差异摘要”的完整闭环。确定性文本对比（无模型总结），沿用 FastAPI 与静态页面；文字差异不判断版本适用性——日期较新不称现行有效，旧版本不等于失效版本。

## 功能交付（对照任务书）

1. **独立合成比较语料** `examples/comparison-corpus/`（未动 parse-corpus 与既有 gold）：同组 `syn-cmp-defer` 两个虚构版本（缓考申请办法：第一条未变、第二条修改 5→3 个工作日、第三条删除、第四条新增）+ 异组 `syn-cmp-grades` 一份（跨组拒绝验证）。文件内明确“虚构政策，仅用于版本对比演示”。
2. **服务与 API**（`comparison/service.py` + `api/comparison.py` + main.py 注册）：GET `/api/v1/comparison/groups`（按 policy_group_id 分组列版本）、POST `/api/v1/comparison`（左右 document_id）；拒绝同文档（LEFT_RIGHT_SAME）与跨组（CROSS_POLICY_GROUP）400；返回两侧元数据（版本/日期/适用范围/哈希）、四类计数、块级差异条目（两侧原文、跨度、文档身份、来源预览链接）。
3. **确定性对齐**：① 第X条标识优先配对（**新增一条不会使后续条款错位**——独立回归验证）→ ② 未编号正文保持顺序精确匹配 → ③ 未编号剩余相似度配对为修改 → ④ 其余新增/删除。修改条目标句内差异（diff_segments），两侧整段原文逐字保留；响应 `algorithm.limitations` 说明条款重编号/移动/重复标识限制。
4. **页面** `static/compare.html`：分组/左右版本选择、交换左右、对比、四类计数、**明确文字标签**（不只靠颜色）、默认只看变化/显示全部、左右对应条款卡片、原文展开（标注字符数不截断）与两侧“查看原文”跳转、复制差异摘要（版本身份+差异类型+原文+来源）。结果绑定提交时版本快照（响应回显），新请求即清空旧结果、失败明示“未生成新比较结果”（不冒充成功）。
5. **导航互通**：search/ask/procedures/preview 四页增加“版本对比”入口（仅加链接行，未重构旧页面）。
6. **README**：算法说明、演示命令、语料更新需重启（无磁盘监控）、旧版本≠失效版本表述。独立演示入口 `scripts/demo-comparison-page.py` 显式注入比较语料；默认产品启动不注入合成数据。

## 验证摘要（聚焦，真实命令见 verification.md）

- **pytest 42 项通过**：`test_comparison.py` 10 项（四类分类正确、句内差异 5→3、跨度=解析块全量 [0,len) 逐字一致、交换后新增删除互换、插入不致后续假修改、未编号修改配对、同文档/跨组拒绝、路由与 503）+ `test_search_api.py` 32 项工厂回归（main.py 路由变更必要回归）。
- **JS**：5 页语法 + comparison 行为 5 场景（请求 ids/标签计数/交换/只看变化与显示全部/复制摘要/失败不冒充旧结果）+ search 14、ask 13、procedures 9 回归不破（四页仅加导航链接，作必要回归）。
- **本地 API 演示**：comparison-demo.json（5 次调用）与**手工期望对照** comparison-expectations.md——6 行分类全部一致、计数 1/1/1/3 一致。
- 未跑 embedding/全量评测；未改产品语料/gold；全程零外部调用。

## 修改与新增文件

- 新增：`examples/comparison-corpus/`（3 文本 + manifest）、`comparison/`（2）、`api/comparison.py`、`static/compare.html`、`tests/test_comparison.py`、`scripts/check-comparison-behavior.cjs`、`scripts/demo-comparison-page.py`、`scripts/demo-comparison-api.py`
- 修改：`main.py`（路由+页面）、`static/search.html`、`static/ask.html`、`static/preview.html`、`static/procedures.html`（导航链接）、`README.md`
- 清单见 `changed-files.json`；未修改：Astra 文档、旧 gold、parse-corpus、既有系统方案。

## 已知限制

- **无浏览器工具**：真实浏览器闭环未执行；[demo-notes.md](./demo-notes.md) 提供 Astra 可运行入口与逐步核验表；stub 不冒充真实浏览器证据。
- 对齐算法限制：条款重编号识别为删除+新增、条款移动识别为删除+新增、同文档重复标识仅首个参与标识配对（响应与 README 均已声明）。
- 合成虚构政策不代表真实学校规定；对比不构成版本适用性或资格结论。

完成后停止，等待 Astra 验收。T018 未发布。
