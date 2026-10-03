# T018 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦验证：未重跑 embedding、全量测试或旧评测；external_model_calls=0。

## 1. 统一演示相关 pytest（5 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_demo_campus.py -q -p no:cacheprovider --basetemp .cache/t018-iter3 --tb=short -rs
# 5 passed, 2 warnings in 0.60s
# 退出码：0
```

覆盖（对照验收重点）：

- **组合语料**：`test_ids_and_hashes_preserved`（5 文档 ID 全集一致、sha256 与源 manifest 一致、文件字节哈希一致）；`test_parseable_and_sources_untouched`（组合语料解析 valid、5 文档、源夹具 manifest 仍在原处）；`test_id_conflict_aborts_explicitly`（构造重复 ID 双源 → SystemExit“ID 冲突”，不静默覆盖）。
- **统一服务**：`test_all_routes_and_marked_mock`（`/`、/ask、/search、/procedures、/compare、/preview 全 200；generator_identity 含 mock；proc-apply-defer 2024 草稿 saveable=true 模板引用通过；比较组含 syn-cmp-defer/syn-cmp-grades；mock 生成段落含【模拟输出，非真实 DeepSeek 回答】）。
- **配置边界**：`test_demo_entry_never_reads_real_generator_config`（demo-campus.py 不含 provider_from_env/CAMPUS_GENERATOR/DEEPSEEK_API_KEY）。

调试记录：首跑 1 failed（测试误用 demo_campus.create_app——该导入在函数内），改为直接从 campus_assistant.main 导入后全过。

## 2. JS 语法与相关行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 6 HTML files passed syntax check.（退出码 0，home.html 新增）
"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 17 scenarios passed（退出码 0）
"D:/nodejs/node.exe" scripts/check-procedures-behavior.cjs
# check-procedures-behavior: 11 scenarios passed（退出码 0）
```

- ask +4：相关事项链接绑定**结果快照**（procedure_id/admission_year/campus 编码参数；改控件后链接不变）；历史结果链接用**历史条件**（非当前控件）并带“本条历史条件”提示；无匹配不显示推荐；URL query 预填问题。
- procedures +2：带入恢复（等选项加载后设值、横幅“已带入条件（来自问答结果快照）…不会自动保存待办，也不会调用模型”、**零 draft 请求零存储写入**、显式点击才生成）；缺失选项保留值并提示“已保留该条件”。

## 3. 本地 API 演示记录

```bash
./.venv/Scripts/python.exe scripts/demo-campus.py --record-api "F:/Collage Paper/docs/collaboration/submissions/T018/campus-demo.json"
# calls_recorded: 10；all_routes_ok: true
# home/ask-status/search-status/procedures-list/comparison-groups/comparison/
# ask-extractive/ask-generated-mock/procedures-draft/preview-page 全部 200
# 退出码：0
```

记录含组合语料路径与只读源标注；`ask-generated-mock` 响应带【模拟输出】标记（非 DeepSeek 实时回答）。

## 4. 浏览器检查情况（如实说明）

本会话**无浏览器工具**，跨页闭环（首页→问答证据→相关事项→带条件草稿→保存勾选→原文核对→版本对比→返回待办）未由真实浏览器执行；已提供 [demo-notes.md](./demo-notes.md) 的 Astra 可运行入口、5—8 分钟演示脚本与逐步检查表（a—g）。stub 证据不冒充真实浏览器证据；mock 不冒充 DeepSeek 实时回答。

## 5. 未验证项

1. 真实浏览器跨页闭环（交 Astra 补验）。
2. 真实 DeepSeek 生成下的联动表现（本任务零外部调用；T014 历史证据独立保留）。
3. embedding/全量测试/旧评测：算法未改动，按任务不重跑。
4. 真实学校语料下的演示效果（当前为合成语料）。
