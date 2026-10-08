# T032 验证记录（verification.md，submission_revision=2）

> 命令在 Windows（Git Bash）下真实执行；退出码实测。**T032-R1 轮**只改模板与说明（t2/t8/t12 三条引用补页尾漏字），按返工单只跑原引用跨度校验、Astra 三项探针、正常草稿/verify 示例；未重复页面回归、全量 pytest 或检索实验。

## 0. T032-R1 轮验证（2026-10-07）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `step2_code/backend/.venv/Scripts/python.exe step2_code/backend/scripts/verify-procedures-citations.py --procedures data/procedures/sicau-transfer-2026-v1/procedures.json --manifest data/corpora/sicau-rag-pilot-v1.1/manifest.json` | `citations: 20/20 ok`；`draft saveable: True \| steps: 13 \| status: ready` | 0 |
| `step2_code/backend/.venv/Scripts/python.exe docs/collaboration/reviews/T032-span-probe.py` | t2「按照必修课初修加权平均」/t8「或后」/t12「必须遵守学校」`present_in_citations: true`，`passed: true` | 0 |
| `python scripts/demo-t032-procedures.py` | 正常草稿（无条件/本科）20/20 saveable；排除条件不可保存且 quote=null；保存快照 verify=**unchanged**（篡改→changed） | 0 |

- 三条 quote/char_end 均由脚本从真实解析块切片生成（v1.0 char_end 260/505/457 → v1.1 **271/507/463**，均为块尾）；未改解析器、未开发通用语义校验器、未改 `verify-procedures-citations.py` 口径。
- 归档：revision 1 七件（`submissions/T032/rev1/`）+ v1.0 模板快照（`data/procedures/sicau-transfer-2026-v1/archive-v1.0/`），9/9 字节核验一致。原语料/gold/历史实验只读未动。
- **人工复核状态：未复核**（保留声明）；无外部调用、无 commit/push。

## 1. T032 revision 1 轮验证（历史记录）

## 1. 来源身份核实（先核实、后整理）

| 项 | 实测 |
|---|---|
| manifest 条目 | document_id `5cb2ac21…e76`、标题「本科生转专业实施办法（校教发[2026]1号）」、version_label「校教发〔2026〕1号」、published_at=effective_from=2026-01-08、effective_to=null、scope.student_type=[本科]、is_synthetic=false |
| 原文件哈希 | SHA-256(`5cb2ac21…e76.pdf`) = `5cb2ac21497c2dade0961bedb355b3ed568b4ea409fb964e3064ea9197209e76`（= 文件名/ID，复算一致） |
| 正文 | 5 个解析块（PDF 第 1–5 页）完整通读后整理；正文页眉「校教发〔2026〕1 号」、落款 2026 年 1 月 8 日与 manifest 一致 |

## 2. 引用逐字/跨度/哈希程序化核对（模板全部引用一次）

```
step2_code/backend/.venv/Scripts/python.exe step2_code/backend/scripts/verify-procedures-citations.py \
    --procedures data/procedures/sicau-transfer-2026-v1/procedures.json \
    --manifest data/corpora/sicau-rag-pilot-v1.1/manifest.json
→ citations: 20/20 ok
→ draft saveable: True | steps: 13 | status: ready
→ CHECK OK   (exit 0)
```

- 复用 `procedures.service` 的既有校验（document 存在 / sha256 / span 内 quote 逐字 / 筛选准入），真实包**新解析**核对，非缓存。
- 逐字对照表（13 步 / 20 引）见 citation-crosscheck.md；跨页事实多引共同支持（t2/t8/t12）已标注。程序化核对 ≠ 语义审定；**人工复核状态：未复核**。

## 3. 最少业务验证（api-demo.json，`scripts/demo-t032-procedures.py`，exit 0）

| 场景 | 实测 |
|---|---|
| 模板列出 | 200；sicau-transfer-2026 /「本科生转专业办理清单（校教发〔2026〕1号·2026版）」/ v1.0 / is_synthetic=false |
| 草稿（无条件） | saveable=true，status=ready，13 步，引用 20/20 ok，免责语为真实模板口径 |
| 草稿（student_type=本科） | saveable=true，20/20（来源 scope=本科，准入通过） |
| **排除条件**（as_of_date=2020-01-01，早于 2026-01-08 生效日；先查 manifest 选定） | saveable=**false**、status=insufficient；失败引用状态=source_excluded；**failed_quotes_are_null=true**（不泄漏失效原文）；失败步骤 detail 抑制；不回退其他版本 |
| 保存快照核对 | verify=**unchanged**（=页面「核对当前依据」所存 steps_snapshot 口径） |
| 篡改快照核对 | verify=changed（span+1 被检出） |

## 4. 页面相关回归（页面/服务有改动）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node scripts/check-js-syntax.cjs` | 9 个 HTML 内联 JS 全过 | 0 |
| `node scripts/check-procedures-behavior.cjs` | **11 scenarios passed** | 0 |
| `python -m pytest tests/test_procedures.py -q` | **14 passed**（service 免责语分支变更直接相关） | 0 |

## 5. 本轮实际改动

- 新增：`data/procedures/sicau-transfer-2026-v1/{procedures.json,SOURCE-CHECK.md}`、`scripts/verify-procedures-citations.py`、`scripts/demo-t032-procedures.py`、提交材料七件。
- 最小修正：`procedures/service.py` 免责语按 is_synthetic 分支；`static/procedures.html` 顶部提示去“合成资料演示”硬编码（真实/合成模板均如实）。未改检索/筛选/计分算法、ASR、Planner、生成器；原合成演示模板保留。
- 只读未动：语料包与 manifest（来源 PDF 哈希复算一致）、T030 gold/冻结、T031 selection-map/experiment（未复算、未改动）。

## 6. 未运行/未验证（如实）

- **真实浏览器**：无浏览器工具，未实测；事项→草稿→原文→保存→勾选/备注→刷新→核对 + 排除案例的短清单交 Astra（demo-notes.md），不代签。
- 模板语义是否符合学校实际办理流程：属人工复核事项，未审定；模板不宣称现行有效、不判定资格、不保证申请成功。
- 未跑：检索实验、全量 pytest、ASR/Agent、外部模型调用、下载/安装/commit/push。
