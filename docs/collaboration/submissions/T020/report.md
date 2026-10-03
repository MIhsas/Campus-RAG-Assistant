# T020 本地语音输入与确认闭环 — 实施报告（submission_revision=2）

日期：2026-09-27。task_id=T020、task_revision=v1、submission_revision=2、responds_to=T020-R1、status=ready_for_review、**external_model_calls=0**、local_asr_verified=true（仅表示有真实主路径证据）。

> 修订记录：revision 2 为 T020-R1 定向返工（静音拦截、空转写 no_speech 状态、未配置提示、模型身份来源标识），详见 [fix-report.md](./fix-report.md)。revision 1 历史副本：`report.rev1.md` 等 4 件；真实转写证据 `asr-evidence.json/.md`、依赖模型记录 `dependencies-model.md` 原样保留。下文为任务整体说明（rev1 内容），语音输入的静音/空结果语义以 fix-report 为准。

## 概述

ask 页“短录音/上传音频 → 本地中文转写 → 编辑确认 → 用户明确填入问题框”闭环。Windows CPU 可用（FunASR 1.4.16 + Paraformer），本地离线推理：不接云端 ASR、不调用 DeepSeek、不上传音频、不自动提问。未录制任何用户或周围人的声音（测试音频为本地 TTS 合成并标注）。

## 依赖与模型（详见 dependencies-model.md）

- dry-run 核对安装 funasr **零覆盖既有包**（torch 2.14.0+cpu 未动）→ funasr 1.4.16 + kaldi-native-fbank（fbank 后端）+ av 18.1.0（WAV/WebM-Opus 解码）。**FunASR 首选路径兼容成功，未启用 faster-whisper 替代**。
- 模型：`iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`（ModelScope 公开快照）→ `.cache/asr-models/paraformer-zh`（10 文件 889MB，逐文件 SHA-256 见 PROVENANCE.json）。下载与运行分离；服务仅本地目录加载、不自动下载、未配置明确不可用。

## 功能交付

1. **ASR 适配与 API**：`asr/adapter.py`（FunASRParaformerAdapter 本地加载；model_id 带 PROVENANCE 摘要来源标识；MockASRAdapter 显式注入标注模拟）、`asr/audio.py`（PyAV 解码、5MB/30 秒硬限、**解码后推理前静音拦截**）、`api/asr.py`（/status、/transcribe：status ok/no_speech、文本+实际 provider/model+时长+耗时、置信度无则 null、线程池推理、单并发 409、清晰错误、零音频日志）。
2. **ask 页面闭环**：录音/上传→转写→独立编辑区→明确“使用此文本/替换问题输入”（空文本防护、不覆盖旧问题）；仅点击请求麦克风；权限拒绝保留上传/文字；取消/离开释放音轨；失败与 no_speech 均注明“原问题未被修改”；启动显示本地识别可用性（未配置禁用语音入口、文字入口保留）；转写与填入不自动提问；快照/历史语义不变。
3. **统一演示**：`demo-campus.py --asr-model-dir` 显式注入；问答生成仍为标记 mock，真实本地转写与 mock 问答分别标注。
4. **T019-R1 两处说明**（rev1 已做）：未知＝“您尚未确认该项”；依据被筛除演示用下拉可选 2022。

## 验证摘要（rev2 聚焦 + rev1 证据保留）

- **rev2**：`tests/test_asr.py` 13 passed（含数字静音不进模型、空/空白转写 no_speech）；JS 7 页 + ask 行为 25 场景（+3：no_speech 不出编辑器/空文本不抹问题/未配置提示）；**真实静音探针退出 0**（400 静音提示、无识别文字，`silence-probe.txt`）；**真实正常样本**输出与 rev1 证据一致（错字保留）。详见 [fix-report.md](./fix-report.md) 与 [verification.md](./verification.md)。
- **rev1 证据保留**：真实转写 asr-evidence（local_asr_verified 的来源）、依赖/模型来源记录、浏览器补验留待 Astra 的检查表（demo-notes.md）。

## 已知限制

- 浏览器语音闭环（权限/录音/上传/确认）留待 Astra 补验；stub 不冒充浏览器证据。
- 真实转写证据为一段合成 TTS 语音，不代表真人识别准确率；静音拦截为保守能量阈值，只解决静音/无有效语音，不解决模型全部幻觉。

完成后停止，等待 Astra 验收。T021 未发布。
