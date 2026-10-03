# T005 语料预览与来源定位报告

执行者：Mimo（Claude Code）。执行时间：2026-09-13。任务修订：v1。submission_revision：2。响应 T005-R1。

---

## 0 R1—R5 修复摘要

| 编号 | 问题 | 修复 |
|---|---|---|
| R1 | renderDetail 替换 innerHTML 后访问已删除旧节点 | 使用 textContent 清空后再 createElement 构建，不访问旧节点 |
| R2 | handleHash → selectDoc → updateHash 丢掉 block_id | selectDoc 接受 blockId 参数并传递；processPending 处理 docs 加载完成后的待处理 hash；未知 block_id 显示提示；无无限轮询 |
| R3 | synthetic-banner 固定、缺错误明细/空状态/键盘操作 | banner 按 is_synthetic 动态显示；status bar 下方显示错误明细；无匹配/未配置/网络错误有明确提示和重试按钮；列表项改为 button 元素可聚焦 |
| R4 | esc/innerHTML 拼接数据存在属性注入风险 | 全面改用 createElement + textContent；URL 通过 .href 属性赋值；copy 链接用 addEventListener 替代 inline onclick |
| R5 | 无响应模型、wheel 缺静态资源、重复校验 | Pydantic 响应模型（CorpusStatusResponse/DocumentListResponse/DocumentDetailResponse/ErrorResponse）；pyproject.toml 增加 package-data；main.py 仅调用 parse_manifest 一次 |

---

## 1 preview.html 重写

- **安全 DOM**：所有数据通过 `createElement` + `textContent` 渲染，不使用 `innerHTML` 拼接用户数据
- **URL 链接**：通过 `a.href = url` 属性赋值，仅允许 http/https，`rel="noopener noreferrer"`
- **事件绑定**：所有交互通过 `addEventListener`，无 inline onclick
- **节点生命周期**：`detail.textContent = ''` 清空后再构建新内容，不访问旧节点
- **Hash 定位**：`selectDoc(docId, blockId)` 保留 blockId；`processPending()` 在 docs 加载后处理待处理 hash；未知 block_id 显示"未找到指定正文块"
- **状态完善**：banner 动态显示合成/真实状态；错误明细显示在 status bar 下方；空列表显示"无匹配文档"/"暂无文档"；网络错误显示重试按钮

## 2 后端修改

- **main.py**：移除 `validate_manifest` 调用，仅 `parse_manifest` 一次（包含校验）
- **corpus.py**：新增 `CorpusStatusResponse`、`DocumentListResponse`、`DocumentDetailResponse`、`ErrorResponse` Pydantic 模型
- **pyproject.toml**：新增 `[tool.setuptools.package-data]` 包含 `static/*.html`

## 3 测试

151 passed, 1 skipped。新增：单次 parse 调用验证、OpenAPI 响应模型验证。wheel 构建确认 `preview.html` 包含在内。

## 4 浏览器交互验证

Claude Code 无浏览器能力，**未进行浏览器交互验证**。以下项交由 Astra 复核：
- 文档详情渲染（R1 修复后应可正常显示）
- 复制块链接 + 刷新回查定位（R2 修复后应保留 block_id）
- 键盘操作（列表项可 Tab 聚焦、Enter 选择）
- 合成/真实混合 banner 显示
- 未配置/无匹配/错误状态显示
- 带 HTML 标签的合成正文以文本显示
