# T036 演示说明（demo-notes.md，revision 3）

> 当前有效包：**T036-v3**（T036-R2 NodeList 兼容修复后构建；意见筛选按本卡意见行、Array.from 化）；T036-v1/v2 保留为历史。pack.json「本地原件」为相对工作区路径——从 `F:\Collage Paper` 解析即可打开原件。

## 复核包打开方式（本机离线）

1. 用浏览器打开（**当前包=T036-v3**，T036-R2 NodeList 兼容修复后构建）：`F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v3\review.html`
   - 本地 file:// 直接打开；页面自包含 CSS/JS/数据，**无网络/无 CDN/无外部字体**；无需启动服务、无需模型。
2. 页面顶部为输入身份（题集/模板 SHA）与条目计数；两栏切换「题目（24）」「办理模板（13 步）」；可按编号或文字查找，展开逐字 quote / 原块全文 / 前后相邻块；版本、条件、原文（橙/蓝/绿框）与模型整理说明（紫框）分区展示。

## Astra 短清单（约 5 分钟；本轮无浏览器工具，未代签）

| # | 操作 | 预期 |
|---|---|---|
| 1 | 打开 review.html | 身份行显示题集 1.3（SHA 5fde70a3…）、模板 1.2（SHA 78f1c1d9…）、24 题（20+4）/57 证据/13 步/20 引用；全部意见初值「未复核」；复核人/记录标题为空 |
| 2 | 查 q05 或 q10（多源 OR 题） | 事实组标注 OR 语义（每源须独立完整支持）；各证据含逐字 quote 与原块全文对照 |
| 3 | 查 u01—u04（不足题） | 显示「已查范围/不足依据」；注明无 gold 引用 ≠ 学校无规定 |
| 4 | 查模板 t2/t8/t12（跨页引用） | 两条引用**并列展示**、页尾文字完整（不再截断）；「资料未说明」项标注保留 |
| 5 | 对任一证据选「需修订」并写意见 → 点「导出复核记录」 | 浏览器下载 human-review-record.json：该条为需修订+意见，**其余条目仍为未复核**；含输入 SHA；record_title/reviewer 为手填值 |
| 6 | 刷新页面（不导出的情况下） | 意见清空（页面不自动保存；顶部有此警示）——验证导出必要性 |
| 7 | 打开 `.cache/human-review/T036-v3-simulated-export.json` | record_title=「模拟操作测试（MiMo 演示导出，非真实复核结论）」；恰 1 项需修订（q01/f1-s1） |
| 8 | （筛选归属）在任一题（如 q02）的 f1-s1 证据保持未复核；仅把 q01/f1-s1 设「需修订」→ 顶部意见筛选「需修订」 | **只显示 q01 卡片**；q02（同名 f1-s1）不出现——不误归属 |
| 9 | 模板页把 t1 的一条引用设「需修订」→ 筛选「需修订」 | **只显示 t1 步骤卡**；t13（共享同一块 d64f4351）与模板摘要卡不出现 |

## 已完成的自动化证据（非浏览器，证据层级=代码/桩）

- 构建：`build-human-review-pack.py` exit 0（77 条逐字/跨度/哈希核对、24/57/13/20 齐备）；非空目录拒绝覆盖 exit 1；隔离坏引用拒绝 exit 1 且不写包、原件未动。
- 行为：`check-review-pack.cjs` **28 项**（DOM/JS 桩，支持 `--pack-dir`，querySelectorAll 返回 NodeList 形态——非 Array、无 some）：原 15 项 + 筛选因果链 9 项 + NodeList 形态断言 4 项（some/map/flatMap 缺失、forEach/item、可索引/迭代）。
- Astra 探针原样核对：`node docs/collaboration/reviews/T036-filter-probe.cjs --pack-dir …/T036-v3` → pass=true，exit 0；`T036-nodelist-probe.cjs --pack-dir …/T036-v3`（NodeList 形态探针）→ pass=true，exit 0。
- 测试：`tests/test_human_review_pack.py` 4 passed（revision 1 轮，本轮未重复）。

## 重新构建（换新目录，如 T036-v4；当前目录已非空会被拒绝）

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\build-human-review-pack.py' --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1\manifest.json' --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.1' --questions 'F:\Collage Paper\data\evaluations\sicau-rag-pilot-eval-v1\questions.json' --procedures 'F:\Collage Paper\data\procedures\sicau-transfer-2026-v1\procedures.json' --out-dir 'F:\Collage Paper\step2_code\backend\.cache\human-review\T036-v4'
```

## 边界提醒

- 导出记录是人工意见记录，**不是签署认证、不是学校政策确认**；不写回 gold/模板/历史文件。
- 程序化逐字一致（构建时核对）≠ 语义正确或政策现行有效——语义结论由用户/导师在页面中填写。
