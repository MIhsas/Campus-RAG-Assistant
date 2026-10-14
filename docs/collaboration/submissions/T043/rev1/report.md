# T043 意见落档与未知学生类型正式准入 — 实施报告（report.md）

身份：task_id=T043、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**、planner_live_verified=false。
范围：①T042 八项真实意见落档（全部确认）+ 两条聊天决定记录；②小型产品策略/快照/消息调整（`include_unknown_student_type` 参考准入）。**零模型调用**（不读密钥/环境、不发任何模型 HTTP）；旧付费授权已结束，新准入实施授权≠模型调用授权。旧 T036/T039/T040/T041/T042 提交/包/用户 JSON/gold/freeze/结果/aggregate/metadata/模板/Astra 文件只读，数字未改。

## 1. 意见落档（[review-disposition.md](./review-disposition.md)）

原件 `data/reviews/T042-user-review-20261014/targeted-review-record.json`（SHA `7a0c6ec4…`，原字节只读）：**8 项均确认**（四修订+四结果），签名/日期空不补签；原 opinion/comment 照录。两条聊天决定分列保存：u04「让正式答案也采用范围未知的资料」、u03「保留已核实的日期，不再额外补充来源」。旧 109/3/2、模板 33、本 8 项**分域记录不相加**；确认≠教师审定/现行认证。delivery 侧新增 [review-disposition-T043.md](../../docs/delivery/review-disposition-T043.md) 作当前状态索引；generation-casebook **原字节冻结**，当前确认状态经落档链接说明。

## 2. 新准入模式实施（仅 student_type 未知维度）

- **开关** `include_unknown_student_type`（严格布尔）：正式 search/ask **默认 true**（两页 UI 默认开、可关回 strict）；**底层 `compute_allowed_document_ids` 默认仍 strict**（办事/自查/旧 evaluation CLI 保护，显式传参才放宽）。
- **语义**：仅 student_type 未标注→参考准入（统计分列已匹配/未标注参考，不冒充适用性确认）；**已知类型冲突（研究生）仍排除**；campus/年级未知或冲突、日期未知/未生效/失效照旧排除（u03 日期规则保持、db05e0 不入）；document_id 求交、先准入后 TopK、BM25/向量/RRF 不变；不硬编码 u04/83eb、不塞 gold、不改 quote/manifest。
- **状态透传**：命中/E/复制文本/结果快照标「学生类型未标注，适用范围尚未核实」；`build_messages` 逐 E 写入状态（生成器可见），系统提示第 7 条允许据实给明明示办理地点并保留范围提示、不判资格。
- **候选/快照/历史**：开启时候选按本次模式去重（已准入含参考不重复显示），关闭时 T038 原 strict 候选保持；两页快照、重试/转摘录、历史、跨页携带开关；**旧历史缺字段=当时 strict**，不重解释历史。
- **办事/自查**：严格核对不变（回归 137 项通过含此保护）。

## 3. 验证摘要（详见 verification.md / api-demo.md / demo-notes.md）

聚焦测试 **7 passed**（真实包 u04：新模式 83eb 入正式 E 含明示地点+状态、严格排除+候选独立查看、ask 透传、候选去重；合成夹具：研究生冲突/其它维度/document_id/三模式共用准入/默认 strict；消息状态+mock 引用串通；页面结构）；回归 137 passed。API 演示本地实测六条调用+消息构造（零网络）。**无真实浏览器**：如实源码结构级+demo-notes 短检查表。若真实包 TopK 未命中 83eb 相关块则测试如实跳过硬凑断言（本次实测命中）。

## 4. 边界与未验证

- 新准入≠适用性已确认/资格判定/现行有效；mock≠模型质量；**本轮 external_model_calls=0**，未执行 live。
- 模式新基线未评测（后续单独安排）；旧历史 T040 的 u04 strict 不足标签不用于新模式计分。
- 用户 8 项确认引用真实记录，不写教师认证或新质量评测。

完成后停止，等待 Astra 验收；不推进 T044。
