# T029 清单适配与元数据映射说明（mapping-notes.md，revision 2）

> **T029-R1 修正**：source_site 改按已选 source_url 主机解析（dataset sources[].site 常为来源页面站点，二者不总一致）；补正 2 份已核实日期；VERIFY 补输入/边车比对（见 fix-report）。当前包：`data/corpora/sicau-rag-pilot-v1.1/`。

> 数据集 `data/datasets/sicau-rag-v1`（**只读**，含其 verification.json 未动；未原地运行 verify_dataset.py）→ 产品包 `data/corpora/sicau-rag-pilot-v1/`。映射脚本：`step2_code/backend/scripts/prepare-real-corpus.py`（显式 `--dataset-root`/`--selection`/`--out-dir`；重复执行进入核验模式不覆盖）。

## 1. 字段映射（dataset manifest.jsonl → 产品 manifest.json）

| 产品字段 | 取值规则（首批实际执行） | 未知处理 |
|---|---|---|
| document_id | = 数据集 doc_id（64 位十六进制 = 原文件 SHA-256，满足产品 ID 规则） | — |
| policy_group_id | 仅**正文互证**的版本序列共享组；其余独立 `sicau-*` 组 | 未核实关系独立组+记待核实 |
| title | = 数据集 title（据文件正文标题） | — |
| source_url | sources[0].url（附件直链优先）；**全部来源**（含来源页 source_page）保留在包内 provenance.jsonl | — |
| source_site | **已选 source_url 的主机**（urlparse.hostname；T029-R1 修正——dataset `sources[].site` 可能是来源页面站点而非附件主机，原记录完整保留于 provenance all_sources/source_sites） | — |
| local_path | 包内相对路径 `\<doc_id\>.\<ext\>`（原字节拷贝；原相对路径存 provenance） | — |
| sha256 | = 原文件 SHA-256（拷贝后逐文件复核一致；仅核验最终候选文件，不反复哈希 1.32GiB 全库） | — |
| version_label | **正文文号**（如 校教发〔2026〕1号）优先；正文无文号则「未标注」 | 不自封“现行最新版” |
| published_at / effective_from / effective_to | **仅正文或来源记录有据才填**（发文日期、施行条款）——已填 4 项：bb8ba97c 发文/生效 2025-11-11（PDF 第 75 页“自发文之日起施行”+落款）、68fb3704 发文 2018-12-20（PDF 第 2 页落款；无施行条款→effective 仍 null）、85840636 生效 2021-01-01、ddf41747 生效 2012-04-01（施行条款） | 无据=null（多数文档；不为填满扩大调查） |
| scope.campus / student_type / admission_years | 仅可支持值（如正文“本科生”→ ["本科"]） | 未知=**空数组**（≠适用所有人；加筛选时保守排除并如实说明） |
| is_synthetic | false（严格布尔） | — |

**未猜测规则（实际执行记录；T029-R1 复核维持）**：
- `year_hints` 仅线索——**未**用作 published_at/effective_from/admission_year（如转专业 2026 件 year_hints=['2026']，其 published_at=2026-01-08 取自正文发文日期，二者独立）。
- “适用于 2025 年及之后入学”“2024 年及之前按原办法”等**年级区间口径**：契约 admission_years 为整数列表无法表达区间 → 留空数组 + provenance `mapping_limits` 记录原句；用户加年级筛选时这些文档会被保守排除——如实说明，未关闭筛选规避。
- 正文列“三校区”但未逐一列校区名 → campus 留空（不猜校区枚举）。
- 发布主体（四川农业大学/教育部）与转载站点分开记录于 provenance（source_sites 全量保留）；学院网站转载不等于院级制度。

## 2. 版本关系核实（policy_group 共享依据）

> 选择记录对账：25 条 = 20 include + 5 defer（rev1“24 候选”指首轮 include 候选，其中 4 条经正文核实改判 defer：dc7012 解析不全 + f76de/2915/22f7 同版副本；31c7 学院级首轮即 defer）。

