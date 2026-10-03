# T019 有限事项条件自查 — 实施报告

身份：task_id=T019、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**（零外部模型调用，无 eval、无规则引擎）。

## 概述

交付“转专业条件自查（合成演示）”：用户以四项三态自报 → 确定性判断 → 逐项满足/不满足/待核实 + 原文引用与原文跳转。**个人自查演示：不代表学校审核结果、不受理申请、不构成录取/批准/申请成功**；不收集姓名、学号、违纪详情；填报仅本次请求内处理，不写报告/日志/localStorage。

## 功能交付（对照任务书）

1. **规则配置** `examples/self-check/rule.json`（rule_id=rule-transfer-major、rule_version=1.0、is_synthetic=true）：显式绑定 parse-corpus 第五条四句（document_id/block_id/精确跨度/quote/文档 sha256，跨度经解析块切片逐条核对）；由工厂参数 `self_check_path` **显式注入**（demo-campus 统一演示注入），普通未配置服务返回 503，不自动启用合成规则。原语料/manifest/gold 未改。
2. **四项规则与原文一致**：入学后第一学年末提出申请 / 在读无违纪记录 / 第一学年加权平均成绩排名前 30% / 通过接收学院考核。全部三态（是/否/不确定或未填写）；排名按自报“是否前 30%”**不做并列/取整换算**；未参加考核记为待核实，与明确未通过（否）区分；不收姓名/学号/违纪详情。
3. **确定性判断**（`selfcheck/service.py`，无 eval/LLM）：未知不计满足；任一“否”→“存在未满足项”；有未知无“否”→“仍有待核实项”；全“是”→“按自填信息满足本演示列出的条件（仍需学校审核）”。依据未过筛选准入/缺失/哈希变化 →“依据不足，无法完成自查”，失效引用不携带原文、不参与通过计算。每项返回已填值、状态、解释与有效引用。
4. **API**（`api/selfcheck.py`，路径选择已在上方说明）：GET `/api/v1/self-check/rule`、POST `/api/v1/self-check`（filters 复用四项；answers 严格三态，非法值 422）；引用链接由服务器绑定（复用 procedures 的引用核查与 T011 准入，**未复制第二套准入逻辑**）；未配置明确 503。
5. **页面 `/self-check`**：首页第六入口（home.html 卡片）；筛选 → 三态表单 → 手动自查 → 快照行（已提交输入+条件）→ 逐项结果（状态标签/解释/原文引用+查看原文）→ 修改重查/清空表单。改表单不改写旧结果；失败明示“未生成新结果”；“依据不足”与“个人不满足”分色分词表达；仅点击后执行，不自动调用模型或保存。统一演示 demo-campus.py 显式注入规则并记录自查接口（12 路由全通）。
6. **演示说明**（README + demo-notes）：Windows 启动命令与四场景（全满足/缺考核信息/一个不满足/依据被筛除），全部标注合成资料、确定性规则，不宣传真实校园资格准确率。

## 验证摘要（聚焦，真实命令见 verification.md）

- `tests/test_self_check.py` **11 passed**：四态组合（全满足/未知/不满足+未知并存/缺失答案=未知）、未知不计满足、依据被筛除与哈希变化→依据不足（失效引用 quote=null）、跨度=原文切片、服务器绑定预览链接、路由 503/422。
- **受影响聚焦回归**：`test_procedures.py` 14 + `test_demo_campus.py` 5 全过（共享核查被复用、工厂加参）。
- JS：7 页语法 + `check-self-check-behavior.cjs` **6 场景**（表单渲染/快照绑定/全满足措辞/改表单不改旧结果+重查替换/失败“未生成新结果”/依据不足≠个人不满足/清空保留结果）。
- 本地 API 示例 `selfcheck-api-demo.json` 四场景判定与设计一致（all_satisfied / has_unknown / has_unsatisfied / insufficient_basis）+ `rule-text-crosscheck.md` 规则原文对照。
- 未重跑 embedding、全量旧测试或无关矩阵。

## 修改与新增文件

- 新增：`examples/self-check/rule.json`、`selfcheck/`（2）、`api/selfcheck.py`、`static/self-check.html`、`tests/test_self_check.py`、`scripts/check-self-check-behavior.cjs`、`scripts/demo-selfcheck-api.py`
- 修改：`main.py`（工厂参数+路由/页面）、`scripts/demo-campus.py`（显式注入+记录）、`static/home.html`（第六入口）、`README.md`
- 清单见 `changed-files.json`；未修改：Astra 文档、旧语料/gold、已验收算法、既有页面行为。

## 已知限制

- **无浏览器工具**：页面闭环未由真实浏览器执行；[demo-notes.md](./demo-notes.md) 提供 Astra 可运行入口与逐步检查表（a—f）；stub 不冒充浏览器证据。
- 合成规则仅覆盖第五条四项；不代表真实校园资格准确率或学校审核结论。
- ask 页“转专业”相关自查入口为任务可选项，本轮未实现（验收不作要求）。

完成后停止，等待 Astra 验收。T020 未发布。
