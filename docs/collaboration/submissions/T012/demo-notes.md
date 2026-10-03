# T012 演示记录

## 复现命令

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-ask.py --corpus examples\parse-corpus
```

原始输出：`ask-demo.json`（退出码 0）。本地语料 + BM25，未配置生成器，未调用任何外部或付费模型。

## 结果摘要

| 场景 | 结果 |
|---|---|
| ask/status | extractive 默认；`generator_configured=false`；`answer_modes_available=["extractive"]` |
| extractive 无筛选 | `evidence_only`、`answer=null`；E1—E5 编号摘录（TXT/DOCX 两文档 chunk），各带原文跨度与 `/preview#…` 跳转 |
| extractive 年级 2023 + 日期 2026-09-22 | 3 条证据全部来自 TXT 文档（DOCX 仅 2024 级，被条件排除）；`filter_summary.allowed_count=1`；预算装入 3 条 214 字符、0 略过 |
| extractive 年级 1900 | `evidence_state=no_admissible_docs` + “没有满足所选条件的资料”，`answer=null`，不凭空回答 |
| generated（未配置） | 503 `GENERATOR_NOT_CONFIGURED`，消息提示可改用原文摘录；摘录不伪装成生成答案 |

## 页面闭环（提问→摘录→出处→复制）

页面逻辑由 `scripts/check-ask-behavior.cjs`（DOM/fetch/clipboard stub）覆盖：提交快照、E-编号证据卡与“查看原文”、纯文本复制（含来源，失败有明确提示）、状态刷新不清筛选、失败重试沿用提交参数、三种空态、生成器未配置禁用“生成答案”、受控 generated 响应的段落+引用渲染（协议演示，非真实 LLM）。

**真实浏览器实测（提问→摘录→原文跳转→复制）本轮无浏览器能力，未执行，由 Astra 补验**；建议步骤：启动 `uvicorn campus_assistant.demo:app --port 8001` → http://127.0.0.1:8001/ask → 输入“缓考申请需要什么材料”→ 选年级 2023 与日期 → “整理依据”→ 核对“原文摘录 / 未生成答案”标签与条件快照 → 点 E1“查看原文”核对定位 → “复制问题与摘录”核对纯文本含来源 → “生成答案”应禁用并提示“自动作答未配置”。
