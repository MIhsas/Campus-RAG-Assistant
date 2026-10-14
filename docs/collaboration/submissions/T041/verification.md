# T041 验证记录（verification.md，submission_revision=2，responds_to=T041-R1）

> 范围=两项口径修复的历史依据、涉及链接与本轮修改 SHA；**已通过的指标/四题原文/token/560 秒/--help/结构矩阵不重复验证**（沿用 [T041-audit](../../reviews/T041-audit.json) 53 项与 [T040-R4](../../reviews/T040-R4.md) 记录）。零外部调用、不读密钥/环境、未跑任何测试/浏览器/实验。

## 1. 本轮实测

| 核对项 | 方法 | 结果 |
|---|---|---|
| 保全 | 改前复制九件 → `docs/delivery/archive-t041-rev1/`、五件提交 → `submissions/T041/rev1/` | 新目录各 9/5 件；既有 archive-pre-t041/archive-t028/archive-t035-rev1/rev1 未覆盖 |
| 必修1 历史依据 | 用户意见 109/3/2、模板 33 项确认=T036 用户记录与 human-review-pending 既有状态；T039 新四项/T040 新答案待复核=T039-R2/T040-R4 口径 | **依据一致**；统一表述后九件无当前态「全未复核/人工未复核」残留（README 历史快照引述语、human-review 工具 UI 用语按上下文保留；E1 历史表加「实验运行时点」标注） |
| 必修2 历史依据 | [T038-R1](../../reviews/T038-R1.md)「真实浏览器主路径已补齐」与 [T038-browser/verification.md](../../reviews/T038-browser/verification.md) 操作表（日期/学生类型候选、控件绑定原结果、候选→PDF 第 4 页、复制隔离、历史恢复隔离、新请求清旧列表、指定文件求交不回退） | **与改写后 §8 引用一致**；T029/T031/T032/T033 按各评审范围并列；T041 本轮无浏览器实操、T040 无浏览器生成闭环两条保留 |
| 涉及链接 | 九件相对链接解析（含新增 T038 两条依据链接） | **30/30 存在** |
| 本轮修改 SHA | sha256sum 六件修改 + 三件未变 | 见 changed-files.json（实测全值）；未变三件（system-design/human-review-pending/generation-casebook）与 rev1 归档哈希一致 |
| 口径扫查 | 九件正文 grep 当前/历史人工与浏览器表述 | 无「本轮未测否定历史」或「全未复核」当前态残留 |

## 2. 历史引用（未重跑）

T041-audit 53 项结构/内容检查、T040-R4 98 项离线审计、T038-R1 浏览器记录、用户意见 109/3/2 与模板 33 项确认、T039/T040 各提交——均沿用既有记录，本轮零改动。Astra audit/输出未改写。

## 3. 未验证（不代填）

- 语义最终认定待 Astra 复验；**不写 accepted**。
- q10 P3 推断、T039 新四项/T040 新答案、学校政策现行性仍待用户；T040 live_verified 历史限定不变；本轮无浏览器/模型/实验。
