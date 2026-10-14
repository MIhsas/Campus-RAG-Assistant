# T040 验证记录（verification.md，submission_revision=3，responds_to=T040-R2）

> 本轮范围=T040-R2 两处因果链修复的定向验证：两条业务链回归 + 原 4 项 mock + 原样运行 Astra 探针。命令真实执行、退出码实测。**全部为注入式本地 mock/探针证据（零真实网络），不是模型质量证据。** 未跑全量/UI/向量/三模式/A 原准备；未发真实请求。执行环境：Windows 11 / Git Bash；解释器 `F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe`。A/revision 2 历史验证见 `rev1/verification.md`、`rev2/verification.md`（归档原字节）。

## 1. 测试（4 原项 + 2 新业务链）

命令（cwd=`F:\Collage Paper\step2_code\backend`）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' -m pytest tests/test_live_smoke_real_qa.py -q
```

| 轮次 | 结果 | 退出码 |
|---|---|---|
| 首跑 | 5 passed / 1 failed：新链 2 断言笔误（`fake.calls == 0` 列表比整数） | 1 |
| 修正断言后 | **6 passed** | **0** |

| 用例 | 链 | 实测断言 |
|---|---|---|
| test_output_gate_refuses_before_any_send | **必修1 业务链** | 非空输出+可用 mock：run_b 抛 RuntimeError（调用前拒绝）、fake.calls=[]/posts=0、旧文件不变、未写新审计 |
| test_presend_failure_zero_post_zero_count | **必修2 业务链** | build_messages 发送前异常：fake.calls=[]、external_http_attempts=0、provider_calls=1（另列）、失败即停（q10 not_attempted） |
| test_attempt_counting_and_fail_stop | 原①（保持） | HTTP 失败计 1 即停；连接失败计 1、供应商状态 null；后续题 not_attempted |
| test_business_insufficient_continues_and_answers_recorded | 原②（保持） | 业务不足可继续；answered 记录完整（paragraph→E/citations/generation_meta/双状态） |
| test_preflight_rejects_without_requests | 原③（保持） | 前置失败零请求；非官方 endpoint 官方门拒绝 |
| test_zero_evidence_short_circuit_costs_no_attempt | 原④（保持） | 零证据本地短路、外部计数 0 |

## 2. 原 Astra 探针（原样运行，不改探针/断言/通过标准）

命令（cwd=`F:\Collage Paper`；复跑前旧失败记录已保全 `rev2/T040-B-preflight-probe-failed-preserved.json`，SHA `94e3944f…` 与当时原件一致）：

```powershell
& 'F:\Collage Paper\step2_code\backend\.venv\Scripts\python.exe' 'F:\Collage Paper\docs\collaboration\reviews\T040-B-preflight-probe.py'
```

| 检查 | 修复前（rev2 记录） | 本轮实测 |
|---|---|---|
| nonempty_output_before_send | post=4 后才拒覆盖，pass=false | **mock_post_calls=0**、error 非空、old_file_unchanged=true、new_audit_written=false，**pass** |
| counter_matches_actual_send | post=0 而 reported=1，pass=false | **post=0 == reported=0**，first_outcome=technical_failure，**pass** |
| 总判 | pass=false（exit 1） | **pass=true，退出码 0** |

## 3. 保全字节核验（revision 2 与 run-1）

| 项 | 结果 |
|---|---|
| rev2 归档 8 件 | live-results `34cbf5f9…` 等与归档前原件逐一同哈希 |
| run-1 原件 | `.cache/real-qa-smoke/T040-B/live-results.json` 全程未改（SHA `34cbf5f9…` == 提交副本） |
| rev1/ 与 A 缓存、A 四件材料 | 未覆盖（A 四件三处同哈希延续 revision 2 核验） |

## 4. 记录层级与勘误

- **run-1 勘误**：其机器记录 `questions={}`、`stop=null`——“四题均未执行、未列条目”，**不是**四条 not_attempted。revision 2 报告“not_attempted×4”与 live-answers-full.json 逐题行属事后人读描述，以本勘误为准；原机读文件不改。代码已修：此后前置/守卫拒绝记录补齐四题 not_attempted 与停止原因。
- **缺密钥**：仅陈述“本次执行进程环境及列明位置检查未发现可用配置”（进程含非沙箱、User/Machine 级查询、仓库 .env）；不作全位置绝对断言；另一终端环境不自动共享。未读取/打印密钥值、全量环境、headers、原始异常。
- **权限分类器拒绝历史**（revision 2 记录刷新被拒）保留；本轮未触发。此后若再被拒绝：记录具体动作/原因并停止该动作，不换途径规避。
- mock/探针 ≠ 模型质量；真实生成、四题支持性、现行性均未验证；live_verified=false 待 Astra 认定。
