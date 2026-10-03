# T017 验证记录（submission_revision=2，responds_to=T017-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。按返工单只运行 `test_comparison.py`、Astra 独立探针及必要检查；未重复 42 项其他回归（未改工厂/旧页面）、未扩大测试矩阵；external_model_calls=0。revision 1 记录见 `verification.rev1.md`。

## 1. Astra 独立探针（修复证据核心）

```bash
./.venv/Scripts/python.exe ../../docs/collaboration/reviews/T017-R1-probe.py
# forward: {'added': 1, 'deleted': 0, 'modified': 1, 'unchanged': 0}
# backward: {'added': 0, 'deleted': 1, 'modified': 1, 'unchanged': 0}
# 退出码：0
```

与探针期望断言一致（修复前为 exit 1、forward 新增2/删除1/修改0）。正向：右侧“新公告”记新增、左“申请材料…”与右“…并签字。”配为修改；反向对称为删除+修改。

## 2. 相关 pytest（14 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_comparison.py -q -p no:cacheprovider --basetemp .cache/t017r2-iter1 --tb=short -rs
# 14 passed, 2 warnings in 0.55s
# 退出码：0
```

- 原 10 项全部保持通过（四类分类、插入不致错位、交换对称、跨度一致、跨组/同文档拒绝、路由）。
- 新增 4 项 `TestT017R1Lookahead`：
  - `test_forward_add_plus_modify`：counts {added:1, deleted:0, modified:1, unchanged:0}；修改项 left=“申请材料须交所在学院审核。”、right=“申请材料须交所在学院审核，并签字。”（**配到正确原文**）；新增项为“新公告”句；全部条目跨度 `char_start=0、char_end=len(text)`（与解析块逐字一致）。
  - `test_backward_delete_plus_modify`：counts {added:0, deleted:1, modified:1, unchanged:0}；同两句配对方向对调；删除项为“新公告”句。
  - `test_unrelated_blocks_not_force_paired`：不相关段落 → 修改 0、新增 1、删除 1（门槛保持，不强行配对）。
  - `test_paragraph_only_limitation_documented`：说明含“表格”与“直接归入新增/删除”（与实现一致）。

## 3. 本地 API 演示重生成

```bash
./.venv/Scripts/python.exe scripts/demo-comparison-api.py --out-dir "F:/Collage Paper/docs/collaboration/submissions/T017"
# calls_recorded: 5；counts: {added:1, deleted:1, modified:1, unchanged:3}
# 退出码：0
```

夹具分类计数不变；响应 `algorithm.limitations` 已含“不含表格差异”与重复条号准确表述；`comparison-expectations.md` 手工对照保持全一致。

## 4. 未验证项（如实标注）

1. 浏览器复制实测：留待 Astra 复验（T017-R1 记录未取得非空剪贴板内容；本轮不伪称已验证）。
2. 页面行为脚本：compare.html 未修改（说明由响应动态呈现），按返工单未重复运行其 5 场景（rev1 已过）。
3. 工厂/旧页面回归（42 项与 search/ask/procedures 行为）：未改相关代码，按返工单未重复。
4. 表格比较：按返工单不实现，边界已声明。