| 组 | 成员 | 核实依据（正文） |
|---|---|---|
| `sicau-zhuan-zhuanye`《本科生转专业实施办法》 | 校教发〔2020〕1号 / 〔2023〕1号 / 〔2026〕1号 | 2026 版：“适用于 2025 年及之后入学学生，2024 年及之前入学学生按原《本科生转专业实施办法》（校教发〔2023〕1 号）执行”；2023 版：“自2022级学生开始执行，2022级之前学生按学校原转专业管理办法处理”；2020 版正文文号“校教发〔2020〕1 号”“自 2020 级学生开始执行”。三版施行/适用条款首尾相接，文号递进 |
| `sicau-benke-jiaoxue-guanli`《本科教学管理办法》 | 校教发〔2018〕2号 / 〔2020〕6号 / 〔2022〕12号 / 〔2025〕14号 | 文号递进 + 同标题同结构（第一部分 学生学业管理…）；2025 版施行条款“2025年及之后入学学生按本办法执行，2024年及之前入学学生按原办法执行”（“原办法”原文未指明文号——不强行指定）；2023/2026 转专业文件分别引用〔2022〕12号/〔2025〕14号为制定依据；教发〔2018〕10号补充规定正文“对《本科教学管理办法》（校教发〔2018〕2 号）中关于缓考、补考和再修的有关条例作出补充规定”反证 2018]2号同族身份 |

**保留旧版身份**：三版/四版各自独立 document_id 与 version_label；检索命中某版 ≠ 其适用于当前学生（2023/2020 版“校区间不转专业”与 2026 版“三校区可申请转入”并存，查询见 query-checks q3）。`related_versions`（数据集字段）**未自动合并**——仅在正文互证时共享组，其余记待核实。

## 3. 副本与近似件判定（不混版、不双挂）

| 文档 | 判定 | 依据 |
|---|---|---|
| f76de842a4d0（转专业 2020]1号副本） | **defer 去重** | 与 d4d3092195ed 同文号、文本近逐字（仅排版/措辞细微差异“实施细则/应用”）；同版双挂混淆版本对照 |
| 2915b1895878（试卷评阅规范副本） | **defer 去重** | 与 df04ebec20b8（教发〔2017〕21号）内容逐段一致（无文号页眉） |
| 22f7cfede562（毕业论文规范 DOCX） | **defer 去重** | 与 287dcca750a4（教发〔2016〕10号印发版）正文一致（DOCX 电子稿含表格结构较优——留作后续加工候选，须另存来源映射与派生 hash） |
| c888c99a6409（学生学业管理办法） | **include 独立组** | 标题与《本科教学管理办法》不同；内容与“学生学业管理”部分重叠，制度隶属/版本关系未核实 → `sicau-xuesheng-xueye` 组记待核实 |

## 4. 来源与 provenance

- 包内 `provenance.jsonl`（每文档）：原相对路径、原 SHA、全部 sources（URL/source_page/page_title）、source_sites、selected_source_url/selected_source_site_resolved（按 URL 主机解析，T029-R1 新增字段）、material_type/topic、processing_required/inspection_status、year_hints、related_versions、selection_reason、mapping_limits、数据集 manifest SHA-256。
- 包内 `selection.json`：完整选择清单（include 20 + defer 5 及理由）。
- 数据集 manifest SHA-256：`6a41ff3cdf3eebfe78ad6a555b1b288242d71dff34751a597dc70288e8c4e514`（与 preflight 记录一致）。

## 5. 未做的事（明确）

- 未做泛化全文清洗（页眉/换行沿用解析规则；PDF 折行保留——引用跨度以原块逐字为准）。
- 未对含名单/个人资料文档做处理（首批所选 20 份通读未见名单类内容；若后续发现暂缓并记原因）。
- 未把改写文本冒充原文件字节；未生成派生文本。
- 未合并同文副本进默认包（去重 defer，理由如上）。
