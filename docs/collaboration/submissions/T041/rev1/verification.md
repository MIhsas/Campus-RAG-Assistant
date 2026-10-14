# T041 验证记录（verification.md）

> 范围=文档链接/关键路径、指标表对已存机器产物、四题文本对原始 JSON、token 算术、主线秒数、归档字节核验；`--help` 仅核对启动命令参数。**没有代码/数据变化，未跑产品测试**；零外部调用、不读密钥/环境。分层：**本轮实测**（下方命令）｜**历史引用**（T038—T040 已验收记录，未重跑）｜**未验证**（§4）。

## 1. 本轮实测（命令与退出码）

| 核对项 | 方法 | 结果 |
|---|---|---|
| 归档字节 | 改前先复制八件至 `archive-pre-t041-20261011/`；改后 `sha256sum` 复核归档 8 件哈希=改前记录（README `a31a9033…`/system-design `dab469a6…`/thesis-outline `07f92376…`/evidence-matrix `4c84fa3d…`/defense-script `e96bce13…`/windows-runbook `d55a0db0…`/experiment-index `9762be38…`/human-review-pending `852a9517…`） | **8/8 一致** |
| 文档链接/关键路径 | Python 解析九件（八件+casebook）相对链接 28 条 + 6 个关键数据路径 | **28/28 解析、路径全存在**（脚本 exit 0） |
| 指标表对已存产物 | `aggregate.json` 逐值 vs experiment-index E4 / thesis-outline 表 6-5 / evidence-matrix 当前基线行（BM25 0.7380952380952381 等全值）；共同子集 n=20 值单列 | **逐值一致** |
| 四题原文本 | casebook 中 q08/u04 不足理由、q10 三段、u03 一段、四题 query 与 `submissions/T040/live-answers-full.json` 逐字比对 | **全部逐字一致** |
| token 算术 | prompt 1344+1379+1667+1690=**6080**；completion 107+171+53+57=**388**；total **6468** | **算术正确**（未换算费用） |
| 主线秒数 | defense-script 合计表 **560** 秒，480—600 区间内 | **一致** |
| 启动命令参数 | `serve-corpus.py --help`（只读）：`--manifest --corpus-root` 必填、`--port --procedures` 等可选——与 windows-runbook §2a 命令一致；v1.2 manifest 与模板 1.2 路径存在 | **一致** |

核对机器产物：`t041-verify.json`（本目录，逐项布尔与数值）。

## 2. 历史引用（未重跑，沿用已验收记录）

- T038 真实包 v1.2（20/1182；bed3ac 2019-11-07；83eb scope/db05e0 日期未知）——T038 提交与 metadata-crosscheck。
- T039 v2.0 基线与 60/60 共同子集——`data/evaluations/sicau-rag-pilot-eval-v2/aggregate.json` 与 T039 提交（本轮只读取值）。
- T040 四题真实冒烟（发送 4/provider 4/ask 8；2 作答/2 不足；usage 6468）与三层判读——`submissions/T040/` 与 [T040-R4](../../reviews/T040-R4.md)（Astra 98 项离线审计 exit 0）。
- 人工意见 109/3/2、模板 33 项确认——`data/reviews/T036-user-review-20261008/` 与历史记录（只读）。

## 3. 保全核验

- 八件归档 `archive-pre-t041-20261011/` 与改前字节一致（§1）；较早 `archive-t028-delivery/`、`archive-t035-rev1/`、`rev1/` 未动。
- T040 模型输出两件（live-results/live-answers-full）与 run 缓存、A 材料、题集/冻结/aggregate **未改**（本轮零写入这些路径）。
- 用户意见/模板/gold/docs01—04/产品脚本未改。

## 4. 未验证（不代填）

- 真实答案质量/学校政策现行性/用户对新答案与 q10 P3 推断的确认——**未验证**。
- `live_verified=true` 为 T040-R4 对**历史四题链路/存档**的认定；**本轮未进行任何 live/浏览器操作**，无本轮浏览器生成闭环证据，无现场计时实测。
- 论文格式/答辩时长形式等用户确认项照旧开放。
