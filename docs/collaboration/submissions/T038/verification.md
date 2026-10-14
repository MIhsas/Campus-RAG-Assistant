# T038 验证记录（verification.md，submission_revision=1）

> 命令真实执行、退出码实测。范围=四条任务指定因果链的聚焦验证；**未跑全量 pytest/检索实验/浏览器/ASR/Agent/模型调用**；零外部调用。

## 1. v1.2 新包校验/核验与原件一致（因果链 1）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `python scripts/prepare-real-corpus.py --dataset-root ../../data/datasets/sicau-rag-v1 --selection .cache/t038/selection-v1.2-input.json --out-dir ../../data/corpora/sicau-rag-pilot-v1.2` | `manifest.json: 20 份；产品校验器: valid` | 0 |
| 同命令重跑（核验模式） | `VERIFY OK: 20 份输入/输出/边车一致（未写入）` | 0 |
| 原件/块一致性（parse_manifest 复核） | 20 份原件逐字节=v1.1；块 ID 1031 不变；manifest 差异仅 bed3ac 两日期字段 | 0 |
| 筛选服务 as_of=2026-10-03 | v1.1: 4/20（bed3ac/db05e0 排除）→ **v1.2: 5/20**（bed3ac 准入、db05e0 仍排除）；无筛选=不限制 | 0 |

bed3ac 30 分钟引文可用（q09 gold 同源 ebab438f 切片核对 OK）；证据切片（落款/印发「印」/生效条款）见 metadata-crosscheck §2。

## 2. 候选 API（因果链 2，真实 API + 隔离夹具）

| 检查 | 结果 | 退出码 |
|---|---|---|
| `tests/test_uncertain_sources.py` | **11 passed**：严格准入不变；date/双未知维度规则；已知冲突/失效/未选维度未知/campus 未知全部排除；无对应筛选/空/非法/重复维度 422；未知 document_id 422；空候选返回空；交集不回退；提示规则含 T038 表达且不硬编码答案 | 0 |
| 受影响既有测试（search/ask API、deepseek provider、procedures、qa evidence） | **85 passed** | 0 |
| `scripts/demo-t038-candidates.py`（真实 v1.2 包）→ `candidate-api-demo.json` | 严格 5/20；date 候选 15、student_type 候选 2（含 83eb）；契约 422×4（空/非法/无筛选/未知文档）；严格 search/ask `has_candidate_fields=false` | 0 |

索引复用确认：候选与严格共用 `_search_mode`/同一索引（service 抽取），测试无重复构建断言路径；模型 provider 调用=0（候选路径无 AnswerProvider 引用）。

## 3. 页面因果链（行为桩，非浏览器）

| 命令 | 结果 | 退出码 |
|---|---|---|
| `node scripts/check-search-behavior.cjs` | **23 scenarios passed**（含：候选不自动请求、勾选后显式请求、**改控件后请求仍带结果快照 as_of=2026-10-03**、新请求清空旧候选、**迟到旧候选响应不挂新结果**、日期/类型勾选可用性由快照决定） | 0 |
| `node scripts/check-ask-behavior.cjs` | **40 scenarios passed**（同款链 + 候选文本不进正式结果区/不进历史保存；既有成功/重试/原生 select 场景保持） | 0 |
| `node scripts/check-js-syntax.cjs` | 9 页内联 JS 全过（两改页） | 0 |

## 4. Provider 消息规则（因果链 4，本地传参检查）

`tests/test_uncertain_sources.py::TestPromptRules`：build_messages 的 system 消息含「修订决定措辞/不同前提/旧版本废止/逐字保留」四条新规则；PROMPT_TEMPLATE 同步；断言不含硬编码答案（「带小抄」「50/50」）。HTTP 参数/JSON 契约/引用结构校验未动（test_deepseek_provider 85 项同批通过）。**未做真实云调用，不以 mock 作生成质量验收。**

## 5. 只读面核对（前后 SHA 未变）

v1.1 manifest `34e182f1…`、T030 questions `5fde70a3…`、模板 `78f1c1d9…`、T031/T034 实验 `57b22f93…`/`cef9f162…`、用户意见 `2e1af149…` —— **6/6 未变**。新包 manifest `b05c3755…`（新身份单列）。changed-files 附变更哈希。

## 6. 未验证/证据边界

- **无真实浏览器证据**（本轮未运行浏览器；短清单交 Astra，见 demo-notes.md）。
- 真实生成质量未实测（提示改进仅本地 messages 规则检查）。
- u03/u04 gold 未改（可答性翻转待用户裁定与另行实施）；用户意见 109/3/2 原样保留。
