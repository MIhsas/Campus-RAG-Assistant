# T040 A 阶段验证记录（verification.md）

> 命令真实执行、退出码实测。范围仅任务书 §4：四题快照一致、证据切片/准入、messages 一致、零外部发送、已有目录不覆盖 + 少量必要业务测试与一次真实本地 dry-run。未跑全量/UI/ASR/Agent/向量/三模式/T030-T039 矩阵；零外部模型调用。执行环境：Windows 11 / Git Bash，cwd 见各行；解释器 `F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe`。

## 1. 少量必要业务测试（新脚本回归）

命令（cwd=`F:\Collage Paper\step2_code\backend`）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' -m pytest tests/test_prepare_real_qa_smoke.py -q
```

| 轮次 | 结果 | 退出码 |
|---|---|---|
| 首跑 | 2 failed / 3 passed：poisoned 用例断言 `match="gold"` 与守卫实际错误（builder 不一致，先于 gold 检查触发）不符；合成 fixture（is_synthetic=True）被脚本污染守卫拒绝 | 1 |
| 修正测试后 | **5 passed**（修正的是测试断言与 fixture 标注，未改守卫逻辑） | **0** |

覆盖：①环境标志守卫关闭/恢复（含异常路径）；②输出目录非空拒绝覆盖；③messages 与 build_messages 一致 + gold 注入被拒；④零证据→本地短路、外部尝试 0；⑤合成语料小闭环（extractive 证据包+messages，generator_configured=false）+ 合成混入守卫。

## 2. 一次真实本地 dry-run（真实包 v1.2 / 冻结题集 v2.0）

命令（cwd=`F:\Collage Paper`；下为可复制 PowerShell 形式）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\step2_code\backend\scripts\prepare-real-qa-smoke.py'
```

| 项 | 实测 |
|---|---|
| stdout | `PREPARE OK: 4 题 dry-run 完成；外部请求 0` + 4 个输出文件路径 |
| stderr | 1 条 PDF 解析警告（`Ignoring wrong pointing object`）原样出现，按既有口径不计失败 |
| 退出码 | **0** |
| 输出 | `.cache/real-qa-smoke/T040-A/{dry-run.json, input-hashes.json, generation-review-sheet.md, live-smoke-plan.md}`（同哈希复制到本提交目录） |

覆盖声明（任务书 §4 逐项）：

| 校验项 | 方法与实测结果 |
|---|---|
| 四题请求与冻结 query/conditions 相同 | 脚本从 questions.json 原样取 query/conditions 构造请求体并核对 API 回显（`check_frozen_consistency` 硬校验）：q08/q10 无条件、u03 as_of=2026-10-03、u04 student_type=本科，全部一致 |
| 证据切片/准入正确、候选不混入 | 逐条 E 的 text==原块 [char_start,char_end) 逐字（`check_evidence_slices` 硬校验）；无合成混入；u03 无 db05e0、u04 无 83eb（候选排除硬校验）；四题 evidence_state=ok、各 5 E、跳过 0 |
| messages 与现有 builder 一致且没塞 gold | 脚本直接调用 `qa.deepseek.build_messages` 并重算比对一致；证据块全量在 messages 中；不在证据里的 gold 文本不在 messages（gold_leaks=0，硬校验）；金标准仅离线对照（dry-run `gold_coverage_offline`），未插入 messages |
| 零外部发送 | `answer_provider=None`（/api/v1/ask/status `generator_configured=false`）；build_messages 纯文本构造；脚本无网络代码路径；`external_requests=0`。**未读取 DEEPSEEK_API_KEY**（三启用标志在导入前于本进程关闭，provider_from_env 在读密钥前即返回 None） |
| 已有目录不覆盖 | 输出目录 T040-A 为新目录；复跑同一命令 → `FAIL: 输出目录非空，拒绝覆盖`，**退出码 1（预期）** |

## 3. 输入身份（input-hashes.json 实测 SHA256）

| 输入 | SHA256 前缀 | 对照 |
|---|---|---|
| questions.json | `4e39229e…` | =T039 冻结身份 |
| freeze.json | `8c289b2a…` | =T039 冻结身份 |
| manifest.json（v1.2） | `b05c3755…` | =v1.2 包身份 |
| review-supplement.md | `d82f4c99…` | =T039 提交件 |
| main.py / api/ask.py / qa/evidence.py / qa/deepseek.py / retrieval/service.py / prepare-real-qa-smoke.py | 见 input-hashes.json 全值 | 复用管线源文件快照 |
| 四题条目（canonical JSON） | `a698e2a7…/806ef47a…/b39a221f…/105eab5f…` | 冻结条目快照 |

## 4. 缺口与非结论（如实记录）

- **q08 f1（2 源）金标准缺口**：top-5 检索块未覆盖 gold 跨度（同块相邻分块未进预算），已记录缺口，**未修数据/改条件补齐**。
- q10 f1（50/50）与 f2（互评 40/10/50）各有多源，E1/E2 为真实跨度命中（逐条匹配明细已复核：f1 命中 c888c99a[23,68]/c0ccb884[105,145]，f2 命中 c888c99a[69,122]/c0ccb884[146,202]，span+quote 双重一致）。
- u03 f1 命中 bed3ac/ebab438f[0,452)（⊇ gold [101,129)）；db05e0 未混入。
- u04：无 gold（不足题）；已有命中可能不相关，**不假称已验证拒答**；83eb 未混入。

## 5. 未验证/边界

- **B 阶段未执行、未验证**（live_verified=false）：无任何模型答案、无真实 HTTP、无 usage/费用数据；不伪造价格/预计 usage。
- 真实模型是否忠于证据/能否拒答待验证；程序化一致性≠语义正确/现行性认证；人工核对栏初值均为“待真实运行/待核对”。
- 未跑：全量/UI/ASR/Agent/向量编码/三模式/T030-T039 矩阵/评测重跑/向量重建；未改产品实现/提示/适配器/筛选/评分器/旧冒烟脚本。
