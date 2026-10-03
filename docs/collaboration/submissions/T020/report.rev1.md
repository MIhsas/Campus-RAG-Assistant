# T020 本地语音输入与确认闭环 — 实施报告

身份：task_id=T020、task_revision=v1、submission_revision=1、status=ready_for_review、**external_model_calls=0**、**local_asr_verified=true**（真实本地转写成功，证据见 asr-evidence.md；模型下载为文件获取，单独记录于 dependencies-model.md）。

## 概述

ask 页“短录音/上传音频 → 本地中文转写 → 编辑确认 → 用户明确填入问题框”闭环。Windows CPU 可用（FunASR 1.4.16 + Paraformer），本地离线推理：不接云端 ASR、不调用 DeepSeek、不上传音频、不自动提问。未录制任何用户或周围人的声音（测试音频为本地 TTS 合成并标注）。

## 依赖与模型（详见 dependencies-model.md）

- 先 dry-run 核对：安装 funasr **零覆盖既有包**（torch 2.14.0+cpu 未动）→ 实装 funasr 1.4.16。首次推理按其明确报错补 `kaldi-native-fbank`（选不耦合 torch 版本的后端，未装 torchaudio）；解码装 `av` 18.1.0（WAV + 浏览器 WebM/Opus → 16k 单声道）。
- 集成修正两处实现细节：Windows 上被进程持有的临时文件 libsndfile 打不开（改为写后关闭、用后即删）；`Path.name` 误传文件名（传完整路径）。**FunASR 路径兼容可用，未启用 faster-whisper 替代**（无第二套实现、无反复遍历模型）。
- 模型：`iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`（ModelScope 公开快照）经 `scripts/download-asr-model.py` 载入 `.cache/asr-models/paraformer-zh`（10 文件 889MB，逐文件 SHA-256 见目录 PROVENANCE.json）。下载与运行分离：服务仅从本地目录加载，**未配置明确不可用、不自动下载**；下载时系统代理 TLS 劫持 modelscope.cn（T014 同款），以进程级 `NO_PROXY` 直连解决（未改系统代理）。

## 功能交付

1. **ASR 适配与 API**：`asr/adapter.py`（FunASRParaformerAdapter 仅本地目录加载；MockASRAdapter 显式注入且标注模拟）、`asr/audio.py`（PyAV 解码、5MB/30 秒服务端硬限）、`api/asr.py`（GET /status、POST /transcribe：文本+实际 provider/model+时长+耗时；置信度无则 null 不伪造；线程池推理不阻塞事件循环；单并发繁忙 409；损坏/空/超限/执行错误清晰中文提示；音频仅请求内处理、结束失败均清理、不保留音频或转写日志）。
2. **ask 页面闭环**：录音开始/停止/取消（最长 30 秒自动停）+ 上传音频；仅点击才请求麦克风，权限拒绝/无设备/非安全上下文提示并保留上传与文字入口；停止后显式“转写音频”；取消与离开（pagehide）释放音轨；**识别文本独立编辑区**，按钮“使用此文本/替换问题输入”（问题框已有文字时按钮显式标注替换）才写入；转写与填入均**不自动** /ask、生成或保存；失败提示均注明“原问题未被修改”；既有 query/mode/filters 快照与历史语义不变。
3. **统一演示**：`demo-campus.py --asr-model-dir` 显式注入真实本地识别；问答生成仍为标记 mock（页面/记录分别标注“真实本地转写”与“模拟生成”）；mock ASR 仅测试注入，不进默认路径。
4. **T019-R1 两处说明**：未知项解释改为“您尚未确认该项，请核实个人情况（未知不计为满足）”（不再误用“资料未说明”）；自查“依据被筛除”演示改用下拉可选的 **2022**（README 与 T019 demo-notes 同步）。

## 验证摘要（相关聚焦，真实命令见 verification.md）

- **真实本地转写证据**（local_asr_verified=true）：合成 TTS 音频（Huihui zh-CN，标注非真人、sha256 记录）5.72s → 原始识别“缓考申请需经所在学院批准并报教务处备案”（参考“…须经…，并报教务处备案。”；**须→需、标点丢失等实际差异保留未改**）；funasr-paraformer@paraformer-zh，转写 375ms，置信度 null。
- `tests/test_asr.py` **10 passed**（解码/5MB/30 秒/损坏/空、503 未配置、标记 mock 字段、502 执行错误、409 单并发、env 门控）+ 受影响回归 `test_self_check.py` 11 项全过（T019 说明改动）。
- JS：7 页语法 + ask 行为 **22 场景**（+5 语音闭环：转写→编辑→明确填入且零自动 ask、失败保原问题、替换标注、权限拒绝保留上传、取消释放音轨）。
- 统一演示 12 路由含 ASR 目录注入复核全通。

## 修改与新增文件

- 新增：`asr/`（3）、`api/asr.py`、`tests/test_asr.py`、`scripts/download-asr-model.py`、`scripts/demo-asr-transcribe.py`
- 修改：`main.py`（工厂/路由/env）、`static/ask.html`（语音闭环）、`scripts/check-ask-behavior.cjs`、`scripts/demo-campus.py`（--asr-model-dir）、`selfcheck/service.py`（T019 说明）、`README.md`、`../docs/collaboration/submissions/T019/demo-notes.md`（T019 说明）
- 依赖：funasr 1.4.16、kaldi-native-fbank、av 18.1.0（venv 局部；requirements 更新见 dependencies-model.md 说明，未改 requirements.lock.txt 既有条目）
- 清单见 `changed-files.json`；未修改：旧语料/gold、检索与问答算法、Astra 文档。

## 已知限制

- **浏览器实测留待 Astra**：麦克风权限/录音/上传/确认交互未由真实浏览器执行（[demo-notes.md](./demo-notes.md) 检查表 a—h）；stub 不冒充浏览器证据。
- 真实转写证据为一段合成 TTS 中文语音：证明本地链路可用，**不代表真人语音识别准确率**。
- 30 秒/5MB 为服务端硬限（已测）；未测极端恶意输入矩阵（按任务不扩大）。

完成后停止，等待 Astra 验收。T021 未发布。
