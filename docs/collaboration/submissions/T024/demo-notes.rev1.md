# T024 演示记录与步骤（DeepSeek 结构化规划适配与离线联调）

## 证据层级（先读）

| 层级 | 内容 | 性质 |
|---|---|---|
| 适配器联调测试 | `tests/test_deepseek_planner.py` 19 项 | **真实适配器 × 本地 loopback mock**（模拟输出，trust_env=False） |
| 必要回归 | agent 20 + run_entry + deepseek_provider + planner = 60 项 | 真实本地运行 |
| Mock 调用轨迹 | `mock-planner-trace.json`（7 runs） | 适配器×loopback mock 6 + 脚本规划器对照 1，零外部调用 |
| 页面行为 | `check-workflow-behavior.cjs` 4 场景 + JS 语法 9 页 | **vm stub 层级，非真实浏览器** |

**全部 mock/loopback 输出标注「模拟，非真实 DeepSeek」；mock 不进入正常启动默认路径。** 测试不可能访问 api.deepseek.com。本轮零外部模型调用。

## 三种规划模式（勿混用）

| 模式 | 来源 | 页面表现 |
|---|---|---|
| off（默认） | 正常入口未开 `--planner` | 仅「运行固定流程」；提示「Agent 模式未开启」 |
| simulated | 仅 demo-campus 显式注入 | 「运行模拟规划（演示）」+「模拟规划，非DeepSeek实时规划」 |
| deepseek | `serve-corpus.py --planner deepseek`（+ CAMPUS_PLANNER/DEEPSEEK_API_KEY） | 「运行 DeepSeek 规划（显式点击）」+「已配置 ≠ 已联调验证（planner_live_verified=false）」 |

固定流程恒为「固定流程（选事项→查找依据→整理草稿），非大模型 Agent」。demo-campus **始终**模拟规划，不因环境配置切真实服务。

## 本地 loopback mock 联调（复现命令）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_deepseek_planner.py -q   # 19 passed
./.venv/Scripts/python.exe scripts/trace-agent-planner.py               # 生成 mock-planner-trace.json
```

关键事实（可核对）：全链 mock 脚本 [search→draft→finish]；**第 2 次 HTTP 请求的 user 消息含第 1 轮真实观察**（`hit_count`、来源标识 `syn-parse-txt`）；草稿引用与直接 `build_draft` 全等；两次同 app 运行互不串扰；放宽条件/换事项在业务前被拒且 finish 报 partial；HTTP 500/非法 JSON 零重试、可解释失败、保留已完成结果。

## Astra 浏览器检查表（stub 不冒充，以下待真实浏览器复验）

| # | 操作 | 预期 |
|---|---|---|
| a 正常模式 | `serve-corpus.py … --procedures …`（无 --planner）→ `/workflow` | 仅固定流程按钮；「Agent 模式未开启」 |
| b DeepSeek 模式 | + `--planner deepseek`（配好 CAMPUS_PLANNER/DEEPSEEK_API_KEY）重启 | 出现「运行 DeepSeek 规划（显式点击）」；提示含 planner_live_verified=false；**不点击时 Network 零规划请求** |
| c 显式点击 | 点击 DeepSeek 规划按钮 | 发出规划请求；步骤区显示规划动作/工具事件/「规划 HTTP 尝试：N（无自动重试）」；不显示模型 Thought |
| d partial 呈现 | 断网或指向不可达 base_url 后点击 | 失败文案安全（无密钥）；已完成结果保留并标注；状态非 completed |
| e 模拟模式 | `demo-campus.py` → `/workflow` | 「运行模拟规划（演示）」+ 模拟标注；不出现 DeepSeek 按钮 |
| f 边界保持 | 任意模式 | 快照行/严格年份/失败清空旧结果/办理页手动保存（不写 localStorage）不变 |

## 边界（诚实口径）

- **planner_live_verified=false**：适配器联调证据全部来自本地 mock；真实 DeepSeek 冒烟仅计划（live-smoke-plan.md），未获调用授权、未运行。
- 规划器只决策动作，不生成政策答案；规划/工具观察中不输出、不保存模型 Thought。
- 工具仍仅 search_policy/build_checklist_draft；无保存/删除待办、Shell、文件、任意 URL、学校登录。
- 密钥仅本地环境变量，不进报告/日志/轨迹（验证含不泄密断言）。
- TinyAgent 维持 reference，未引其代码或依赖。
