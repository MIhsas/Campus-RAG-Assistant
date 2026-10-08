# T029 验证记录（revision 2，responds_to=T029-R1）

工作目录 `F:\Collage Paper`。零外部模型调用、无下载/安装、未 commit/push；未跑全量/UI/ASR/Agent；未重复向量编码。rev1 记录归档 `rev1/`；Astra 探针/评论未动。

## 1. Astra 隔离探针原样复跑（真实命令，退出码 0）

```powershell
Set-Location 'F:\Collage Paper'
& '.\step2_code\backend\.venv\Scripts\python.exe' 'docs\collaboration\reviews\T029-prepare-probe.py'
```

四场景全 passed（探针通过标准未改、`T029-prepare-probe-v1.txt` 未覆盖）：

| 场景 | 期望 | 实际退出码 | 输出未覆盖 | 报出 |
|---|---|---|---|---|
| initial_build | 成功 | 0 | ✓ | 产品校验器 valid |
| unchanged_verify | 成功 | 0 | ✓ | VERIFY OK: 1 份输入/输出/边车一致（未写入） |
| source_bytes_changed_manifest_unchanged | **失败** | 1 | ✓ | DIFF: 输入原文件 SHA 与数据集声明不一致 |
| selection_evidence_changed | **失败** | 1 | ✓ | DIFF: selection.json / provenance.jsonl 与当前推导结果不一致（结构化比较） |

## 2. 精简业务回归（真实命令，退出码 0）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_prepare_real_corpus.py -q
# 3 passed in 0.17s
```

- 来源站点：`source_site == 已选 URL 主机`（jiaowu.sicau.edu.cn），dataset `site`（rwy.sicau.edu.cn）完整保留于 provenance。
- 输入字节变化 → 非零退出、核验不写入；selection 边车变化 → 非零退出、核验不写入。
- JS 语法（compare 静态文案改动后）：`check-js-syntax.cjs` **All 9 HTML files passed**，退出码 0。

## 3. v1.1 包生成与核验（真实命令）

```bash
./.venv/Scripts/python.exe scripts/prepare-real-corpus.py --dataset-root "F:/Collage Paper/data/datasets/sicau-rag-v1" --selection .cache/t029/selection-v1.1.json --out-dir "F:/Collage Paper/data/corpora/sicau-rag-pilot-v1.1"
# manifest.json: 20 份；产品校验器: valid   退出码 0
# 同命令重跑 ×2：VERIFY OK: 20 份输入/输出/边车一致（未写入）  退出码 0 / 0
```

- **v1↔v1.1 对照**：20 份原文件逐字节一致（SHA 相同）、doc_id 集合相同；manifest 差异**恰为 4 处**——source_site×2（d1fe991c rwy→jiaowu、92049a1c jiaowu→jwnews）、日期×2（bb8ba97c published/effective 2025-11-11、68fb3704 published 2018-12-20）。
- **source_site 同源核对**：20/20 与已选 URL 主机一致（urlparse）；provenance 原站点记录保留（all_sources[0].site=rwy.sicau.edu.cn 等）。
- **日期补正生效对照**（`compute_allowed_document_ids`，as_of_date=2026-10-03）：v1 准入 3/20（bb8b 被 date_unknown 排除）→ **v1.1 准入 4/20（bb8b 已准入）**；68fb 两版均排除（无施行条款不推算生效日）。筛选规则未放宽。
- v1 包保留未动；未绕过 VERIFY 覆盖旧包。

## 4. v1.1 摘录→出处主路径（API 级，零外部请求）

- `GET /api/v1/search/status` → ready；docs 20 / parsed 20 / **synthetic_count=0**。
- `POST /api/v1/ask`（extractive，缓考成绩题）→ 200 evidence_only、5 条；E1=68fb37043ab7/8a790c05/span[0,364]/preview_url ✓（与 v1 同链路）。
- **未重跑**三模式编码/九题（正文同字节；query-checks.json 排名证据对应 v1、与 v1.1 等价——已注明）。

## 5. 证据层级与未验证

**真实核查**：§1—§4 本轮实际执行（探针/回归/包核验/主路径）。
**未运行**：全量测试、UI/ASR/Agent、向量编码、生成/规划；**浏览器复核交 Astra**（不以 stub 冒充）。
**未验证**：真实校园准确率；compare 页级对齐质量（留后续）；其余未核实日期（不扩大调查）。

## 6. 依赖

未安装新依赖；未改产品解析/检索/筛选算法；仅新增 `tests/test_prepare_real_corpus.py`、修订 `scripts/prepare-real-corpus.py` 与 compare 一处静态文案。
