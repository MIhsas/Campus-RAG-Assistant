# T039 验证记录（verification.md，submission_revision=2，responds_to=T039-R1）

> 命令真实执行、退出码实测。必要验证仅限任务书/返工单范围；**未重跑 UI/ASR/Agent/全量/三模式**；零外部模型调用。
>
> **证据归属（三层，互不冒充）**：
> - **历史执行**（旧窗口，T039 任务期间）：§1—§3 为当时真实运行与捕获日志。本轮仅修复命令文案（原文档路径含 `\b`/`\t` 转义损坏与缺引号），**不为改文案重跑**。
> - **Astra 盘点执行**（2026-10-08—09 交接盘点）：§4a 的差异正向/负向与 8 条原引比对由 Astra 实跑并记录于 `docs/collaboration/handoffs/T039-R1-20261009-盘点.json`，本窗口**引用**而非自称实跑。
> - **新窗口执行**（2026-10-09 本续接窗口）：§4b 只读 SHA 快照核对、§5 原 audit 复跑一次（唯一实验性例外，原返工单要求）。

## 1. 新契约/跨度/准入与冻结校验（历史执行，一次）

| 命令（PowerShell，cwd=`F:\Collage Paper`） | 结果 | 退出码 |
|---|---|---|
| `& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\.cache\t039\build-v2-questions.py'` | 24 题/58 证据；仅 6 题允许字段变更（u03/u04/q08/q10/u01/u02）；meta（schema_version/split/is_synthetic/metric_semantics）不变。**注：该脚本的 field-diff 因共享对象缺陷无效**（24 题全记 changed_fields=[]），差异审计已由 `check-field-diff.py` 替代（§4a）；本命令**不再运行**（会覆盖冻结题集），此处仅保留历史出处 | 0 |
| QuestionDataset 契约校验 + u03 逐源准入（parse_manifest v1.2 + compute_allowed_document_ids，历史脚本内联执行） | 契约 OK（21 可答/3 不足）；u03 gold 源 bed3ac **准入**、span==quote 逐字 OK、db05e0 **排除** | 0 |
| `& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\check-real-eval.py' --pack 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2' --questions 'F:\Collage Paper\data\evaluations\sicau-rag-pilot-eval-v2\questions.json' --freeze 'F:\Collage Paper\data\evaluations\sicau-rag-pilot-eval-v2\freeze.json'` | `CHECK OK: 24 题 / 58 条证据；冻结哈希核对 37 项` | 0 |

freeze.json 五节 schema；实现 hash=**当前实际文件**（chunk.py/filters.py 含 T034/T038 变更，非 T030 旧值）；模型身份=本机 BGE 配置文件。

## 2. 三模式本轮原始输出（历史执行，各一次）

捕获脚本（历史执行，**不再运行**）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\.cache\t039\run-v2-baseline.py'
```

其内部对每个 mode 执行（cwd=`F:\Collage Paper\step2_code\backend`；`<MODE>` 分别取 `bm25`、`dense`、`hybrid` **各独立执行一次**，不是单条 `bm25|dense|hybrid` 参数）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' -m campus_assistant.evaluation.run --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2\manifest.json' --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2' --questions 'F:\Collage Paper\data\evaluations\sicau-rag-pilot-eval-v2\questions.json' --top-k 5 --mode <MODE> --model-path 'F:\Collage Paper\step2_code\backend\models\bge-small-zh-v1.5'
```

真实日志：`data/evaluations/sicau-rag-pilot-eval-v2/results/{bm25,dense,hybrid}.json`（完整 JSON）+ `.stderr.log` + `.exitcode.txt`（三者均为当时实际捕获，不为补文案重跑）。

| mode | valid | n | R / H / M | exit |
|---|---|---|---|---|
| bm25 | true | 21 | 0.7380952380952381 / 0.7619047619047619 / 0.6190476190476191 | 0 |
| dense | true | 21 | 0.7142857142857143 / 0.7142857142857143 / 0.46984126984126984 | 0 |
| hybrid | true | 21 | 0.7142857142857143 / 0.7142857142857143 / 0.5634920634920635 | 0 |

完整 JSON+stderr+exitcode 存 `results/`；无 document_id/候选/生成/Agent；每 mode 独立构建索引（未改框架）。

## 3. 聚合/分组一致性与共同子集（历史执行）

