# T029 演示与复现说明（demo-notes.md，revision 2）

> 当前包 **v1.1**（`data/corpora/sicau-rag-pilot-v1.1/`；v1 保留为历史）。v1→v1.1 仅元数据补正（source_site×2、日期×2），**20 份正文同字节**——旧查询排名证据对应 v1、与 v1.1 内容等价。

> 语料包：`data/corpora/sicau-rag-pilot-v1.1/`（20 份真实资料，`is_synthetic=false`；原字节与原 SHA 保留）。MiMo 无浏览器能力——API 级证据如实记录，**浏览器核验步骤交 Astra**（不编造截图）。

## 1. Windows 启动命令（含空格路径已引用）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
# 首批真实包正常运行（最小配置：BM25+摘录+预览；零外部请求、默认全关）
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1\manifest.json' `
  --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1'

# 可选增强（按需；向量检索用本地既有 BGE，不自动下载）
#   --embedding-model-dir 'F:\Collage Paper\step2_code\backend\models\bge-small-zh-v1.5'
# 生成器/规划器默认关闭——首批真实资料阶段建议保持关闭（任务书：首批默认生成器关闭）
```

启动后配置报告应显示：语料 20 份解析成功、**资料性质=真实资料**（is_synthetic=0）、生成器/规划器未启用。

## 2. 浏览器核验步骤（交 Astra）

| # | 操作 | 预期 |
|---|---|---|
| a | 打开 `http://127.0.0.1:8040/` | 首页能力状态：语料 文档 20 / 解析成功 20 / **资料性质：真实资料**；检索模式=关键词；生成器/ASR/模板/规则未配置（正常） |
| b | `/search` 搜「缓考课程成绩如何评定和记载？」 | 命中含 教发〔2018〕10号 缓（补）考成绩规定（top1）；结果卡有“查看原文”链接 |
| c | 点“查看原文” | `/preview` 逐块原文定位（页码 locator），**数字“≥85 分记 85 分”与原 PDF 一致** |
| d | `/ask` 同题「整理依据」 | E 编号摘录 + 文档/块/span + preview 链接（证据包）；**生成答案按钮禁用**（生成器未配置） |
| e | `/search` 搜「**申请转专业对已修课程有什么要求？**」（本题已实测） | 显示 2023/2020/2026 **三版及各自不同课程要求**（2026“均合格”/2023、2020“无补考或重修记录”+排名门槛）——注意 version_label，**检索命中≠适用于当前学生**。注：「跨校区转专业允许吗？」的旧版冲突句未入 top5（词面距离），浏览器预期不作此预言 |
| f | 加条件 学生类型=本科 再搜「转专业申请需要什么条件？」 | 三版办法仍命中；scope 未知的文档（如学籍指南）被保守排除——如实呈现筛选语义 |

## 3. API 级已核对证据（MiMo 实测，零外部请求）

- `GET /api/v1/search/status` → `status=ready`、`document_count=20`、`parsed_count=20`、**`synthetic_count=0`**（真实资料标识）、`available_modes=[bm25]`。
- `POST /api/v1/ask`（extractive）「缓考课程成绩如何评定和记载？」→ HTTP 200、`evidence_only`、5 条证据；E1=68fb37043ab7/块 8a790c05/span[0,364]/带 preview_url。
- 查询记录：`query-checks.json`（9 题 × BM25，4 题另跑 Dense/Hybrid 冒烟；**运行于 v1，正文与 v1.1 同字节故等价**）；引用对照：`citation-crosscheck.md`（9 条跨度）；v1.1 摘录主路径已补核（同 E1 链路）。
- 说明：探针中 `/api/v1/corpus/preview` 路径猜测 404（预览为 `/preview` 页面+`preview_url` 锚点），不影响摘录→出处闭环。

## 4. 复现（构建与查询）

```powershell
# 构建语料包（新输出目录；重复执行自动进入核验模式，不覆盖；v1.1 选择清单=.cache/t029/selection-v1.1.json）
& .\.venv\Scripts\python.exe scripts\prepare-real-corpus.py --dataset-root 'F:\Collage Paper\data\datasets\sicau-rag-v1' --selection '<selection-v1.1.json>' --out-dir 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1'
# 核验模式（同一命令重跑）：VERIFY OK: 20 份输入/输出/边车一致（未写入）——任何输入/边车漂移 DIFF 报出且非零退出
```

选择清单与映射说明见 `mapping-notes.md`（selection.json 副本在包内）；解析摘要 `parse-summary.json`；查询与引用记录同目录。

## 5. 检索验证口径（勿混算）

本组 9 题为**开发核查问题**（预期先于查询保存；非正式人工 gold、非教师标注）；结果仅证明“搜索/摘录→原文”闭环与筛选/版本语义在真实资料上工作。**不与 T027 合成指标混算**；真实校园准确率未验证。
