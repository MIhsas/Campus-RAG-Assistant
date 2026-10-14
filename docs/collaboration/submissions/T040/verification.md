# T040 验证记录（verification.md，submission_revision=4，responds_to=T040-B-恢复执行）

> 本轮=恢复执行单真实运行一次。命令真实执行、退出码实测。未重跑 mock/原 A 准备/实验（工单明确）；未改代码。历史验证分层见 `rev1/`、`rev2/`、`rev3/` 归档。执行环境：Windows 11；密钥按 2026-10-09 配置补充授权加载（仅 User 级一条变量、不打印值）。

## 1. 密钥就绪检查（仅存在性）

| 项 | 实测 |
|---|---|
| 实际执行进程 `DEEPSEEK_API_KEY` | False（既有进程未继承） |
| 按授权加载 User 级该一条变量后（同一 PowerShell 装入执行 Python 的进程，未打印值、未查其他位置/注册表/进程/.env） | **True** |

## 2. 真实运行（一次，T040-B-resume-1）

命令（cwd=`F:\Collage Paper\step2_code\backend`；密钥在同一 PowerShell 装入进程后执行，下为可复制形式）：

```powershell
$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable('DEEPSEEK_API_KEY', 'User')
.\.venv\Scripts\python.exe .\scripts\live-smoke-real-qa.py --live --out-dir '.\.cache\real-qa-smoke\T040-B-resume-1'
```

| 项 | 实测 |
|---|---|
| 前置门 | A 身份/E/messages 一致 ✓；实际 provider 配置=官方值（endpoint `https://api.deepseek.com/chat/completions`、deepseek-flash、max_tokens=1500、timeout=30s，取自实际只读属性）✓；key_present=true；输出目录新目录无已有输出 ✓；安全摘要先于请求输出 ✓ |
| 执行 | q08→q10→u03→u04 各尝试 1、发送 1；**external_http_attempts=4**、provider_calls=4、ask_calls=8（前置 extractive 4+generated 4）；`completed_all`，无技术失败/not_attempted |
| 供应商审计（已观察值） | 4 次 HTTP 200、finish_reason=stop×4；request_id×4、usage（prompt 1344/1379/1667/1690、completion 107/171/53/57）、latency 1359/1092/922/811ms、max_tokens=1500 |
| 退出码 | **0** |
| 输出 | `.cache/real-qa-smoke/T040-B-resume-1/{live-results.json, live-answers-full.json}`（完整 E/messages/审计/send_log/停止原因；未执行题=无；未知字段 null） |

## 3. 逐段核对（执行者辅助；详见 live-review-notes.md）

| 校验项 | 结果 |
|---|---|
| E 支持性（对照本次实发 E 全文） | q10 P1/P2 逐字支持、P3 基本支持（适度推断留人工）；u03 逐字支持；q08/u04 无答案段落，拒答理由与实发 E 相符（合理不足） |
| gold 目标覆盖（离线对照，不入 messages） | q10 f1/f2 覆盖、u03 f1 覆盖；**q08 f1 缺口保持**（2 源未发，不兜底）；u04 无 gold |
| 语义边界 | q10 两前提分开、未按年份宣布废止；u03 未从 db05e0 补信息；u04 未推测办理部门、83eb 未混入 |
| 用户语义确认状态 | 四题全部「未确认」（不代签；用户 109/3/2 与模板 33 项确认不变） |

## 4. 保全核验

| 项 | 结果 |
|---|---|
| revision 3 归档 | `rev3/` 9 件（替换前复制）；旧 live 三件保全于其中 |
| run-1 缓存 | `.cache/real-qa-smoke/T040-B/live-results.json` 未改（`34cbf5f9…`） |
| rev1/rev2、A 四件三处 | 保持（历史核验延续） |
| 新产物副本 | 提交目录 live-results `e607654b…`/live-answers-full `96416950…` == T040-B-resume-1 原件 |

## 5. 未验证/边界

- 真实答案质量/学校现行性**未认证**；live_verified=false 待 Astra 认定；4 题冒烟≠校园准确率/可靠拒答。
- 未测价格/费用；max_tokens≠费用上限；无余额/账户查询。
- 未改产品/语料/模板/gold/冻结/实验/用户记录/Astra 文件；无 commit/push、下载安装；自动权限审查未拒绝本轮动作（此前拒绝历史保留于 rev2/rev3 记录）。
