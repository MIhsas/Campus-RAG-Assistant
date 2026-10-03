# T018 验证记录（submission_revision=2，responds_to=T018-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。按返工单只运行必要 JS 语法与 procedures 行为验证 + 被改说明涉及的一件测试；未重复 ask/后端/无关测试；external_model_calls=0。revision 1 记录见 `verification.rev1.md`。

## 1. JS 语法与 procedures 行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 6 HTML files passed syntax check.（退出码 0）
"D:/nodejs/node.exe" scripts/check-procedures-behavior.cjs
# check-procedures-behavior: 11 scenarios passed（退出码 0）
```

- **强化因果链场景**（并入导入场景）：带入 `proc-review-grade` + `admission_year=2023` → 选项加载后年份=2023 恢复、横幅“已带入条件（来自问答结果快照）”、事项卡 `selected` 类生效（预选经公共 selectProcedure）；**加载本身零 draft 请求、零存储写入**；显式点击“生成办理步骤草稿”后请求 URL=`…/proc-review-grade/draft`、body.filters.admission_year=2023。
- **缺失选项场景**保留：值 2019 保留 + “已保留该条件”提示。
- **严格桩**：children 为 HTMLCollection 形态（无 forEach/map）、事件存桩外 WeakMap（元素无公开 listeners，测试经 `trigger()`）——页面对数组专有方法或桩内部属性的依赖会立即暴露。修复前的页面代码在此桩下必然失败（children.forEach 抛异常致条件未恢复；无 listeners 致预选失效），故本场景即两处 P1 的回归。

## 2. 说明校正相关测试（1 件）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_demo_campus.py -q -p no:cacheprovider --basetemp .cache/t018r2-iter1 --tb=short -rs
# 5 passed, 2 warnings in 0.63s
# 退出码：0
```

原 `test_demo_entry_never_reads_real_generator_config` 改名为 `test_demo_entry_source_uses_mock_only` 并注明**源码字符串检查非运行时隔离证明**；其余 4 项（组合语料/统一路由/标记 mock）保持通过。

## 3. 未验证项（如实标注）

1. **真实浏览器复验**：留待 Astra。建议复现 rev1 路径 `/procedures?procedure_id=proc-review-grade&query=成绩复核&admission_year=2023`（demo-campus.py 启动）：应显示带入条件横幅、年份=2023、成绩复核卡片选中；点击生成后出现草稿；全程无自动保存/模型请求。
2. ask 页面与后端：本轮未修改，按返工单未重复其测试与全量。
3. 外部模型调用：0。
