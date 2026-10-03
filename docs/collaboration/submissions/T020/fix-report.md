# T020-R1 定向返工报告（submission_revision=2）

日期：2026-09-27。responds_to=T020-R1。task_revision 保持 v1、status=ready_for_review、**external_model_calls=0**、local_asr_verified=true（仅表示 rev1/rev2 有真实主路径证据）。仅修静音/空转写处理与两处说明；未重下模型、未扩大测试矩阵、未按幻觉字符串做过滤。

## P1-1 修复：解码后、推理前拦截静音

**根因**：`audio.py` 只查格式/时长；数字静音进入模型产生幻觉文字（探针两次输出不同——“没我没有”/“没知嗯”，故不能按字符串过滤）。

**修复**：`decode_audio` 在解码完成后、返回给适配器推理前增加保守静音检查——`peak < SILENCE_PEAK_THRESHOLD (1e-3 ≈ -60 dBFS)` 判为静音/几乎无声 → `AudioError("音频为静音，未识别到有效语音，请重录或重新选择音频")`。阈值保守、可解释：只拦截明显静音（含全零 PCM），不要求噪声分类、不宣称解决全部幻觉。该门是解码共享出口，MockASRAdapter 同样把解码/静音检查放在任何识别动作与计数之前——**静音不进入模型路径**。

## P1-2 修复：空/空白转写结果明确“未识别到有效语音”

**修复**（API 与页面约定一致）：

- API：转写文本空/仅空白 → 200 `{"status":"no_speech","text":"","message":"未识别到有效语音，请重录或重新选择音频"}`（成功为 `status:"ok"`）。
- 页面：`no_speech`/空文本 → 显示“未识别到有效语音，请重录或重新选择音频（原问题未被修改）”，**不显示成功编辑器**；“使用此文本/替换问题输入”增加空文本防护——识别文本为空时提示“识别文本为空，未修改问题输入”，**不覆盖已有问题**。

## 最小因果链回归 + 真实模型各一次

- `tests/test_asr.py` +3（合计 13 passed）：`test_digital_silence_rejected_before_model`（静音 → AudioError 且 `adapter.calls == 0`，未进识别逻辑）、`test_silent_audio_rejected_400`、`test_empty_transcription_is_no_speech`（空/空白/制表符三种）。
- `check-ask-behavior.cjs` +3（合计 25 场景）：no_speech 不出编辑器且问题不变；编辑区清空后“替换问题输入”不抹掉旧问题并提示；未配置状态提示 + 语音入口禁用 + 文字入口保留。既有“正常 TTS 转写→编辑→手动填入、不自动提问”场景保持通过。
- **真实静音探针**（Astra 的 T020-R1-probe.py，对本地服务）：`{"status": 400, "code": "AUDIO_INVALID", "message": "音频为静音，未识别到有效语音…"}`，无识别文字，**探针退出 0**（修复前 exit 1）。原始记录 `silence-probe.txt`。
- **真实正常样本**（修复后各一次）：tts-sample.wav → 原始识别“缓考申请需经所在学院批准并报教务处备案”（与 rev1 证据一致，错字保留），344ms——主路径未回归。rev1 的 `asr-evidence.json/.md` 原样保留。

## 非阻断说明（随修复一起）

1. **未配置提示**：ask 页启动读取 `/api/v1/asr/status`——可用时显示“本地识别可用（provider / model）”，未配置时提示“录音/转写不可用，可继续使用文字提问”并禁用语音入口（文字入口保留）。
2. **模型身份**：model_id 注释与实现对齐并真正带入来源标识——`paraformer-zh@provenance-<PROVENANCE.json 摘要 12 位>`（逐文件哈希清单摘要，可核验）；无清单时 `（来源未核实）` 标注。实测输出 `paraformer-zh@provenance-8b449f3ba655`。

## 验证范围（按返工单）

仅运行 `tests/test_asr.py`（13）、JS 语法（7 页）、ask 行为（25 场景）+ 真实静音探针与正常样本各一次；未重跑 selfcheck/embedding/全量。调试记录：页面桩补 asr/status 路由与 asrStatus 默认（既有语音场景兼容）。

## 历史与文件

- revision 1 历史：`report.rev1.md`、`verification.rev1.md`、`submission.rev1.json`、`changed-files.rev1.json`；真实证据 `asr-evidence.json/.md`、`dependencies-model.md` 原样保留。
- 本修订修改：`asr/audio.py`、`asr/adapter.py`、`api/asr.py`、`static/ask.html`、`tests/test_asr.py`、`scripts/check-ask-behavior.cjs`；新增 `silence-probe.txt`。清单见 `changed-files.json`。

完成后停止，等待 Astra 验收。T021 未发布。
