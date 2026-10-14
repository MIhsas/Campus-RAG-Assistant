# T042 验证记录（verification.md）

> 范围=复核包构建与页面业务链（主链验证）；**未跑产品套件/实验/模型/旧 114 项测试**。零外部调用、不读密钥/环境。分层：**本轮实测**（构建/测试/桩检查）｜**历史引用**（T039/T040/T041 既有记录）｜**未验证**（§4）。

## 1. 本轮实测

### 1.1 构建（真实输入，只读核验）

命令（cwd=`F:\Collage Paper`，PowerShell 可复制形式见输出 README.md）：

```text
python scripts/build-targeted-review-pack.py --manifest <v1.2> --corpus-root <v1.2> --questions <v2.0> --supplement <T039 review-supplement> --live-answers <T040 live-answers-full> --casebook <T041 casebook> --user-record <T036 记录> --out-dir .cache/human-review/T042-v1
```

| 项 | 实测 |
|---|---|
| 引用核对 | **40 条**（17 gold 证据 + 3 未核实候选 + 20 T040 实发 E）逐条：文档 SHA、块存在、跨度合法、quote==块切片逐字——全过 |
| 卡片 | 8 张（revision:q08/q10/u03/u04 + answer:q08/q10/u03/u04），分域 ID 不冲突；supplement 的 query/conditions 与冻结题集一致；T040 记录 query/conditions 与冻结一致 |
| 新意见 | 8 项初值全「未复核」；每卡仅 1 条顶层意见行 |
| 防覆盖 | 复跑同命令 →「输出目录非空，拒绝覆盖」，exit 1（预期） |
| 退出码 | 首次构建 **0**（stderr 3 条 PDF 解析警告原样，非失败） |

### 1.2 构建聚焦测试

```text
python -m pytest tests/test_targeted_review_pack.py -q   （cwd=backend）
# 6 passed，退出码 0
```

覆盖：8 卡分域 ID 集合/顺序；q10 三段与 P3 逐字==T040 原文且 P3 推断在关键点；q08 gold 与实发 E 互不包含；u04 候选标注「未核实范围/非本次模型依据」且 83eb 不在实发 E；全未复核+输入身份；构建前后源输入 SHA 一致（**不改源输入**）；非空拒覆盖。

### 1.3 JS 行为检查（DOM/桩级，非真实浏览器）

```text
node scripts/check-targeted-review-pack.cjs --write-sample .cache/human-review/T042-v1-simulated-export.json
# 24 checks passed，退出码 0
```

覆盖：8 卡渲染与 ID 顺序；默认导出=8 项全未复核、reviewer/review_date/标题空（**不预填**）；**独立模拟仅 `answer:q10` 需修订+P3 说明→导出**：`revision:q10` 与其余 6 项仍未复核（分域生效）、tally 1/7、输入 SHA 不变、导出时间有而 review_date 空；NodeList 真实形态（无 some/map）、select 原生语义；localStorage/fetch 桩禁用且预扫描无外链资源/存储 API 使用。模拟样例 `simulated-export-sample.json`（record_title=「模拟操作测试」，**非真人意见**）独立存放、不在默认包内。

### 1.4 保全与只读核对

- 源输入（v1.2 manifest/语料、v2.0 题集、review-supplement、live-answers-full、casebook、用户记录）构建前后 SHA 一致（测试断言）。
- 旧 T036 脚本/HTML/包、产品 API/前台、gold/冻结/指标/模板/历史输出未改（本轮零写入这些路径）。
- human-review-pending.md 仅追加「待验收的新补充工具」位置预告，未改意见/入口/历史状态。

## 2. 历史引用（未重跑）

- T039 review-supplement 四项修订与 T040 两件真实结果/核对记录——沿用既有材料（本包只读取并展示）。
- T041 casebook、用户 109/3/2 与模板 33 项确认——既有记录，只读展示/引用。

## 3. 浏览器

本执行窗口**无真实浏览器工具**：未做真实浏览器实操，不冒充。[demo-notes.md](./demo-notes.md) 提供用户/Astra 的 7 步短检查表（打开→展开 q10→改 1 项→导出→刷新丢失提示）。

## 4. 未验证（不代填）

- 8 项语义正确性/政策现行有效性/用户填写结果——**未验证**（工具≠复核完成）。
- 真实浏览器渲染/下载行为——待用户按 demo-notes 人工走查。
- 不写 accepted；T040 live_verified 历史限定与 planner_live_verified=false 不变。
