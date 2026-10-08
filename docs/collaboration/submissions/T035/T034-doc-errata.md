# T034 文档勘误（T034-doc-errata.md，随 T035 提交）

来源：T034-R1 验收「非阻断的说明收尾（并入 T035，无需重跑实验）」。**只补勘误，不覆盖 T034 原始数据/冻结文件/历史提交**（`data/evaluations/sicau-rag-overlap-v1/` 与 `submissions/T034/` 保持原样）。以下勘误指向 T034 提交材料（`submissions/T034/experiment-report.md` 等）中的表述；机器算分与「默认不采用」结论不变。

## 1. 边界案例的候选窗口按实际跨度表述

experiment-report §3 曾写 q10 案例 candidate 窗口「[400,900)」——该值是按通用 500/100 步长的示意，**不是实际生成窗口**。核准实际几何（块长决定尾窗）：

| 案例 | 块 | 块长 | gold 跨度 | 实际 candidate 窗口 | 实际覆盖窗 |
|---|---|---|---|---|---|
| q10 f1-s7 | bb8ba97c/090f4a9c | **506** | [470,503) | (0,500)、**(400,506)** | [400,506) |
| q20 f1-s2 | cc25a92b/7270f8a8 | 569 | [490,534) | (0,500)、**(400,569)** | [400,569) |

边界覆盖收益仍成立（两跨度均被 baseline 硬边界切开、被 candidate 尾窗完整覆盖）；表述以本表为准。

## 2. q10/q11 的回退不归因于 top5 重复命中

experiment-report §4 曾把回退与「重复区间挤占」并列叙述。机器值（experiment.json dup_stats）：**q10 dense 与 q11 dense 的 candidate top5 同块/重叠对数均为 0**（两题两模式 same_block_pairs=0、overlapping_interval_pairs=0）。两者的回退应记录为**重叠窗口改变 chunk 文本/起点后的排序变化**（q11：43602ebd 事实块跌出 top5；q10：首相关 rank1→2），不是 top5 内重复命中挤占。**q17 bm25 确有 1 对重叠区间相伴**（10ea5893 的 (0,500) 与 (400,507) 同占两位）——仍按「观察到同时发生」记录，不作进一步因果推断。全部重复区间统计：BM25 4/24 题、Dense 3/24、Hybrid 3/24 存在同块/重叠命中（各 4 对），其中不含 q10/q11。

## 3. 「默认逐字节兼容」的范围限定

「逐字节兼容」应限定为 **`chunk_documents` 产出的 chunk 列表**：默认（overlap=0）1231 个 chunk 的 ID/文本/跨度/字段/顺序与历史实现逐键一致（Astra 独立比对 1231/1231 dict 相等；golden ID 回归通过）。**`chunk_manifest`/CLI 顶层新增 `overlap_chars: 0` 字段**——不能声称整个 CLI JSON 输出字节未变。实际服务默认检索行为兼容已验证（BM25 旧路径 24 题排名全一致）。

## 4. frozen-config 的历史元字段与当前题集版本

`data/evaluations/sicau-rag-overlap-v1/frozen-config.json` 的 `t030_results_identity.dataset_version` 显示 **1.1**——这是 T030 存储结果文件中**保留的旧元字段**（结果文件生成时写入，后续合并未回写）。**当前题集版本为 v1.3**，以 SHA-256 `5fde70a332744b64…` 识别（与 frozen-config 的 questions_sha256 吻合）。两者区别如上；**不修改 T030 历史文件**。

（完。T034 结论不变：收益与代价抵消且不稳定，维持产品默认 overlap=0，参数保留为显式实验选项；gold 仍模型辅助、人工未复核；不足题空检索率不是拒答率。）
