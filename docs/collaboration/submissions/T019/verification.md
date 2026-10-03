# T019 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦验证：未重跑 embedding、全量旧测试或无关矩阵；external_model_calls=0。

## 1. 新增 pytest（11 项）与受影响聚焦回归

```bash
./.venv/Scripts/python.exe -m pytest tests/test_procedures.py tests/test_demo_campus.py tests/test_self_check.py -q -p no:cacheprovider --basetemp .cache/t019-iter2 --tb=short -rs
# 30 passed, 2 warnings in 0.88s
# 退出码：0
```

- `test_self_check.py`（11 项）：
  - **判定组合**：`test_all_satisfied`（含“仍需学校审核/不构成录取、批准或申请成功”措辞）、`test_unknown_never_satisfied`（未参加考核→待核实，含“未知不计为满足”）、`test_unsatisfied_plus_unknown`（否+未知并存→存在未满足项；未参加与明确未通过区分）、`test_missing_answers_count_as_unknown`。
  - **依据失效**：`test_basis_insufficient_on_filter_exclusion`（年级 1900 不放宽筛选→依据不足、各项 basis_unavailable、失效引用 quote=null）、`test_basis_insufficient_on_hash_change`（隔离夹具哈希更新→hash_changed→依据不足）。
  - **绑定与路由**：`test_citation_spans_match_original`（4 条引用跨度=原块切片）、`test_items_cover_four_conditions`（四项+肯否方向 satisfied_when=yes）、`test_citations_server_bound_with_preview`、`test_not_configured_503`、`test_configured_flow`（rule 结构/非法答案 422/最小语料下依据不足如实报）。
- 受影响聚焦回归：`test_procedures.py` 14 项（共享核查被复用未改动）、`test_demo_campus.py` 5 项（工厂新增 self_check_path 参数）全过。

调试记录：demo 脚本首跑一处 f-string 闭合括号笔误（SyntaxError），修复后四场景判定全部符合设计（管道退出码一度误取 tail 值，已用 PIPESTATUS 复核真实退出码 0）。

## 2. JS 语法与页面行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 7 HTML files passed syntax check.（退出码 0，self-check.html 新增）
"D:/nodejs/node.exe" scripts/check-self-check-behavior.cjs
# check-self-check-behavior: 6 scenarios passed（退出码 0）
```

6 场景：四项三态表单渲染（含“不收集：姓名、学号、违纪详情”）与提交；结果快照（已填输入+条件）与逐项状态/原文引用/查看原文；全满足措辞（仍需学校审核）；改表单不改写旧结果、重查替换新结果；失败明示“未生成新结果”且不冒充；依据不足（失效引用“不作为自查依据”）与个人不满足明确区分；清空表单保留结果。产品代码仅用原生 DOM 兼容访问（索引遍历 children、无桩内部属性）。

## 3. 本地 API 示例与规则原文对照

```bash
./.venv/Scripts/python.exe scripts/demo-selfcheck-api.py --out-dir "F:/Collage Paper/docs/collaboration/submissions/T019"
# calls_recorded: 5；verdicts: all_satisfied / has_unknown / has_unsatisfied / insufficient_basis
# 退出码：0（PIPESTATUS 复核）
```

- `selfcheck-api-demo.json`：rule-info + 四场景请求/响应示例。
- `rule-text-crosscheck.md`：四条规则项与第五条原文逐条对照（问题/原文 quote/块与区间/判定语义）。
- 统一演示入口复核：`demo-campus.py --record-api` 12 路由全 200（含 self-check-rule/self-check-eval，临时记录于 .cache）。

## 4. 浏览器检查情况（如实说明）

本会话**无浏览器工具**，页面闭环（表单→自查→逐项引用→改重查/清空）未由真实浏览器执行；已提供 [demo-notes.md](./demo-notes.md) 的 Astra 可运行入口、四场景与逐步检查表（a—f）。stub 不冒充浏览器证据。

## 5. 未验证项

1. 真实浏览器闭环（交 Astra 补验）。
2. 真实校园资格判断准确性（合成规则原型，不作此宣称）。
3. embedding/全量旧测试/无关矩阵：按任务不重跑。
4. ask 页转专业→自查入口：任务可选项，未实现。
