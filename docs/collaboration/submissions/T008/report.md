# T008 检索接口与证据搜索页报告

执行者：Mimo（Claude Code）。执行时间：2026-09-14。task_revision=v1，submission_revision=4。响应 T008-R3。

---

## 0 R1—R3 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | DOCX InvalidXmlError 逃出迭代边界 | `except Exception` 替代具体异常列表，隔离第三方 XML/格式异常，返回 DOCUMENT_PARSE_ERROR |
| R2 | 空白提交未恢复按钮 | 空白分支添加 `btn.disabled = false` |
| R3 | ID 正则 `$` 接受尾换行 | `_ID_PATTERN` 改用 `\Z` 严格匹配字符串末尾 |

---

## 1 R1：DOCX 异常隔离

```python
# Before: except (ValueError, TypeError, KeyError, AttributeError, ET.ParseError)
# After:
except Exception as e:
    return [], [_error(DOCUMENT_PARSE_ERROR, ...)], warnings
```

- InvalidXmlError（python-docx 从 malformed gridSpan 抛出）被正确捕获
- 正常 TXT + 坏 DOCX：valid=false、保留正常文档、CLI exit 1、无 traceback
- 仅坏 DOCX：failed、search 503、live 200

## 2 R2：按钮状态

```javascript
if(!query.trim()){
  // ...
  btn.disabled = false;  // restore immediately
  return;
}
```

## 3 R3：ID 严格匹配

```python
# Before: re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
# After:  re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
```

`\Z` 不匹配尾换行。新增 8 项 ID 验证测试。

## 4 验证

| 检查 | 结果 |
|---|---|
| 全量 pytest | 295 passed, 1 skipped |
| pip check | pass |
| JS 语法 | pass |
| R1: InvalidXmlError 隔离（parse + factory） | pass |
| R2: 空白提交按钮恢复（源码确认） | ✓ |
| R3: ID 尾换行拒绝 | pass |
