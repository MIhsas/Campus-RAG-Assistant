# T015 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。执行工具为 Git Bash。按任务只做相关验证：JS 语法、ask 行为回归与新增主流程 stub 验证、本地 mock 演示入口实跑；无后端变更未重跑全量 pytest/embedding/评测。**external_model_calls=0（无任何外部请求）。**

## 1. JS 语法与行为检查

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# ask.html: syntax OK / preview.html: syntax OK / search.html: syntax OK
# All 3 HTML files passed syntax check.
# 退出码：0

"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 13 scenarios passed
# 退出码：0
```

13 场景 = 原 9（快照/状态刷新保筛选/重试快照/复制/空态/生成器未配置/受控生成渲染等）+ 新 4：

- **S9 引用定位**：生成段落 E1 引用点击 → 对应证据卡获得 highlight 高亮，卡片保留“查看原文”。
- **S10 失败转摘录**：502 生成失败 → 标签“生成失败 / 未返回答案”→“查看本次问题的原文依据”按钮 → 以失败请求的问题/年级 2023 快照发 extractive 请求（控件事后被编辑为空也不丢条件）、answer_mode=extractive（不调模型）、结果回到“原文摘录 / 未生成答案”。
- **S11 本机历史**：开启保存后两条结果入库（含材料不足）；“查看”恢复**零新请求**且带“历史结果，资料可能已更新”横幅；删除单条生效；取消勾选提示“仍保留”；清空后提示“未开启保存”。
- **S12 存储不可用**：写入失败时提示“本机存储不可用”，问答结果正常渲染不受影响。

调试记录：首跑两处失败——generate 按钮处理器依赖页面内 `generatorConfigured`（stub 状态须在初次 status 加载前置位）；历史提示措辞与断言不一致（统一为“仅保存在此浏览器本机”）。均为测试脚本/文案问题，修正后全过。

## 2. 本地 mock 演示入口实跑（零外部请求）

```bash
./.venv/Scripts/python.exe scripts/demo-ask-page-mock.py --port 8012 &
# GET /ask → 200
# GET /api/v1/ask/status → generator_configured: True | identity: mock:page-demo（模拟，非真实 DeepSeek）
# POST generated（UTF-8 请求文件）→ status=generated，段落带【模拟输出，非真实 DeepSeek 回答】，cites ['E1']，meta.model=mock-page-demo
# POST "模拟失败测试" → GENERATOR_ERROR「生成器执行失败：RuntimeError；可改用原文摘录…」
# POST "宿舍门禁时间是几点？" → insufficient_evidence「无可用证据，未调用生成器。」（本地短路，generation_meta=null）
# 服务由本会话启动并停止（kill 本会话进程）
```

退出码 0/200 正常；模拟回答全程带明显标记，fake 不在 main.py/demo.py 启动路径。
备注：Git Bash curl 直接携带中文 JSON 会因控制台编码导致服务端解析失败（与产品无关），改用 UTF-8 请求文件后正常。

## 3. 浏览器检查情况（如实说明）

本会话**无浏览器工具**，未执行真实浏览器闭环（提问→模拟生成→引用/原文→复制→历史恢复、失败转摘录）。已在 [demo-notes.md](./demo-notes.md) 提供 Astra 可运行的本地演示入口与逐步核验表；stub 与 mock 证据不冒充真实浏览器证据。

## 4. 未验证项

1. 真实浏览器交互（上表交 Astra 本地核验）。
2. 真实 DeepSeek 生成下的页面渲染：本任务未授权外部调用，未执行（T014 真实证据不重放）。
3. 全量 pytest / JS(search) 行为 / embedding / 评测：无后端与 search 页变更，按任务不重跑。
4. localStorage 容量极端情况（20 条上限与替换逻辑已实现并经 stub 验证，未做真实浏览器大容量测试）。
