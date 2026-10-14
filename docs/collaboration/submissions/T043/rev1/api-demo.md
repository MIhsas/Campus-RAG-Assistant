# T043 API 演示（api-demo.md，本地 TestClient 实测）

> **层级**：本地进程内 API 实测（**零外部请求**、零模型调用）；数据来自真实包 v1.2。证明的是**准入/状态/消息链路**，不是模型质量。机器记录见同目录 `api-demo.json`。

## 实测（u04 原问题 + student_type=本科，BM25/top_k=5）

| 调用 | include_unknown_student_type | 实测结果 |
|---|---|---|
| `POST /api/v1/search` | **true** | 83eb 进入正式命中/准入集合（`filter_summary.unknown_student_type_document_ids` 含 83eb；reference_count≥1、confirmed+reference=allowed）；其命中携带 **「学生类型未标注，适用范围尚未核实」**；命中正文含明示办理地点（「1 教 105」「217」）；回显模式 true |
| `POST /api/v1/search` | **false** | 83eb **严格排除**（不在命中/未知集合）；普通命中无状态字段（旧协议）；回显 false |
| `POST /api/v1/ask`（extractive） | **true** | 83eb 进入正式 E、逐条携带未核实状态、E 正文含明示地点；回显模式 true |
| `POST /api/v1/ask`（extractive） | **false** | E 不含 83eb、无状态字段 |
| `POST /api/v1/search/candidates`（student_type 维度） | **false** | 候选含 83eb（T038 原 strict 候选保持，可独立查看） |
| 同上 | **true** | 候选**空**——83eb 已正式准入，不重复显示（按本次模式去重） |

## 消息构造（build_messages，本地实测）

- 逐 E 状态真实入消息：`【E?】（学生类型未标注，适用范围尚未核实）` 出现在 user 内容中——**生成器可见**来源状态（非仅 UI 显示）；E 正文（quote）一字未改。
- 系统提示含第 7 条：此类摘录可作参考依据、可给资料中明示的办理信息、必须保留「适用范围尚未核实」提示、不得断言适用于本科生或判资格。
- mock provider 串通测试（测试套件内）：返回引用该 E 的办理地点回答，引用结构校验通过——**mock 非 DeepSeek 真实回答**，外部调用 0。

## 边界

- 本演示不证明生成质量/拒答可靠性/政策现行有效；正式 E 含未核实来源≠适用性已确认。
- u03 相关规则（保留已核实日期、db05e0 不补）无代码变更，见 review-disposition.md。
