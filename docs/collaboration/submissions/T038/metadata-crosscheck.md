# T038 元数据补正对照（metadata-crosscheck.md）

> 范围：`data/corpora/sicau-rag-pilot-v1.2/`（新包）相对 v1.1 的**唯一差异 = bed3ac 日期补正**。旧 v1/v1.1 与 `data/datasets/sicau-rag-v1/` 只读未改。日期区间核查≠现行有效认证。

## 1. 新包身份与构建

| 项 | 值 |
|---|---|
| 构建命令 | `python scripts/prepare-real-corpus.py --dataset-root ../../data/datasets/sicau-rag-v1 --selection .cache/t038/selection-v1.2-input.json --out-dir ../../data/corpora/sicau-rag-pilot-v1.2`（复用既有构建/验证逻辑，旧输入输出未动） |
| 构建 | `manifest.json: 20 份；产品校验器: valid`，exit 0 |
| 核验模式（同命令重跑） | `VERIFY OK: 20 份输入/输出/边车一致（未写入）`，exit 0 |
| 原件一致性 | 20 份原文件 SHA 与 v1.1 **逐字节相同**（IDs 一致）；块 ID 全集 1031 个不变 |
| manifest 差异 | **仅 2 字段**：bed3ac `published_at: null→2019-11-07`、`effective_from: null→2019-11-07`；其余字段与文档全部一致 |
| 边车 | selection.json（含修订备注）/provenance.jsonl 自动生成，记录差异理由 |

## 2. 日期补正证据（真实解析块切片，构建时逐字核对）

| 证据 | 块/跨度 | 切片 | 作用 |
|---|---|---|---|
| 落款 | `bed3ac…/f3cdb912` | 「四川农业大学\n 2019年11月7日」 | 发文主体与日期 |
| 印发 | `bed3ac…/a3536032` | 「四川农业大学党政办公室 2019年11月7日印」 | **末字解析为「印」——不补写「发」**；含日期的实际切片 |
| 生效条款 | `bed3ac…/c641f172[135:206]` | 「本办法自发文之日起执行，由教务处负责解释。以往有关规定与本办法不符之处，以本办法为准；…」 | 生效日=发文日→2019-11-07 |

2019 文号（标题注 2019 年 7 号）本轮仅记录，不扩大字段修改。

## 3. 准入变化（现有筛选服务，as_of=2026-10-03）

| 语料包 | allowed | bed3ac | db05e0 | 无筛选 |
|---|---|---|---|---|
| v1.1 | 4/20 | 排除（date_unknown_from） | 排除（date_unknown_from） | 全部 |
| **v1.2** | **5/20** | **准入** | **仍排除（日期保持未知）** | 全部（None=不限制） |

- 83eb scope 保留未知（不改）；db05e0 日期保持未知（正文无任何日期）。
- 明确：**日期区间核查 ≠ 现行有效认证**；历史冻结实验（T030/T031/T034）输入仍是 v1.1，运行可显式指定 v1.1 复现旧基线；**v1.2 不是旧冻结实验的输入**。本任务不改 u03/u04 gold、不重计指标、不重编码向量。

## 4. 旧数据/实验证据（只读核对，前后 SHA 未变）

| 文件 | SHA |
|---|---|
| v1.1 manifest | `34e182f18178c8a8…` |
| T030 questions v1.3 | `5fde70a332744b64…` |
| 模板 procedures v1.2 | `78f1c1d9f839c41d…` |
| T031 / T034 experiment | `57b22f93bd1420fa…` / `cef9f162f1eb164a…` |
| 用户意见记录 | `2e1af1493846efd7…`（109/3/2 保留，不代关闭争议） |

v1.2 manifest SHA=`b05c37557675f02c…`（新包身份，与旧包区分）。
