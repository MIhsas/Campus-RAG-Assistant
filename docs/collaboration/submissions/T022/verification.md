# T022 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦装配与状态真实性验证；未重测底层解析/ASR 识别质量/全部检索算法；未下载新模型；零外部调用；未读取/打印密钥。

## 1. 装配与状态测试（25 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_run_entry.py tests/test_pdf_corpus.py tests/test_demo_campus.py -q -p no:cacheprovider --basetemp .cache/t022-iter2 --tb=short -rs
# 25 passed, 2 warnings in 4.14s
# 退出码：0
```

- `test_run_entry.py`（9）：默认全关（bm25-only、生成器/ASR/模板/规则未配置、无隐式合成装载）；显式注入才 200；缺配置降级消息（BM25/文字提问/摘录可用）；生成器“请求启用但配置不完整→已降级”；**计数桩：启动/状态/摘录 0 调用，显式生成 1 调用**；中性首页无“演示问题”、demo_home 首页保留；R1 整理（启动命令引号、is_synthetic 严格布尔两分支、true 原值保留）。
- `test_pdf_corpus.py`（11，含 R1 跨度独立对照：API evidence `block.text[start:end]==ev.text` 对解析块核对）+ `test_demo_campus.py`（5，demo_home 变更回归）。
- 说明：T021-R1 指出 verification 中“91”为含新增的总数口径；本轮同样按“合计 25”表述。

## 2. 配置组合 → 预期/实测（六组合全一致）

```bash
./.venv/Scripts/python.exe scripts/demo-run-configs.py --out-dir "F:/Collage Paper/docs/collaboration/submissions/T022"
# rows_ok: [true, true, true, true, true, true]
# 退出码：0
```

实测要点（全表见 `config-combos.md`）：C1 最小=BM25/摘录、功能全未配置；C2 现有本地向量模型加载一次后三模式可用（单条 dense 查询命中）；C3 ASR 状态正确（按需加载）；C4 模板/规则显式注入可用；C5 生成器计数桩**启动/状态/摘录零调用、显式生成可达**；C6 缺配置明确降级不静默。测试资料为合成性质。

## 3. JS 语法

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 8 HTML files passed syntax check.（退出码 0，home-demo.html 新增）
```

首页为状态聚合页（调用现有 6 个状态接口），无独立行为脚本；浏览器主路径交 Astra（demo-notes 检查表 a—f）。

## 4. 依赖声明

未改 requirements（pypdf/fpdf2 等既有声明足够）；无需 pip check（无依赖变化）。README 增加配置组合表与最小/增强/ASR 可选组合说明。

## 5. 未验证项

1. 浏览器主路径（正常首页→状态→搜索/摘录→未配置提示）：交 Astra 补验。
2. 真实语料运行（真实资料未提供）。
3. 真实 DeepSeek 生成链路本轮未触发（生成器以计数桩验证装配；外部调用 0）。
