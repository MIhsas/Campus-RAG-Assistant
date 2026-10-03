# T017 本地演示记录与步骤（submission_revision=2）

## 证据层级（先读）

| 层级 | 内容 | 性质 |
|---|---|---|
| 后端 pytest | `tests/test_comparison.py` 14 项（含 T017-R1 正反向回归） | 真实本地运行 |
| 独立探针 | Astra 的 `T017-R1-probe.py` 退出 0（正向 新增1/修改1；反向 删除1/修改1） | 真实本地运行 |
| 页面 stub 行为 | `check-comparison-behavior.cjs` 5 场景 | **不是**真实浏览器证据 |
| 本地 API 演示 | `comparison-demo.json`（5 次调用）+ `comparison-expectations.md` | 合成虚构政策，零外部调用 |

本轮无浏览器工具：真实浏览器闭环未由本会话执行，以下步骤交 Astra 补验。**浏览器复制实测留待 Astra 复验**（T017-R1 记录 Astra 本轮未取得非空剪贴板内容，不伪称已验证）。

## Astra 可运行的本地演示步骤（PowerShell）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-comparison-page.py --port 8020
# 打开 http://127.0.0.1:8020/compare
```

| 步骤 | 操作 | 预期 |
|---|---|---|
| a 分组与版本 | 页首下拉 | `syn-cmp-defer（2 个版本）`、`syn-cmp-grades（1 个版本）`；左右版本 cmp-defer-v1/cmp-defer-v2 |
| b 版本元数据 | 查看两侧卡片 | 虚构 2024 版/2025 版、发布/生效/失效、适用范围（非资格结论）、合成标记；缺失显示“未标注/未标注截止” |
| c 对比 | 点“对比” | 计数 新增 1、删除 1、修改 1、未变 3；明确文字标签（不只靠颜色）；算法限制说明含**“不含表格差异”** |
| d 默认视图 | 默认只看变化 | 第二条（修改）、第三条（删除）、第四条（新增）；未变计数仍显示 |
| e 显示全部 | 勾选“显示全部条款” | 第一条（未变）出现 |
| f 两侧原文 | 展开条款 | 左/右原文完整（标注字符数，不截断）；“查看原文”分别跳转 |
| g 修改细节 | 查看第二条 | 句内差异：删除“5”、插入“3”，整段原文逐字保留 |
| h 交换左右 | “交换左右”→对比 | 新增/删除互换（第三条变新增、第四条变删除），快照显示 v2↔v1 |
| i 复制摘要 | 点“复制差异摘要” | 纯文本含左右版本身份、【修改】【删除】【新增】标签、条款原文与来源（**浏览器剪贴板实测留待 Astra 复验**） |
| j 同文档失败 | 左右均选 cmp-defer-v1 → 对比 | 旧结果清除，显示“左右不能选择同一文档（未生成新比较结果）” |
| k 导航 | /search /ask /procedures /preview 头部 | 均有“版本对比”入口 |

**跨组拒绝**用 API 验证（页面下拉按分组联动，无法选出跨组组合）：`comparison-demo.json` 的 `reject-cross-group` 调用返回 400 `CROSS_POLICY_GROUP`（`demo-comparison-api.py` 实跑记录）。

## 本地 API 演示（已实跑）

```powershell
& .\.venv\Scripts\python.exe scripts\demo-comparison-api.py --out-dir 'F:\Collage Paper\docs\collaboration\submissions\T017'
```

5 次调用：groups、v1→v2（1/1/1/3）、v2→v1（新增/删除互换）、同文档 400、跨组 400。手工期望对照 `comparison-expectations.md` 全部一致。

## 边界说明（rev2 明确）

- 对比为条款**文字差异**：不判断适用性；日期较新≠现行有效，旧版本≠失效版本。
- **仅比较段落块，不含表格差异**（表格块不参与对比；用于 DOCX 勿把未展示的表格变化当作无变化）。
- 重复条号中未参与标识配对的其余同号条款**直接归入新增/删除**（不做正文匹配）。
- 对比只反映服务器当前已加载语料：更新夹具后需重启演示；默认产品启动不注入合成数据。
