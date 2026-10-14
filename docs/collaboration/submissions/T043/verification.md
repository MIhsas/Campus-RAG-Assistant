# T043 验证记录（verification.md，submission_revision=2，responds_to=T043-R1）

> 分层：**本窗口实跑**（前台导航修复相关）｜**Astra 既有证据**（revision 1，沿用不重跑）｜**未验证**。零模型调用、不读密钥。无后端修改 → 未重跑 144 项 Python/模型/全量/实验。

## 1. 本窗口实跑

| 项 | 命令 | 实测 |
|---|---|---|
| search 行为桩 | `node scripts/check-search-behavior.cjs`（cwd=backend） | **24 场景 passed，exit 0**（23+1 新链） |
| ask 行为桩 | `node scripts/check-ask-behavior.cjs` | **41 场景 passed，exit 0**（40+1 新链；首跑 1 处 fixture 时序问题——generate 处理器依赖状态加载——修正 fixture 后通过，产品代码未因此改动） |
| 9 页 JS 语法 | `node scripts/check-js-syntax.cjs` | **All 9 HTML files passed，exit 0** |
| **Astra 导航探针（原样）** | `& 'D:\nodejs\node.exe' docs\collaboration/reviews/T043-navigation-probe.cjs` | **11/11、failures=0、exit 0**（修复前 11 项 3 失败/exit 1）。探针脚本/通过标准未改；结果 json 由原脚本自写、未手改 |

**新增链覆盖**（合并验证，无扩展矩阵）：两方向 URL 恢复→**无需提交**再次跨页（query/filters/document_id/include_unknown_student_type 完整）；旧 strict 历史查看→零请求+「按当时 strict」+导航=历史快照（此前误带最近 reference）；提交后改控件→导航仍用原快照；提交/重试/失败转摘录/候选参数均按快照携带开关。行为桩含**真实 checkbox 控件**（默认 checked、checked 真实读写），非源码字符串检查。

**保全**：探针原失败记录 `T043-navigation-probe-failed-preserved.json`（SHA `9374947e…` 与运行前原件逐字节一致，运行后原件由探针自写更新）；revision 1 八件归档 `rev1/`；用户原件/casebook/gold/freeze/结果/指标/模型输出零写入（身份沿用 revision 1 核对）。

## 2. Astra 既有证据（沿用，本窗口未重跑）

- `tests/test_unknown_student_type.py` 7 passed + 相关 8 文件 137 passed（Astra revision 1 实跑）；T043-audit 34 项 exit 0；真实浏览器参考准入/正式 E/复制验证（T043-browser.json）。
- 真实浏览器复现的 URL 恢复跨页缺陷——修复后**浏览器复验待 Astra 补验**（本窗口无浏览器工具，不代签）。

## 3. 未验证

- 真实浏览器中的导航修复效果、模型回答质量、政策现行性——未验证。
- `confirmed_count` 语义限定为文档说明（非阻断）；计数语义后续统一，本轮未改后端。
