# T003 语料登记与校验报告

执行者：Mimo（Claude Code）。执行时间：2026-09-12。任务修订：v1。

---

## 1 完成内容

### 1.1 语料登记校验模块

- **数据模型**（`corpus/models.py`）：Pydantic v2 模型，schema_version="1.0"，Document 含全部必需字段，Scope 含 campus/student_type/admission_years。extra="forbid" 拒绝未知字段。
- **校验逻辑**（`corpus/validate.py`）：6 步校验——读取清单、JSON 解析、Pydantic 结构验证、重复 ID 检查、路径安全检查、文件完整性校验（SHA-256 分块计算）。
- **CLI 入口**：`python -m campus_assistant.corpus.validate --manifest ... --corpus-root ...`，stdout 输出 JSON（valid/document_count/errors），exit 0=成功，1=校验失败，2=参数错误。
- **错误码**：MANIFEST_READ_ERROR、MANIFEST_SCHEMA_ERROR、DUPLICATE_DOCUMENT_ID、UNSAFE_LOCAL_PATH、FILE_NOT_FOUND、FILE_READ_ERROR、HASH_MISMATCH。

### 1.2 合成测试语料

- `examples/synthetic-corpus/policy-abc-v1.txt` 和 `policy-abc-v2.txt`：共享 policy_group_id `syn-policy-abc`，不同 version_label，说明分组不等于自动判定新旧效力。
- `manifest.json`：有效清单，2 项登记，is_synthetic=true，source_url 用 example.org。
- 所有合成文件标注"合成测试"，不得用于论文评测或真实校园问答。

### 1.3 T002 遗留整理

- **中间件统一 request ID**：middleware 生成 UUID 存入 `request.state.request_id`，health 路由读取该值，响应头由中间件统一写入。
- **.gitignore**：新增 `.pytest_cache/`，`.env.*` 规则后允许 `.env.example`。
- **README**：所有 pip 命令增加 `--cache-dir .cache/pip`，新增语料校验章节。

### 1.4 测试覆盖

34 项语料校验测试 + 16 项健康回归测试 = 50 项全部通过。

覆盖场景：
- 合法清单（中文路径、未知范围空数组）
- 缺字段、未知字段、非法 URL（无 scheme/含凭据）、布尔字符串、非法日期、倒置日期
- 重复 document_id
- 绝对路径、盘符、UNC、路径穿越（..）、ADS 冒号
- 缺失文件、目录当文件、哈希不符
- 多文件错误同时返回
- 校验不改写输入清单
- CLI subprocess 成功/失败退出码及 JSON 输出

---

## 2 文件清单

见 `changed-files.json`（20 个文件）。

新增/修改的业务文件：

| 类别 | 文件 | 说明 |
|---|---|---|
| 新增 | `corpus/__init__.py`、`corpus/models.py`、`corpus/validate.py`、`corpus/__main__.py` | 语料校验模块 |
| 新增 | `examples/synthetic-corpus/*`（4 文件） | 合成测试语料 |
| 新增 | `tests/test_corpus_validate.py` | 语料校验测试（34 项） |
| 修改 | `main.py` | 中间件统一 request ID |
| 修改 | `api/health.py` | 路由读取 request.state |
| 修改 | `README.md` | 缓存目录、语料章节 |
| 修改 | `step2_code/.gitignore` | pytest_cache、env.example |

---

## 3 验证结果摘要

| 编号 | 行为 | 结果 |
|---|---|---|
| 1 | 合法清单含中文路径与未知范围 | ✅ 通过 |
| 2 | 缺字段/未知字段/非法 URL/布尔字符串/非法日期/倒置日期 | ✅ 全部拒绝 |
| 3 | 重复 document_id | ✅ 检测并报告 |
| 4 | 绝对路径/盘符/UNC/路径穿越/ADS | ✅ 全部拒绝 |
| 5 | 缺失文件/目录当文件/哈希不符 | ✅ 分别报告 |
| 6 | 多文件错误同时返回 | ✅ 收集全部错误 |
| 7 | 校验不改写输入 | ✅ 文件内容不变 |
| 8 | CLI 成功退出码 0 / 失败退出码 1 / 用法错误退出码 2 | ✅ 通过 |
| 9 | 示例 CLI 成功（2 文档通过） | ✅ valid=true |
| 10 | 损坏哈希 CLI 失败 | ✅ valid=false, HASH_MISMATCH |
| 11 | 健康接口回归（live 200, ready 503） | ✅ 通过 |
| 12 | 全量 pytest 50 passed | ✅ 通过 |
| 13 | pip check | ✅ No broken requirements found |

---

## 4 已知限制

1. 未固化校区和培养类型字典（避免未核对真实资料就写死）。
2. 不联网验证 URL 可达性或权威性。
3. 路径安全检查基于字符串解析，未经 symlink 创建测试（Windows 无 symlink 创建权限时不声称已覆盖）。
4. 合成测试资料不能用于论文评测或真实校园问答。
5. Pydantic 弃用警告（Starlette TestClient、anyio）保留，不盲目升级。