| 检查 | 结果 |
|---|---|
| aggregate.json 重算 | 由本轮 results/*.json 完整输出计算（未复制旧 summary_by_type/group）；不足 n=3 空检索率三模式 0.000 |
| 共同子集（原 20 可答） | R/H/M 与 T030 存储**逐值一致**；**60/60（20×3）命中序列与分数逐项一致**（排名变化=无） |
| 两例手算 | u03：单源 OR、[0,452)⊇[101,129)、rank1、MRR 1.0 ✓；q10：f1×7 OR、f2×7 OR、组间 AND、两前提不判冲突 ✓ |

## 4. 差异审计与输入身份

### 4a. 差异正向/负向与补充原引（Astra 盘点执行，本窗口引用）

| 命令（PowerShell，cwd=`F:\Collage Paper`） | 结果 | 退出码 |
|---|---|---|
| `& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\.cache\t039\check-field-diff.py'` | 6 题非空差异、18 题无变更；字段全部落在返工允许集；所有 query/conditions 不变 | 0 |
| `& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\.cache\t039\check-field-diff.py' --inject-drift q07:query` | **预期失败的负向对照**：q07.query 内存注入被判定越界（非零退出）；未写正式题集/清单 | 1（预期） |

补充材料原引比对（Astra 以真实解析器切片独立比对）：8/8 条与解析块逐字相等；8 个本机原件路径存在。q10 两前提原引与上下文、u04 两页候选注记均已落盘于 `review-supplement.md`。程序化逐字一致≠语义审定/现行性认证。

### 4b. 旧输入/实验/用户意见不变

历史执行（任务期间前后 SHA，7/7 未变）：

| 文件 | SHA | 结论 |
|---|---|---|
| v1.1 manifest / v1.3 questions / v1.3 freeze | `34e182f1…` / `5fde70a3…` / `fd2f2476…` | 未变 |
| 模板 v1.2 / T031 / T034 实验 | `78f1c1d9…` / `57b22f93…` / `cef9f162…` | 未变 |
| 用户意见记录 | `2e1af149…` | 未变 |

新窗口执行（2026-10-09）：对照盘点快照 `handoffs/T039-R1-20261009-盘点.json` 逐文件重算 SHA256——23 只读文件 + 8 部分成果文件 + 7 件 rev1 归档共 **38 项，drift_or_missing=0**（退出码 0）。新产物身份单列：v2 questions `4e39229e…`、freeze `8c289b2a…`、aggregate `fcecdc9c…`（与 revision 1 记录身份 3/3 一致）。

## 5. 原 Astra audit 复跑（新窗口执行，一次，返工单明确要求）

复跑前保全旧失败历史：`reviews/T039-audit.json`（revision 1 失败记录，6 条提交差异不匹配）复制为 `submissions/T039/T039-audit-rev1-failed-preserved.json`，SHA `41f043a2e069da80…` 与原件逐字节一致。探针源码/判据/通过条件未改。

命令（cwd=`F:\Collage Paper`；新窗口实际经 Git Bash 调用同一解释器与参数，下为可复制 PowerShell 形式）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\docs\collaboration\reviews\T039-audit.py'
```

| 项 | 实测 |
|---|---|
| stdout | `SCORES OK: 72 rows; common rankings/scores 60 ; fresh BM25 24 rows; group checks 36` |
| EXPECTED CHANGES | q08/q10=`rationale,revision_note`；u01/u02/u04=`missing,rationale,revision_note`；u03=`answerable,evidence,missing,question_type,rationale,revision_note` |
| SUBMITTED DIFF MISMATCHES | 0 |
| stderr | 4 条 `Ignoring wrong pointing object` PDF 解析警告（原样出现，按盘点口径不计失败） |
| 退出码 | **0** |
| 写入 | `reviews/T039-audit.json`（status=**ok**，含 6 项历史哈希核对）、`reviews/T039-bm25-fresh.json`（内部一次 BM25 全 24 题与已存结果逐行一致；未编码向量、未调云模型、未覆盖 `results/`） |

## 6. 文档整理核对

- review-supplement.md 四项齐（原意见/处置/逐字原引/示例释义标注「模型辅助、非产品实时生成」/待确认）；Astra 盘点 8/8 原引一致；未要求重确认模板 33 项；无代签。不再运行 build-review-supplement.py 覆盖。
- 本文件修复：路径转义损坏/缺引号命令改为可复制 PowerShell 形式（解释器、脚本、含空格参数分别加引号）；`bm25|dense|hybrid` 不再写成单条可执行模式值；标题更新为 revision 2；三层证据归属明确。
- human-review-pending.md：§0 收窄为「T036 首次意见对应历史包」，§1 区分历史 v1.3 与当前 v2.0 题集；顶部/§2/§5 口径（用户 109/3/2、模板 33 项确认、现行性未认证）不变。
- README：v1.2 当前包与 v1.1 历史边界说明（历史执行时已更新，本轮只读核对未再改写）。
- 新检查器 `check-field-diff.py` 替代 `build-v2-questions.py` 的差异审计职能（后者共享对象缺陷，保留历史原件**不运行**）。

## 7. 未验证/边界

- 未跑：UI/ASR/Agent/全量/三模式重跑/向量编码；产品算法/评分器/筛选/provider 未改。
- 真实浏览器跳转未在本窗口验证；新修订人工意见、学校政策现行性**未认证**。
- 语义边界维持：q10 普通/互评为不同前提（不按发布时间宣称 2016 废止）；u04 scope 未知/严格不足保留；db05e0 日期未知只候选查看；u01/u02 未确认保留。
- 新基线不代表校园 QA 准确率/可靠拒答/算法提升；`planner_live_verified=false`。
