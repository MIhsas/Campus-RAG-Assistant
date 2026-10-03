# T020 验证记录

工作目录 `F:\Collage Paper\step2_code\backend`。聚焦验证；external_model_calls=0（全部本地 CPU 推理，无云端/收费调用）。依赖有变已跑 pip check。

## 1. 依赖与模型（详见 dependencies-model.md）

```bash
./.venv/Scripts/python.exe -m pip install --dry-run funasr     # 零覆盖既有包（含 torch）→ 才安装
./.venv/Scripts/python.exe -m pip install funasr               # funasr 1.4.16（退出 0）
./.venv/Scripts/python.exe -m pip install kaldi-native-fbank   # 首次推理报“缺 fbank 后端”后按其提示安装（退出 0）
./.venv/Scripts/python.exe -m pip install av                   # 18.1.0（WebM/Opus 解码，退出 0）
NO_PROXY=modelscope.cn ./.venv/Scripts/python.exe scripts/download-asr-model.py
# {"model_id": "iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
#  "local_dir": ".cache\\asr-models\\paraformer-zh", "files": 10, "total_bytes": 889147099}（退出 0）
./.venv/Scripts/python.exe -m pip check
# No broken requirements found.（退出码 0）
```

- FunASR 首选路径兼容成功（Windows/Python 3.12/torch 2.14 CPU）：仅需按其明确报错补 fbank 后端 + 两处集成细节（临时文件句柄、路径传递），**未启用 faster-whisper 替代、未遍历其他模型**。
- 下载期系统代理 TLS 劫持 modelscope.cn（T014 同款）：进程级 `NO_PROXY` 直连解决，未改系统代理。

## 2. 真实本地转写证据（local_asr_verified=true）

```bash
./.venv/Scripts/python.exe scripts/demo-asr-transcribe.py --model-dir .cache/asr-models/paraformer-zh \
  --audio .cache/t020-audio/tts-sample.wav \
  --reference "缓考申请须经所在学院批准，并报教务处备案。" \
  --audio-origin "本地 Windows TTS 合成（Microsoft Huihui Desktop, zh-CN），非真人录音" \
  --out "F:/Collage Paper/docs/collaboration/submissions/T020/asr-evidence.json"
# 退出码：0
```

结果（完整见 `asr-evidence.json` / `asr-evidence.md`）：参考“缓考申请须经所在学院批准，并报教务处备案。”→ **原始识别**“缓考申请需经所在学院批准并报教务处备案”（须→需、标点丢失，实际差异保留未改）；provider=funasr-paraformer、model=paraformer-zh@paraformer-zh；音频 5.72 秒/252190 字节/sha256 记录；转写 375ms；置信度 null（不伪造）。音频为本地 TTS 合成并标注，未录制真人声音、未上传第三方。

## 3. 相关 pytest 与受影响回归

```bash
./.venv/Scripts/python.exe -m pytest tests/test_self_check.py tests/test_asr.py -q -p no:cacheprovider --basetemp .cache/t020-iter2 --tb=short -rs
# 21 passed, 2 warnings in 1.49s（test_asr 10 + test_self_check 11）
# 退出码：0
```

- `test_asr.py`（10 项）：WAV 解码与时长、空/损坏音频、5MB/30 秒硬限、503 未配置（含“可继续使用文字提问”）、标记 mock 转写字段（provider 带 mock、duration/elapsed、confidence=null）、502 执行错误、409 单并发（两线程 200+409）、env 门控（未配置/缺目录/正常）。
- 受影响回归：`test_self_check.py` 11 项（T019-R1 说明改动后仍绿——未知解释现为“您尚未确认该项…”）。
- 集成调试记录：两处实现 bug（NamedTemporaryFile 持句柄致 libsndfile 打不开→写后关闭用后即删；`Path.name` 误传文件名→传完整路径）修复后真实转写成功；funasr 导入横幅混入 stdout（以 `--out` 文件为准）。

## 4. JS 语法与 ask 行为

```bash
"D:/nodejs/node.exe" scripts/check-js-syntax.cjs
# All 7 HTML files passed syntax check.（退出码 0）
"D:/nodejs/node.exe" scripts/check-ask-behavior.cjs
# check-ask-behavior: 22 scenarios passed（退出码 0，17 原有 + 5 语音闭环）
```

语音 5 场景：录音→停止→转写→编辑→“使用此文本”填入且**零自动 /ask**；转写失败（400）原问题保持不变；已有文字时按钮显式“替换问题输入”才替换；权限拒绝提示并保留上传/文字入口；取消释放音轨（track.stop 计数）并禁用转写。既有快照/历史/失败转摘录回归不破。

## 5. 统一演示复核

```bash
./.venv/Scripts/python.exe scripts/demo-campus.py --record-api .cache/t020-campus-check.json --asr-model-dir .cache/asr-models/paraformer-zh
# 12 路由全 200（含 ASR 目录注入）；退出码：0
```

## 6. 浏览器检查情况（如实说明）

本会话**无浏览器工具**：麦克风权限流、录音、上传、确认填入未由真实浏览器执行；[demo-notes.md](./demo-notes.md) 提供 Astra 可运行检查表（a—h）。stub 不冒充浏览器证据；模型下载不等于推理调用（external_model_calls=0）。

## 7. 未验证项

1. 真实浏览器语音闭环（交 Astra 补验）。
2. 真人语音识别准确率（证据为一段合成 TTS 语音，仅证明链路可用）。
3. 极端/恶意音频输入矩阵、30 秒边界毫秒级边界：按任务不扩大。
4. WebM/Opus 真实浏览器录音文件解码：代码路径经 PyAV（支持），但无浏览器实录样本——随 Astra 浏览器补验覆盖。
