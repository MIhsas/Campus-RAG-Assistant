# T003 语料登记与校验报告

执行者：Mimo（Claude Code）。执行时间：2026-09-12。任务修订：v1。submission_revision：2。响应 T003-R1。

---

## 0 R1—R5 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | 字段约束漏检：布尔字符串、假日期、缺 scope、年份类型/范围、空格 campus、URL 主机 | StrictBool、date.fromisoformat、scope 必需无默认、int+range 校验、list+strip 校验、urlparse 主机解析 |
| R2 | 负例测试误通过（sha256="" 掩盖真正错误） | 重写全部测试：有效基线 → 单字段破坏 → 断言精确 error code 和 field → 恢复确认通过 |
| R3 | 异常输入破坏 CLI JSON 契约（TypeError/UnicodeDecodeError 未捕获） | 显式捕获 ValidationError、UnicodeDecodeError；CLI 测试验证非 UTF-8 和 null campus 输出可解析 JSON |
| R4 | document_count 统计文件成功而非结构合法条目 | count = 结构验证通过条目数；重复 ID 不提前返回，继续收集文件错误 |
| R5 | Pydantic 未声明为直接依赖；无符号链接逃逸测试；is_file 替代 not is_dir | pyproject.toml/requirements.in 增加 pydantic>=2.9,<3；符号链接测试（skip if no perms）；is_file() |

---

## 1 完成内容

### 1.1 数据模型（R1 修复）

- `is_synthetic: bool = Field(strict=True)`——拒绝 "false"/"true" 字符串
- 日期验证：`date.fromisoformat()` 替代正则，拒绝 2024-13-01、2025-02-29 等
- `scope` 必需字段，无默认值；`campus`/`student_type` 必须是非空去重字符串数组；`admission_years` 必须是 1900—2100 整数数组
- URL 验证：`urlparse` 提取 hostname，拒绝无主机（`https://?query`）和含凭据的 URL
- 非数组输入（`campus=None`、`campus="abc"`）被 list 类型校验拒绝

### 1.2 校验逻辑（R3+R4 修复）

- Pydantic `ValidationError` 显式捕获，非 ValidationError 异常独立处理
- `UnicodeDecodeError` → MANIFEST_READ_ERROR
- 错误 message 不直接转发英文 Pydantic 消息
- `document_count` = 结构验证通过条目数，非文件检查成功数
- 重复 ID 不提前返回，继续收集可执行的文件级错误
- `is_file()` 替代 `not is_dir()`

### 1.3 依赖声明（R5 修复）

- `pyproject.toml`：dependencies 增加 `pydantic>=2.9,<3`
- `requirements.in`：增加 Pydantic 直接依赖说明

### 1.4 测试（R2 重写）

76 项通过，1 项 skipped（符号链接权限不足）。新增：
- 精确布尔严格测试（"false"/"true" 拒绝，True/False 通过）
- 真实日期测试（月份/日期/闰年/时间戳）
- scope 必需测试（缺 scope、空 scope）
- admission_years 类型+范围测试
- campus 元素验证（空格、非列表、null、非字符串元素）
- URL 主机验证（无主机、凭据）
- document_count 契约测试（结构合法 vs 文件成功）
- CLI 非 UTF-8 和 null campus JSON 输出测试
- 符号链接逃逸测试（skip if no perms）

---

## 2 文件清单

见 `changed-files.json`（20 个文件）。

---

## 3 已知限制

1. 符号链接逃逸测试在当前环境无权限创建，已 skip 并记录实际 OSError。
2. Pydantic 的 `campus="abc"` 被 `list[str]` 类型校验拒绝（"必须是数组"），而非字符级校验。这是正确的：非数组输入不进入元素验证。
3. 弃用警告保留，不盲目升级依赖。
