# T033 验证记录（verification.md，submission_revision=1）

> 命令在 Windows（Git Bash）下真实执行；退出码实测。范围=入口联动主链与受影响测试；未跑全量 pytest、检索实验或模型编码。

## 1. 后端（受影响 procedures 测试 + 引用哈希核对）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python -m pytest tests/test_procedures.py -q` | **16 passed**（14 既有 + 入口元数据 2 项：列表含 related_keywords/source_document_ids 且无路径/全文；loader 接受无字段模板并校验类型/空白） | 0 |
| `step2_code/backend/.venv/Scripts/python.exe scripts/verify-procedures-citations.py --procedures data/procedures/sicau-transfer-2026-v1/procedures.json --manifest data/corpora/sicau-rag-pilot-v1.1/manifest.json` | `citations: 20/20 ok`；`draft saveable: True`（模板引用未变，仅核对哈希，不重做语义调查） | 0 |

## 2. 页面回归（ask 重做入口 + 受影响 procedures 行为/语法）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node scripts/check-js-syntax.cjs` | 9 页内联 JS 全过 | 0 |
| `node scripts/check-ask-behavior.cjs` | **38 scenarios passed**（33 既有 + T033 五链） | 0 |
| `node scripts/check-procedures-behavior.cjs` | 11 scenarios passed | 0 |

T033 五链断言要点：

1. **2026 来源**（结果快照 document_id=doc-2026）→ 入口标题「…（校教发〔2026〕1号·2026版）」+「关键词匹配」+「办理依据将在办事页…」；链接 `procedure_id=sicau-transfer-2026` 且 **不含 document_id**。
2. **2023 来源**（doc-2023）→ **零办事链接**；提示「依据与本次指定文件不同」+「本次文件条件保留」（不误导 2026 模板、不静默丢条件）。
3. **无指定来源** → 入口含适用范围摘要（「2025 年及之后入学」）+「不代表」适用断言。
4. **目录晚到**（deferProcedures）→ 先显示「正在确认当前配置」；释放后入口出现且 **ask 请求数仍为 1**（不重复问答）。
5. **无关键词匹配** → 无「相关事项入口」区块（无死链）。

既有行为保留核验（33 场景全过）：T031 四条件恢复/失效文件 422/重试与转摘录快照/历史零请求、原生 select 语义桩、快照链接不被控件改写（含无配置「本次运行未配置对应指南」提示）。

## 3. 本地证据（entry-api-demo.json，`scripts/demo-t033-entry.py`，exit 0）

真实包+真实模板装配（serve-corpus 等价）：`GET /api/v1/procedures` 列出 `sicau-transfer-2026`（related_keywords=["转专业"]，source_document_ids=["5cb2ac21…e76"]，由模板引用推导）；确定性判定输出——2026 来源→`matched`、2023 来源→`source_mismatch`、无来源→`matched`、无关问题→空。链接契约记录：document_id 不进入办事参数。

## 4. 本轮实际改动

- 模板：`data/procedures/sicau-transfer-2026-v1/procedures.json` v1.1→v1.2（仅加 `related_keywords`；正文/20 条引用未改）；`examples/procedures/procedures.json` 两事项加 `related_keywords`（正文/引用未改）。
- 后端（最小）：`procedures/service.py` loader 可选字段校验；`api/procedures.py` 列表增加两字段（引用推导，无路径/全文）。
- 页面：`static/ask.html` 目录驱动入口（关键词∩来源集合、快照链接、目录晚到补渲染、删除固定 ID 逻辑）。
- 测试/桩：`tests/test_procedures.py` +2；`scripts/check-ask-behavior.cjs` 桩目录字段/延迟 + 五链场景；`scripts/demo-t033-entry.py` 新增。
- 未改：检索/生成/Planner/ASR/资格自查、procedures 页（预选/恢复行为原样）、原语料/gold/T030-T032 实验与归档。

## 5. 未运行/未验证（如实）

- **真实浏览器**：无浏览器工具；短清单交 Astra（demo-notes.md，端口 8010），不代签。
- 未跑：全量 pytest、检索实验、模型编码、ASR/Agent。
- 入口为确定性匹配，**不宣称用户符合政策、完成审批或真实 Agent 验证**；人工复核（模板语义/政策现行性）仍为未完成。
