# T016 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。按任务聚焦验证；未重跑全量 pytest/模型下载/编码/评测。**external_model_calls=0（无任何外部请求）。**

## 1. 新增后端测试（12 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_procedures.py -q -p no:cacheprovider --basetemp .cache/t016-iter5 --tb=short -rs
# 12 passed, 2 warnings in 0.58s
# 退出码：0
```

覆盖（对照验收重点）：

1. **两事项引用有效、不同年级不混入**：`test_defer_ok_for_2023_without_docx_content`（2023 材料降级“资料未说明”，不出现“需医院证明”）、`test_defer_ok_for_2024_with_materials`（2024 引用 DOCX 表）、`test_grade_review_ok_2024_and_refused_2023`（2024 全通过；2023 saveable=false 且理由“不符合当前筛选条件”）、`test_all_citation_spans_match_original`（跨度=原块切片）、`test_filters_never_relaxed`。
2. **哈希变化/缺失明确不可用**（隔离夹具复制到 tmp，产品语料与旧 gold 未动）：`test_hash_changed_and_missing`（篡改+删除 → saveable=false、source_missing）、`test_verify_changed_missing_source`、`test_verify_changed_hash_update`（manifest 更新哈希后 verify 报“哈希已变化”）、`test_verify_unchanged`、`test_verify_unavailable_and_version_change`。
3. **路由/工厂回归**：默认不加载模板 → 503 PROCEDURES_NOT_CONFIGURED；显式注入 → 列表/草稿/404 正常，search/status 不受影响。

调试记录：两处首轮失败均为测试脚本问题（Windows 文本写入换行翻译导致夹具哈希算错→改按文件字节；verify 断言措辞），修正后全过；另发现并修复 FastAPI 返回注解错误（JSONResponse|dict 不合法）。

## 2. 本地 API 演示（存档 api-demo.json / citation-crosscheck.md）

```bash
./.venv/Scripts/python.exe scripts/demo-procedures-api.py --out-dir "F:/Collage Paper/docs/collaboration/submissions/T016"
# calls_recorded: 7；draft_saveable: {defer-2023: true, defer-2024: true, grade-2024: true, grade-2023: false}
# 退出码：0
```

verify 双分支：同快照 `unchanged`；模板版本 0.9 → `changed`（提示复核）。引用核对表逐条列出原文→步骤与跨度一致性。

## 3. 页面 JS 语法与行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 4 HTML files passed syntax check.（退出码 0）
"D:/nodejs/node.exe" scripts/check-procedures-behavior.cjs
# check-procedures-behavior: 7 scenarios passed（退出码 0）
"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 13 scenarios passed（退出码 0，T015 整理不破回归）
"D:/nodejs/node.exe" scripts/check-search-behavior.cjs
# check-search-behavior: 14 scenarios passed（退出码 0）
```

procedures 7 场景：草稿引用渲染与保存门槛、资料不足禁用保存、保存前零持久化+防重复提交+另存、刷新恢复零请求+进度勾选、备注/个人步骤/提醒排序（升序空日期置后）/删除/筛选、核对变化保留进度与备注、存储不可用不显保存成功且草稿可看。
调试记录：修复页面真 bug 一处（修改写回闭包旧对象被持久化覆盖——排序/勾选丢失；改为按 id 在最新存储上修改）与保存失败无提示一处；测试端修正 verify 未 resolve、input.value 断言、排序期望。

## 4. T015-R1 三项整理实测

```bash
./.venv/Scripts/python.exe scripts/demo-ask-page-mock.py --port 8013 &   # 本会话启动并停止
curl POST /api/v1/ask {"query":"缓考申请模拟不足",...}
# status=insufficient_evidence | evidence_state=ok | evidence: 5
# reason: 【模拟输出】材料不足（mock）。
```

第 2 项达成：含可检索词 → 命中证据 → 进入 mock 不足分支（不再是 no_hits 短路）。第 1 项（pageshow 同步）与第 3 项（复制按钮文案）经代码与 ask 行为 13 场景回归覆盖。

## 5. 浏览器检查情况（如实说明）

本会话**无浏览器工具**，完整闭环（选择→草稿→保存→进度/备注/提醒→刷新恢复→核对依据）未由真实浏览器执行；已提供 [demo-notes.md](./demo-notes.md) 的 Astra 可运行入口与逐步核验表。stub/mock 证据不冒充真实浏览器证据。

## 6. 未验证项

1. 真实浏览器闭环（交 Astra 补验，步骤见 demo-notes.md）。
2. 真实学校语料下的办事指南准确性（当前为合成模板原型，未接真实语料，不从网上补政策）。
3. 全量 pytest/embedding/评测：按任务不重跑（共享代码仅复用未改动；factory 仅加可选参数并经 12 项相关测试）。
4. localStorage 大容量/多标签页并发场景（未做边界矩阵，按任务省略）。
