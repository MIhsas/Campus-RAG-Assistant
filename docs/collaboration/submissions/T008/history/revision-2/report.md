# T008 检索接口与证据搜索页报告

执行者：Mimo（Claude Code）。执行时间：2026-09-14。task_revision=v1，submission_revision=2。响应 T008-R1。

---

## 0 R1—R4 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | API 严格输入未落实 | SearchRequest 使用 `mode="before"` 验证器：query 纯 str 检查 + 非空白；top_k 拒绝 bool/float/str；handler 移除 strip() |
| R2 | 索引构建异常未降级 | chunk/index 构建捕获 Exception（非仅 ValueError）；message 不含 str(e)；synthetic_count 在分块前计算；测试验证 failed app 仍可提供 preview/health |
| R3 | 重试读取当前输入 | submittedQuery/submittedTopK 与输入草稿分离；重试使用捕获参数；status 有独立 statusSeq；503/catch/JSON 失败各有重试按钮 |
| R4 | 来源展示缺项 | 全合成/部分合成动态提示；三组日期全部展示（null→未标注）；"无有效词元"与"无匹配结果"区分 |

---

## 1 R1：严格输入

```python
@field_validator("top_k", mode="before")
def validate_top_k(cls, v):
    if isinstance(v, bool): raise ValueError(...)
    if isinstance(v, float): raise ValueError(...)
    if isinstance(v, str): raise ValueError(...)
```

`mode="before"` 在 Pydantic 类型强制转换前拦截。`true` → 422，`1.0` → 422，`"5"` → 422。query 不 strip，原样回传。

## 2 R2：构建异常降级

```python
try:
    chunks = chunk_documents(documents, max_chars=500)
except Exception:  # not just ValueError
    app.state.search_status = "failed"
    ...
```

- synthetic_count 在分块前计算（即使分块失败也有值）
- message 固定中文，不插入 str(e)
- 测试：patch chunk_documents 抛 RuntimeError → app 可服务，preview/health 正常

## 3 R3：页面重试状态

- `lastSubmittedQuery` / `lastSubmittedTopK` 存储已提交参数
- `retrySearchParams()` 使用捕获参数，不读取 input.value
- `statusSeq` 独立于 `searchSeq`
- 503/HTTP 错误/JSON 失败/catch 各有重试按钮
- 空白 Enter 在增加 searchSeq 前返回

## 4 R4：来源展示

- 全合成/部分合成动态提示条
- 三组日期：发布/生效/失效，null 显示"未标注"
- 无有效词元：显示"输入内容不包含可检索的汉字或字母数字"
- 无有效索引：显示"无有效索引内容，无法匹配"
- 无匹配：显示"无匹配结果"

## 5 验证

| 检查 | 结果 |
|---|---|
| 全量 pytest | 283 passed, 1 skipped |
| pip check | pass |
| JS 语法（两页） | pass |
| R1: bool/float/string top_k → 422 | pass |
| R1: blank query → 422 | pass |
| R1: query 不 strip | pass |
| R2: RuntimeError chunk → failed + preview ok | pass |
| R2: synthetic_count 在分块前计算 | pass |
| 浏览器交互 | 未验证 |
