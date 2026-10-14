# T043 演示与短检查表（demo-notes.md）

> **证据层级声明**：本执行窗口**无真实浏览器工具**——页面改动（search.html/ask.html 新开关与快照/历史/跨页/复制携带）证据仅为**源码结构检查**（pytest `test_pages_wire_switch_and_snapshot`）与既有页面桩；**不冒充浏览器实测**。下表供 Astra/用户真实浏览器人工走查（预计 3 分钟）。

## 用户/Astra 短检查表（真实浏览器，本地服务）

启动（strict 与参考准入同一命令；模式由页面开关控制）：

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\serve-corpus.py --manifest 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2\manifest.json' --corpus-root 'F:\Collage Paper\data\corpora\sicau-rag-pilot-v1.2' --port 8010
```

| # | 操作 | 预期 |
|---|---|---|
| 1 | /search 选学生类型=本科，问题「学籍基本信息有误需要更正时，学生本人去哪里办理？」，开关保持默认开 | 结果含 83eb（新生学籍指南）命中，卡片带「学生类型未标注，适用范围尚未核实」提示；顶部「准入模式（快照）：参考准入」 |
| 2 | 关闭「纳入学生类型未标注资料（参考）」再搜 | 83eb 消失（严格准入）；模式行显示「严格准入」；「查看未核实资料」候选仍可单独查到 83eb |
| 3 | 开关开→整理依据（/ask）→查看 83eb E 卡 | E 卡带未核实提示；复制纯文本含该提示与准入模式行 |
| 4 | 改控件（如换校区）后点「重试」 | 重试按**提交快照**（含当时开关）执行，不吃当前控件 |
| 5 | 生成失败后「查看本次问题的原文依据」 | 转摘录沿用快照（含开关），不丢条件 |
| 6 | 开启历史→提问→刷新→查看历史 | 历史条目带「参考准入/严格准入（当时）」标签；旧历史记录显示「严格准入（当时）」；恢复只读渲染不发请求 |
| 7 | /search↔/ask 互跳 | URL 携带 `include_unknown_type`，对页开关与快照一致 |

## 本窗口已做（零外部调用）

- 聚焦测试 7 项通过（真实包 u04 新模式入 83eb 含明示地点/严格排除/候选按模式去重/ask 状态透传；合成夹具已知冲突与其它维度约束、三模式共用准入集合、document_id 求交；消息状态传递+mock 引用串通；页面结构检查）。
- 回归：相关旧套件 137 项通过（filters 默认 strict、办事/自查严格保持）。
- API 演示（api-demo.md/json）：本地 TestClient 实测六条调用+消息构造。
- 零模型 HTTP、不读密钥；旧 T040 授权已结束，本轮未执行 live。

## 边界

- 新准入≠适用性已确认/资格判定；mock≠模型质量；本轮无模型调用授权。
- 模式新基线未评测（后续单独安排，不编造指标）。
