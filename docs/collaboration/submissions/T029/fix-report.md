# T029-R1 定向返工 — 修复报告（fix-report.md）

身份：task_id=T029、task_revision=v1、**submission_revision=2、responds_to=T029-R1**、status=ready_for_review、external_model_calls=0、planner_live_verified=false。仅改：适配脚本与聚焦测试、修订语料包 v1.1、T029 提交资料、backend README、compare 一处静态提示。未改检索/筛选算法、旧 gold、Astra 探针/评论、STATUS/CLAUDE、原数据集；未联网/下载/安装/commit/push。v1 提交件与 v1 包完整保留（`rev1/`、`data/corpora/sicau-rag-pilot-v1/`）。

## 必修 1：重复核验漏检输入变化（prepare-real-corpus.py）

**问题**：VERIFY 只比推导 manifest + 输出文件 SHA；输入文件仅查存在、provenance/selection 未比对——改源文件字节或改 selection 依据说明仍报 exit 0。

**修复**：核验模式补齐六项（不写入、只查选定文件）：① 选定**输入原文件 SHA** 对数据集声明；② 产品 manifest 结构化比较；③ **selection.json** 结构化比较；④ **provenance.jsonl** 逐条结构化比较（JSON 空白差异不影响）；⑤ 输出文件哈希；⑥ 产品校验器有效性。任一差异 `DIFF:` 明确报出、`VERIFY FAILED` 非零退出；构建模式同样先做输入哈希预检（改动输入直接 SystemExit 非零，不写入）。

**真实命令/退出码**：
```powershell
Set-Location 'F:\Collage Paper'
& '.\step2_code\backend\.venv\Scripts\python.exe' 'docs\collaboration\reviews\T029-prepare-probe.py'
# 四场景全 passed：initial_build(0) / unchanged_verify(0) / source_bytes_changed(1, 未覆盖) / selection_evidence_changed(1, 未覆盖)
# PROBE_EXIT=0   ← 探针原样、通过标准未改、T029-prepare-probe-v1.txt 未覆盖
```
- 精简业务回归 `tests/test_prepare_real_corpus.py` **3 passed**（来源站点解析、输入字节变化、selection 边车变化→非零且不写入）。

## 必修 2：元数据与已读来源不一致

**来源站点**：`_map_entry` 改为 `_site_from_url(已选 source_url)`（urlparse hostname）；数据集 `sources[].site`（常为来源页面站点）完整保留在 provenance 的 all_sources/source_sites。实测 20 份 source_site 与 URL 主机**全部一致**；返工单两例已纠：d1fe991c `rwy.sicau.edu.cn→jiaowu.sicau.edu.cn`、92049a1c `jiaowu.sicau.edu.cn→jwnews.sicau.edu.cn`（provenance 仍存 rwy 等原记录，转载站点未当发布主体）。

**日期补正（仅两份，不扩大调查）**：
- `bb8ba97c0a03`（2025 教学管理办法）：PDF 第 75 页「本办法自发文之日起施行」+ 落款/印发 2025-11-11 → `published_at=effective_from=2025-11-11`（selection notes 记页码/原句）。
- `68fb37043ab7`（缓补考成绩规定）：PDF 第 2 页落款 2018-12-20 → `published_at=2018-12-20`；**无明确施行条款，未把落款复制为 effective_from**（保持 null）。
- 其余未核实日期继续 null；未推算旧版统一失效日（各版仍按入学年级分别适用）。

**生效前后准入对照**（`compute_allowed_document_ids`，as_of_date=2026-10-03）：v1 → 3/20 准入（bb8b 被 date_unknown 排除）；**v1.1 → 4/20（bb8b 补正后准入）**；68fb 两版均排除（仅落款无生效日，不放宽筛选）。对照证明是补齐已有依据、非放宽规则。

**新包生成**：`data/corpora/sicau-rag-pilot-v1.1/`（同批 20 份原字节+文档 ID，逐字节核对一致；产品校验 valid）；构建 + 两次重复核验均 `VERIFY OK: 20 份输入/输出/边车一致（未写入）` exit 0。**v1 包保留**、未绕过 VERIFY 覆盖。README/复现命令已指向 v1.1 并列版本差异。

## 随单整理（合并处理）

1. **数量对账**（intake-report 重写）：processing_required（955/144/63/19/1）与 inspection_status（text_extracted 957 / legacy_or_table_review 141 / ocr_needed 60 / non_text 4 / excluded_by_direct_title 20）是**不同维度不相加**；选择记录实为 **25 条（20 include + 5 defer）**（rev1“24 候选”指首轮 include 候选，其中 4 条后被 defer——对账关系已注明）；其余 **1157 条未进入本轮选择（930 可提取文本 + 227 其他处理需求）**，删除“其余≈735”；non_text=4 ≠ 图片 4 份（图片实为 JPG 2+PNG 1）；excluded_by_direct_title=20 属 inspection_status 维度。
2. **scope 口径**：20 份校区/年级全空；**18 份 student_type=[本科]、2 份为空**（83eb3948 学籍指南“适用于所有在校生”、ddf41747 国家教育考试办法）——修正 rev1“17 份”。
3. **演示预期**：demo-notes e 改用已验证的「申请转专业对已修课程有什么要求？」展示三版（2026“均合格”/2023“无补考或重修记录”/2020 同 2023 前 30% 门槛）；不再预言跨校区冲突句出现（rev1 实测其未进 top5）。
4. **真实页面标记**：`static/compare.html` 固定文案「合成资料演示」→「对比说明：对比结果是解析块级文字差异…」（中性；按 `is_synthetic` 的卡片标记保留；比较算法未动）。JS 语法 9 页通过。说明口径：真实 2026/2023 比较「新增 9、删除 5、修改 0、未变 0」为**解析块级**结果，不宣称准确识别所有政策条款变化；PDF 页级大块对齐质量留作后续任务。

## 验证范围与证据层级

- **原样复跑 Astra 隔离探针**（4/4 passed，exit 0）——真实命令如上。
- **精简业务回归 3 passed**（来源站点/输入变化/边车变化）；**JS 语法 9 页通过**（compare 静态文案改动后）。未跑全量/UI/ASR/Agent 边界矩阵。
- **新包核验**：20 份原字节/哈希/来源逐项对照（v1↔v1.1 同字节；manifest 差异恰为 source_site×2 + 日期×2）；重复核验两次 exit 0。
- **未重跑**三模式编码与九题（正文未变、同字节——**旧排名证据对应 v1，与 v1.1 内容等价**，见 query-checks.json 头注）；补一条 v1.1 摘录/出处主路径（API 级：status 20/20/synthetic_count=0；ask E1=68fb3704/8a790c05/span[0,364]/preview ✓）。
- **浏览器复核交 Astra**（不以 stub 冒充浏览器）。

## 未验证项

真实校园准确率（不变）；compare 页级对齐质量（留后续）；其余未核实日期（不扩大调查）。
