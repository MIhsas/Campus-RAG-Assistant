# T017 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。聚焦验证：未跑 embedding、全量评测或无关测试；全程 external_model_calls=0。

## 1. 合成语料校验

```bash
./.venv/Scripts/python.exe -m campus_assistant.corpus.validate --manifest examples/comparison-corpus/manifest.json --corpus-root examples/comparison-corpus
# {"valid": true, "document_count": 3, "errors": []}
# 退出码：0
```

调试记录：首版夹具条款间无空行，TXT 解析将三条合并为一块（分类塌缩）；改为条款各自成块后正常。另发现 parse 块不带 char 区间——对比条目跨度定义为整块 `[0, len)`，与解析块逐字一致（测试核对）。

## 2. 相关 pytest（42 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_comparison.py tests/test_search_api.py -q -p no:cacheprovider --basetemp .cache/t017-iter4 --tb=short -rs
# 42 passed, 2 warnings in 1.43s
# 退出码：0
```

- `test_comparison.py`（10 项）：
  - **分类正确**：夹具 v1↔v2 为 {added:1, deleted:1, modified:1, unchanged:3}；第一条未变、第二条修改（diff_segments 删除“5”插入“3”）、第三条删除、第四条新增。
  - **新增不致错位**：内存文档 A/B/C ↔ A/插入块/B/C → 三条全部未变、仅 1 新增（标识优先配对，不受列表位置影响）。
  - **交换左右**：added/deleted 互换，modified/unchanged 对称。
  - **跨度一致**：每条 entry 的 `block.text[char_start:char_end] == text`（与解析块一致）+ sha256/preview_url 存在。
  - **约束**：同文档 LEFT_RIGHT_SAME、跨组 CROSS_POLICY_GROUP（pytest.raises + API 400）。
  - 未编号修改配对（相似度配对为修改）；groups 列表结构。
- `test_search_api.py`（32 项）：main.py 路由/页面变更的必要工厂回归，全部通过。
- 首轮 4 failed 已定位修复（夹具合并块 + span 语义 + 一处测试期望写错），修复后全过。

## 3. JS 语法与页面行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 5 HTML files passed syntax check.（退出码 0）
"D:/nodejs/node.exe" scripts/check-comparison-behavior.cjs
# check-comparison-behavior: 5 scenarios passed（退出码 0）
"D:/nodejs/node.exe" scripts/check-search-behavior.cjs   # 14 scenarios passed（退出码 0）
"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs      # 13 scenarios passed（退出码 0）
"D:/nodejs/node.exe" scripts/check-procedures-behavior.cjs # 9 scenarios passed（退出码 0）
```

comparison 5 场景：请求携带左右 ids 与快照行/四类计数与明确文字标签/交换后请求 sides 对换/默认只看变化（未变计数仍显示）与显示全部/复制摘要含版本身份·差异类型·原文·来源/失败显示“未生成新比较结果”且旧结果不冒充。search/ask/procedures 回归因四页仅加导航链接而作必要回归，全部不破。

## 4. 本地 API 演示与手工对照

```bash
./.venv/Scripts/python.exe scripts/demo-comparison-api.py --out-dir "F:/Collage Paper/docs/collaboration/submissions/T017"
# calls_recorded: 5；counts: {added:1, deleted:1, modified:1, unchanged:3}
# 退出码：0
```

- `comparison-demo.json`：groups、v1→v2、v2→v1（新增/删除互换）、同文档 400、跨组 400。
- `comparison-expectations.md`：**手工期望分类与程序结果对照**——6 行全部一致（前言/标题/第一条未变、第二条修改、第三条删除、第四条新增），计数 1/1/1/3 一致。

## 5. 浏览器检查情况（如实说明）

本会话**无浏览器工具**，页面闭环未由真实浏览器执行；已提供 [demo-notes.md](./demo-notes.md) 的 Astra 可运行入口与逐步核验表（a—k）。stub 证据不冒充真实浏览器证据。

## 6. 未验证项

1. 真实浏览器闭环（交 Astra 补验）。
2. 真实学校语料的版本对比效果（当前为合成虚构政策夹具）。
3. 全量 pytest/embedding/评测：按任务不跑。
4. 条款重编号/移动/重复标识的复杂对齐：按任务不开发，限制已在响应与 README 声明。
