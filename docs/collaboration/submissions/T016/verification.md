# T016 验证记录（submission_revision=2，responds_to=T016-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。按返工单只跑相关 pytest 与 procedures 页面语法/行为；**未修改 ask/search，未重复其测试与全量 pytest**；无外部模型调用。revision 1 验证记录见 `verification.rev1.md`。

## 1. 相关 pytest（14 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_procedures.py -q -p no:cacheprovider --basetemp .cache/t016r2-iter3 --tb=short -rs
# 14 passed, 2 warnings in 0.58s
# 退出码：0
```

- 原 12 项全部保持通过（两事项引用/防混入/隔离哈希缺失/verify 三分支/路由工厂）。
- 新增 2 条 R1 因果链：
  - `test_excluded_content_never_in_draft_output`：2023 缓考草稿**完整 JSON 输出**无“需医院证明/3个工作日”（非仅 detail 字段），保留“资料未说明/来源不符合当前筛选条件”；2024 对照含有效材料引用；成绩复核 2023 失效步骤 detail=null 且无“10个工作日内/仅查分不查卷”。
  - `test_verify_checks_adopted_optional_citations`：2024 缓考快照含已采用可选引用——原语料 `unchanged`；隔离夹具 DOCX 缺失 → `changed`（issues 指名“确认材料与办理时点”）；隔离夹具哈希更新 → `changed`（“哈希已变化”）。

调试记录：首跑 1 failed（断言把页面渲染文案“未作为可用办理依据”误当服务输出字段），改断言服务语义后全过。

## 2. procedures 页面 JS 语法与行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 4 HTML files passed syntax check.（退出码 0）
"D:/nodejs/node.exe" scripts/check-procedures-behavior.cjs
# check-procedures-behavior: 9 scenarios passed（退出码 0）
```

- 原 7 场景保持通过；新增 2 条：
  - **链 1**（stub）：2023 草稿渲染无“需医院证明/3个工作日”、含“资料未说明/未作为可用办理依据/待核实或未说明项”横幅；保存后 localStorage 串仍无被排除内容；刷新恢复的待办无被排除内容且含“待核实”；2024 对照渲染含有效引用“需医院证明”。
  - **链 3**（stub）：成功草稿→换条件再生成→503：请求开始即禁用保存、失败后保持禁用、点击保存零写入、横幅含“旧草稿已失效”。

## 3. 本地 API 演示输出（重生成）

```bash
./.venv/Scripts/python.exe scripts/demo-procedures-api.py --out-dir "F:/Collage Paper/docs/collaboration/submissions/T016"
# calls_recorded: 7；draft_saveable: {defer-2023: true, defer-2024: true, grade-2024: true, grade-2023: false}
# 退出码：0
```

对 `api-demo.json` 的修复断言（真实输出核对）：2023 缓考响应无“需医院证明/3个工作日”、含“资料未说明”；2024 缓考含有效材料引用；2023 成绩复核无“10个工作日内/仅查分不查卷”；verify unchanged/changed 双分支正常。引用核对表（`citation-crosscheck.md`）对未准入引用标注“不作为可用依据，原文内容不输出”。

## 4. 未验证项（如实标注）

1. **完整待办闭环的真实浏览器复验**：按返工单留待修复后由 Astra 补验（本轮 stub 覆盖渲染/保存/恢复链；上轮 Astra 浏览器已补验准入混入）。stub 不冒充真实浏览器证据。
2. ask/search 与全量测试：未修改其代码，按返工单不重复。
3. 产品语料与 gold：未改动（隔离夹具均在 pytest tmp 目录）。
4. 外部模型调用：0。
