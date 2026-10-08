# T032 演示说明（demo-notes.md）

## 启动命令（真实资料 + 显式装配模板）

```powershell
# step2_code/backend 下（PowerShell）；默认 BM25，不要求向量/ASR/生成器
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
    --manifest ..\..\data\corpora\sicau-rag-pilot-v1.1\manifest.json `
    --corpus-root ..\..\data\corpora\sicau-rag-pilot-v1.1 `
    --procedures ..\..\data\procedures\sicau-transfer-2026-v1\procedures.json `
    --port 8010
# 浏览器打开 http://127.0.0.1:8010/procedures
```

- 普通启动（不带 `--procedures`）不加载任何模板，维持既有行为；合成演示模板仍可由测试/演示显式启用（原样保留）。
- 本轮不启用 DeepSeek/生成器/向量/ASR；零外部调用。

## 已完成的自动化证据（非浏览器实证）

- `api-demo.json`（`scripts/demo-t032-procedures.py`，exit 0）：模板列出（is_synthetic=false、文号/2026 版标题）；无条件与 student_type=本科 草稿均 saveable、20/20 引用 ok；**排除条件**（as_of_date=2020-01-01，早于生效日 2026-01-08）→ saveable=false、失败引用 quote 为 null（不泄漏失效原文）、失败步骤 detail 抑制；保存快照 verify=**unchanged**；篡改跨度后 verify=changed。
- 引用程序化核对 `verify-procedures-citations.py`：20/20 ok，exit 0（见 citation-crosscheck.md）。
- 页面回归：`check-js-syntax.cjs` 9 页全过；`check-procedures-behavior.cjs` 11 场景全过（exit 0）；`tests/test_procedures.py` 14 passed。

## 真实浏览器工具

**本执行环境没有真实浏览器工具**，未做浏览器实证，不代签。以下短清单供 Astra 复验（约 5 分钟）。

## Astra 短清单

| # | 操作 | 预期 |
|---|---|---|
| 1 | 打开 /procedures 事项列表 | 「本科生转专业办理清单（校教发〔2026〕1号·2026版）」，无「合成演示」徽标；顶部提示含“不代表…受理或资格认证；不判定资格、不保证申请成功” |
| 2 | 选择该事项 → 生成草稿 | 13 步逐步展示；每步含逐字引用（可点「查看原文」跳 /preview#5cb2ac21…）；标注“资料未说明”的项不编造 |
| 3 | 核对 t1/t2/t8/t12 | 关键例外在步骤明示：2024 及之前入学按〔2023〕1号（不适用本清单）、艺体中外合作仅同类互转、跨校区资格放弃不得再次申请、注册前受处分取消资格、学籍生效不得撤销 |
| 4 | 保存到我的待办 | 仅 saveable 时可保存；保存提示“个人待办（本机）…不提交申请”；勾选 2 项、写备注、设提醒日期 |
| 5 | 刷新页面 | 待办、勾选、备注、提醒全部保留（本机 localStorage） |
| 6 | 点「核对当前依据」 | 绿条“已核对当前依据：与保存时一致”（verify=unchanged） |
| 7 | 筛选条件改 as_of_date=2020-01-01 → 生成草稿 | 横幅“资料不足/依据需更新”、不可保存；被排除引用不显示原文内容 |
| 8 | 对照查看 /preview 原文 | 5cb2ac21 文档 5 页原文与步骤引用一致 |
