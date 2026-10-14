# T043 验证记录（verification.md）

> 范围=变更相关聚焦验证（检索/筛选/search/ask/候选/生成消息 + 两页必要检查）；**未跑全量/旧大矩阵/模型下载/三模式评测**。零外部模型调用、不读密钥/环境。分层：**本轮实测**｜**历史引用**｜**未验证**。

## 1. 本轮实测

### 1.1 聚焦测试（新增 tests/test_unknown_student_type.py）

```text
python -m pytest tests/test_unknown_student_type.py -q   （cwd=backend）
# 7 passed，退出码 0
```

| 链 | 实测 |
|---|---|
| 真实包 u04 + 本科 + 新模式 | 83eb 进正式命中/E：状态=「学生类型未标注，适用范围尚未核实」、正文含明示地点（1 教 105/217）、filter_summary 分列（confirmed+reference=allowed、unknown 集合含 83eb）、模式回显 true |
| 同题严格模式 | 83eb 排除、普通命中无状态字段、模式回显 false；**候选仍可独立查到 83eb**（T038 原 strict 候选保持）；新模式下候选**去重为空**（83eb 已正式准入不重复显示） |
| 合成夹具 | 已知**研究生冲突仍排除**；日期未知/已失效仍排除（其它维度不放宽）；默认 compute **strict**（办事/自查/旧 CLI 保护）；无学生类型条件=原无筛选行为；三模式 stub 共用同一准入集合；document_id 求交（被排除文件→空集短路不回退） |
| 消息/mock | 逐 E 状态真实入 messages（`【E1】（…未核实…）`）；quote 未改写；系统提示含范围保留规则；mock provider 引用该 E 的办理地点串通引用结构（**mock 非模型质量**，外部调用 0） |
| 两页结构 | 新开关（默认 on）、body 带 `include_unknown_student_type`、提交快照、重试/转摘录用快照、跨页 `include_unknown_type`、候选同模式、历史缺字段=当时 strict 展示 |

### 1.2 回归（相关旧套件）

```text
python -m pytest tests/test_search_filters.py tests/test_search_api.py tests/test_ask_api.py tests/test_uncertain_sources.py tests/test_qa_evidence.py tests/test_procedures.py tests/test_self_check.py tests/test_deepseek_provider.py -q
# 137 passed，退出码 0
```

旧 strict 预期**无需改写**：filters 单元测试经默认 strict 参数覆盖不删；旧 API 测试无需显式 false（其断言不涉未知排除语义）。办事/自查严格核查保持（test_procedures/test_self_check 通过）。

### 1.3 API 演示（本地 TestClient，零网络）

`api-demo.json/md`：六条实测（search/ask × 新模式/严格、candidates × 两模式）+ build_messages 状态传递。83eb 入 E 含明示地点、严格排除、候选按模式去重、消息含状态——逐项如 api-demo.md。

### 1.4 保全核对

- 用户原件（SHA `7a0c6ec4…`）/T036 记录/gold/freeze/结果/aggregate/metadata/模板/T039—T042 提交与包/casebook：**零写入**（casebook 原字节，测试断言外清单见 changed-files）。
- 改前 docs 三件（README/system-design/human-review-pending）归档 `docs/delivery/archive-t043-pre/`（哈希 52240b07/3a54c639/bca58be9 与改前一致）。

## 2. 历史引用（未重跑）

T042 接收核对 21 项（Astra）；T040/T039 旧 strict 边界记录；T038 候选功能。历史数字未改。

## 3. 浏览器

本窗口**无真实浏览器工具**：页面行为为源码结构级证据；[demo-notes.md](./demo-notes.md) 提供 7 步人工短检查表。不冒充浏览器、不绕过工具拒绝。

## 4. 未验证（不代填）

- 模型生成质量/资格判定/政策现行有效——**未验证**（本轮零模型调用）。
- 新准入模式的检索基线指标——未评测（后续单独安排，不编造）。
- 真实浏览器渲染行为——待用户/Astra 按 demo-notes 走查。
