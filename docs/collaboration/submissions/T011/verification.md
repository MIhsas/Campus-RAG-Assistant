# T011 验证记录（submission_revision=2）

对象：T011-R1 定向返工（P1：搜索成功后状态刷新清空筛选）。工作目录 `F:\Collage Paper\step2_code\backend`。按返工单，本轮**仅**运行变更页面的 JS 语法与行为检查；未重复全量 pytest、pip check、模型编码与三模式评测（revision 1 已通过并经 Astra 独立复核，完整记录见 `verification.rev1.md`，此处不重复）。本轮未修改后端代码，无需补后端检查。

## 1. JS 语法检查

```bash
cd "F:\Collage Paper\step2_code\backend"
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# preview.html: syntax OK
# search.html: syntax OK
# All 2 HTML files passed syntax check.
```

退出码：0。

## 2. 行为检查（含 T011-R1 因果链回归）

```bash
"D:/nodejs/node.exe" scripts/check-search-behavior.cjs
# check-search-behavior: 14 scenarios passed
```

退出码：0。14 = 旧 12 场景（空白取消 2、A→B 竞态 2、失败重试 3、mode/query/filters 重试快照、条件快照、清除条件、筛选空态、语义按 hits 展示）+ 本修订新增 2：

- Test 9（R1 指定回归）：选条件→成功搜索→等 status 刷新完成→控件全保留（含等待期间的编辑）→再次搜索仍带原条件。stub status 含可选值（成都校区/都江堰校区、全日制本科、2024/2025）。
- Test 10：选项消失时条件保留（以选项项形式）并在状态区提示，下一次请求仍携带该条件。

## 3. 负向对照（证明回归有效性）

将 `search.html` 临时退回旧逻辑（选项未变也重建 + 重建时清空选择；内存级两行改动），重跑行为脚本：

```bash
"D:/nodejs/node.exe" scripts/check-search-behavior.cjs
# FAIL: campus survives status refresh
# '' !== '成都校区'
```

退出码：1。失败点即 R1 复现链的观测点。随即还原两行并重跑语法与行为检查：14 scenarios passed、2 files passed（退出码 0/0）。当前 `search.html` 为修复后最终代码（见 changed-files.json 哈希）。

## 4. 证据层级与未验证项

- 以上行为检查为 DOM/fetch stub 级证据，非真实浏览器。
- **真实浏览器补验**（筛选→搜索→查看原文→清除条件，及一次错误重试）：本轮无浏览器工具，按 T011-R1 交 Astra 实测。错误重试沿用原提交参数的行为已在 stub 级 Test 3/4/9 覆盖。
- revision 1 的全量回归（404 passed、1 skipped）、pip check、真实模型筛选演示与三模式评测记录见 `verification.rev1.md`；本轮未重复、未修改其结论范围。
