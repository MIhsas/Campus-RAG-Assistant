# 筛选 API 演示说明（filter-demo.json）

真实本地 BGE（bge-small-zh-v1.5）+ 合成夹具 `examples/filter-demo/`（5 文档，均含“缓考申请”），经真实 create_app 与 POST `/api/v1/search`（mode=hybrid）。**合成资料，不代表四川农业大学真实政策。**

## 复现命令

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-filter-search.py --model-path models\bge-small-zh-v1.5 --corpus examples\filter-demo
```

## 夹具覆盖

| 文档 | 校区 | 年级 | 生效 | 失效 |
|---|---|---|---|---|
| fd-2024 | 成都 | 2024 | 2024-09-01 | 2025-08-31 |
| fd-2025 | 成都 | 2025 | 2025-09-01 | 未标注 |
| fd-yjy | 都江堰 | 2024/2025 | 2024-09-01 | 未标注 |
| fd-unknown | 未标注 | 未标注 | 未标注 | 未标注 |
| fd-future | 成都 | 2026 | 2026-09-01 | 未标注 |

## 六个场景的预期与实测一致

1. **no-filters**：5 文档均可准入（allowed=5），排名为全库行为。
2. **year-2024**：只准入 fd-2024、fd-yjy（allowed=2）。
3. **year-2025**：只准入 fd-2025、fd-yjy（allowed=2）。
4. **as-of-2024-10-01**：fd-2025 尚未生效、fd-future 未生效、fd-unknown（effective_from=null）被排除（allowed=2）；注“1 份适用文档未标注截止”（fd-yjy）。
5. **as-of-2025-09-10**：fd-2024 已失效被排除（allowed=2）；注“2 份未标注截止”（fd-2025、fd-yjy）。
6. **chengdu-2024-as-of-2025-09-10**：成都+2024+该日期下唯一候选 fd-2024 已过期 → allowed=0、hits=[]，`filters` 原样回显，**不悄悄取消条件**。

## 其他核对点

- 同题换年级/日期 → 命中文档集合变化（场景 2/3/4/5），满足“不同结果”要求。
- `encode_documents_calls=1` 且重复查询后仍为 1：正文向量仅在应用创建时批量构建，查询只编码 query。
- status 身份：`embedding_model=bge-small-zh-v1.5`（无本机路径）、`embedding_model_revision=7999e1d3359715c523056ef9478215996d62a620`（下载元数据核实）、`truncated_chunk_count=0`、`embedding_error=null`。
- 每个场景的 hits 均只含准入集合内文档（三模式同集合；演示跑 hybrid，单测已覆盖三模式）。
