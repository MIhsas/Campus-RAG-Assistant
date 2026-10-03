# T017 本地演示记录与步骤

## 证据层级（先读）

| 层级 | 内容 | 性质 |
|---|---|---|
| 后端 pytest | `tests/test_comparison.py` 10 项 + `test_search_api.py` 工厂回归 | 真实本地运行 |
| 页面 stub 行为 | `check-comparison-behavior.cjs` 5 场景 | **不是**真实浏览器证据 |
| 本地 API 演示 | `comparison-demo.json`（5 次调用）+ `comparison-expectations.md`（手工对照） | 合成虚构政策，零外部调用 |

本轮无浏览器工具：真实浏览器闭环未由本会话执行，以下步骤交 Astra 补验。

## Astra 可运行的本地演示步骤（PowerShell）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-comparison-page.py --port 8020
# 打开 http://127.0.0.1:8020/compare
```

闭环核验表（选择两个版本 → 四类条款 → 两侧原文与适用范围 → 复制差异摘要）：

| 步骤 | 操作 | 预期 |
|---|---|---|
| a 分组与版本 | 页首下拉 | 分组 `syn-cmp-defer（2 个版本）`、`syn-cmp-grades（1 个版本）`；选择 defer 后左右版本为 cmp-defer-v1/cmp-defer-v2 |
| b 版本元数据 | 查看两侧卡片 | 虚构 2024 版/虚构 2025 版、发布/生效/失效日期、适用范围（标注非资格结论）、合成标记；缺失项显示“未标注/未标注截止” |
| c 对比 | 点“对比” | 计数条：新增 1、删除 1、修改 1、未变 3；**文字标签**“修改/删除/新增”明确（不只靠颜色） |
| d 默认视图 | 默认只看变化 | 显示 第二条（修改）、第三条（删除）、第四条（新增）；第一条未变默认隐藏 |
| e 显示全部 | 勾选“显示全部条款” | 第一条（未变）出现 |
| f 两侧原文 | 展开条款 | 左/右原文完整显示（标注字符数，不截断）；“查看原文”分别跳转 `/preview#…` |
| g 修改细节 | 查看第二条 | 句内差异标记：删除“5”、插入“3”，整段原文逐字保留 |
| h 交换左右 | 点“交换左右”→ 对比 | 左右互换后新增/删除互换（第三条变新增、第四条变删除） |
| i 复制摘要 | 点“复制差异摘要” | 纯文本含左右版本身份、【修改】【删除】【新增】标签、条款原文与来源标识 |
| j 失败不冒充 | 选择跨组版本（defer ↔ grades）→ 对比 | 明确报“只能比较同一政策分组下的版本（未生成新比较结果）”，旧结果不冒充新比较 |
| k 导航 | /search /ask /procedures /preview 头部 | 均有“版本对比”入口 |

## 本地 API 演示（已实跑，存档于 comparison-demo.json）

```powershell
& .\.venv\Scripts\python.exe scripts\demo-comparison-api.py --out-dir 'F:\Collage Paper\docs\collaboration\submissions\T017'
```

5 次调用：groups、compare v1→v2（1/1/1/3）、compare v2→v1（新增/删除互换）、同文档 400、跨组 400。**手工期望分类与程序结果对照**见 `comparison-expectations.md`（6 行全部一致）。

## 边界说明

- 对比为条款**文字差异**：不判断版本适用性；日期较新≠现行有效，旧版本≠失效版本（页面与响应均有说明）。
- 对比只反映服务器当前已加载语料：更新 `examples/comparison-corpus/` 后需**重启演示**重新加载，不监控磁盘。
- 默认产品启动不注入合成比较语料（演示入口显式注入）。
