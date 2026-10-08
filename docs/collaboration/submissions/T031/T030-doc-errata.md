# T030 文档勘误（T030-doc-errata.md，随 T031 提交）

来源：T030-R3 验收「非阻断文案整理（并入 T031，不再为此返工）」。**只补勘误，不改已验收的 T030 历史数据、结果与冻结**（`data/evaluations/sicau-rag-pilot-eval-v1/` 与其归档全部只读）。以下勘误指向 revision 3 提交材料中的表述（`submissions/T030/` 及其 `rev2/` 归档保持原样）。

1. **q05 手算的 rank 表述**（evaluation-report §6 q05 段）：同排名双 gold 对照中写过「rank1 的 287d/842680f7 命中即满足 f1 → MRR=1/2=0.5（dense 输出首相关 rank=2）」，rank1 与 rank2 混写。正确表述：**Dense 在 v1.2/v1.3 gold 下首相关为 rank2，MRR=1/2=0.5**；rev1 gold（2 源）下首相关 rank5、MRR=0.2。Hybrid：rev1 gold rank3（1/3）→ 新 gold rank1（1.0）。指标数值本身无误。
2. **O3 的「18 题」口径**（evaluation-report §5 O3）：「gold 未变的 18 题分数零漂移」是 **v1.2 轮口径**（v1.1→v1.2 时 18 题 gold 未变）。**v1.3 轮（T030-R2）** 的口径是 **22 题×3=66 分数零漂移 + 72/72 排名一致**，另有 q10 gold 修改但重计分后分数不变（两组集合不同：q10 在「gold 变化但分数不变」组，不在 66 计数内）。
3. **「显著低于」措辞**（evaluation-report §2 按题型表后的句子）：「指定版本组仍是失分集中区」一句若用「显著」措辞，均**不表示统计显著**（单次小样本、未做显著性检验）；应读作「本集数值较低」。
4. **O2 的指标名**（evaluation-report §5 O2）：「q10 跨版本源补全后三模式由部分/零分升至满分（bm25 0→1、dense 0→1、hybrid 0.25→1）」——其中 hybrid 0.25→1 是 **MRR** 的变化（Recall/Hit 在 rev1 gold 下为 1/1/0.25 与 1/1/1.0 的对比），应标明指标名，不写成无指标的裸数字。

（完。T030 revision 3 基线本身不变：题集 `5fde70a3…`、BM25 0.725/0.750/0.600、Dense 0.700/0.700/0.443、Hybrid 0.700/0.700/0.542。）
