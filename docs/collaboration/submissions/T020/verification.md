# T020 验证记录（submission_revision=2，responds_to=T020-R1）

工作目录 `F:\Collage Paper\step2_code\backend`。按返工单仅运行 ASR 相关测试、JS 语法与 ask 行为；未重跑 selfcheck/embedding/全量；未重下模型；external_model_calls=0。revision 1 记录见 `verification.rev1.md`（含依赖安装、真实转写证据等）。

## 1. 相关 pytest（13 项）

```bash
./.venv/Scripts/python.exe -m pytest tests/test_asr.py -q -p no:cacheprovider --basetemp .cache/t020r2-iter1 --tb=short -rs
# 13 passed, 2 warnings in 1.53s
# 退出码：0
```

- 新增 3 项因果链：`test_digital_silence_rejected_before_model`（全零 PCM → AudioError“静音”，**adapter.calls == 0 未进识别逻辑**）、`test_silent_audio_rejected_400`（API 明确“未识别到有效语音”）、`test_empty_transcription_is_no_speech`（空/空白/制表符三种 → 200 status=no_speech、text 空、message 明确）。
- 原 10 项保持通过（解码/限额/503/标记 mock/502/409/env 门控）。

## 2. JS 语法与 ask 行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 7 HTML files passed syntax check.（退出码 0）
"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 25 scenarios passed（退出码 0）
```

- 新增 3 场景：no_speech → “未识别到有效语音”提示、**无成功编辑器**、问题不变；编辑区清空后“替换问题输入”不抹掉旧问题并提示“识别文本为空，未修改问题输入”；未配置 → 提示“本地语音识别未配置；录音/转写不可用，可继续使用文字提问”、语音入口禁用、文字入口保留。
- 既有 22 场景保持通过（含“正常 TTS→编辑→手动填入、不自动提问”“失败保原问题”“取消释放音轨”等）。
- 调试记录：页面桩补 `/asr/status` GET 路由与 asrStatus 默认值，既有语音场景兼容。

## 3. 真实模型各一次（本地服务 + 本地推理）

**静音探针（Astra 的 T020-R1-probe.py）**：

```bash
./.venv/Scripts/python.exe scripts/demo-campus.py --port 8031 --asr-model-dir .cache/asr-models/paraformer-zh &   # 本会话启动并停止
./.venv/Scripts/python.exe ../../docs/collaboration/reviews/T020-R1-probe.py --port 8031
# {"status": 400, "body": {"code": "AUDIO_INVALID", "message": "音频为静音，未识别到有效语音，请重录或重新选择音频", ...}}
# 退出码：0（断言通过：无识别文字；修复前为 exit 1）
```

原始记录：`silence-probe.txt`（本次输出存档）。

**正常样本（修复后）**：

```bash
./.venv/Scripts/python.exe scripts/demo-asr-transcribe.py --model-dir .cache/asr-models/paraformer-zh --audio .cache/t020-audio/tts-sample.wav ...
# raw: 缓考申请需经所在学院批准并报教务处备案（与 rev1 一致，错字保留）
# model: paraformer-zh@provenance-8b449f3ba655 | elapsed_ms: 344
# 退出码：0
```

主路径未回归；rev1 的 `asr-evidence.json/.md` 原样保留为历史真实证据。

## 4. 未验证项

1. 真实浏览器语音闭环（留待 Astra，rev1 demo-notes 检查表适用）。
2. 噪声/口音/边界矩阵：按返工单不扩展。
3. 真人语音识别准确率：不作此宣称（合成 TTS 证据）。
