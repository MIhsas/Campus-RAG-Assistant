# T033 演示说明（demo-notes.md）

## 启动命令（真实资料 + 真实模板，Astra 可运行）

```powershell
# step2_code/backend 下（PowerShell）；默认 BM25，不启用生成器/向量/ASR
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
    --manifest ..\..\data\corpora\sicau-rag-pilot-v1.1\manifest.json `
    --corpus-root ..\..\data\corpora\sicau-rag-pilot-v1.1 `
    --procedures ..\..\data\procedures\sicau-transfer-2026-v1\procedures.json `
    --port 8010
# 打开 http://127.0.0.1:8010/ask（问答→办事入口）与 http://127.0.0.1:8010/procedures
```

零外部调用；不启用 DeepSeek/生成器。

## 已完成的自动化证据（非浏览器实证，与浏览器证据分开）

- `entry-api-demo.json`（`scripts/demo-t033-entry.py`，exit 0）：目录含 `related_keywords`/`source_document_ids`（由模板引用推导）；确定性判定——**2026 来源→matched(sicau-transfer-2026)**、**2023 来源→source_mismatch（不推荐）**、无来源→matched、无关问题→无入口。
- ask 行为桩 `check-ask-behavior.cjs` **38 场景**（含 T033 五链：2026 入口/2023 不误导/无来源版本提示/目录晚到不重复请求/无关键词无死链；既有 33 场景含 T031 条件恢复/失效文件/快照链接不被控件改写全保留）。
- `check-js-syntax.cjs` 9 页 exit 0；`check-procedures-behavior.cjs` 11 场景 exit 0；`tests/test_procedures.py` 16 passed（含入口元数据 2 项）；引用哈希核对 20/20 ok（模板引用未变）。

## 真实浏览器短清单（本环境无浏览器工具，供 Astra 复验）

| # | 操作 | 预期 |
|---|---|---|
| 1 | /ask 选「指定文件」=《本科生转专业实施办法（校教发[2023]1号）》，问「申请转专业 课程要求」→ 整理依据 | 结果区「相关事项入口」出现**提示**「当前已配置指南的依据与本次指定文件不同…不提供入口；本次文件条件保留」；**无**办事链接（不误导 2026 模板） |
| 2 | 清除选择改选 2026 文件（校教发[2026]1号），同题再问 | 入口出现「本科生转专业办理清单（校教发〔2026〕1号·2026版）　模板 1.2」+「关键词匹配，非资格判断」+「办理依据将在办事页…重新核对」；链接一个 |
| 3 | 点击「进入办事页」 | 进入 /procedures，**只预选**该事项卡片并恢复本次问题+四条件快照；**不自动生成草稿/保存/调用模型**（明确操作前零 draft） |
| 4 | 在办事页显式「生成草稿」 | 13 步草稿（模板 1.2），逐字引用可跳原文 |
| 5 | 回到 /ask 不选文件问同题 | 入口显示版本/适用范围摘要（含「2025 年及之后入学」）与「不代表…适用的建议」措辞 |
| 6 | 已出结果后改动顶部筛选控件（不重新提问） | 旧结果入口链接不变（绑定结果快照） |
| 7 | 开启本机历史保存后提问→切换文件→历史「查看」 | 入口使用该历史结果的条件/来源快照；零新请求 |
| 8 | 问无关问题（如「宿舍晚归」） | 无相关事项入口（无死链） |

（入口=关键词+来源集合的确定性匹配，非 Agent 推理/版本自动判断/资格判定。）
