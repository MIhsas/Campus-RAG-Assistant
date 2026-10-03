# T020 真实本地转写证据

**性质**：真实本地 ASR 推理（FunASR Paraformer，Windows CPU），零外部推理调用；**非** mock。原始结构化记录见 `asr-evidence.json`。

## 音频来源（来源明确、允许使用）

| 项 | 值 |
|---|---|
| 来源 | 本地 Windows TTS 合成（Microsoft Huihui Desktop, zh-CN），**非真人录音**，非第三方样本 |
| 文件 | `step2_code/backend/.cache/t020-audio/tts-sample.wav` |
| SHA-256 | `51a3b41b5e4fd97c…`（完整值见 asr-evidence.json） |
| 大小 / 时长 | 252,190 字节 / 5.72 秒 |

## 转写对照（识别输出为原始结果，保留实际错字，未人工改正）

| 参考文本（合成时朗读） | 原始识别输出 |
|---|---|
| 缓考申请须经所在学院批准，并报教务处备案。 | 缓考申请需经所在学院批准并报教务处备案 |

实际差异（如实保留）：“须”识别为“需”；标点“，。”未输出（Paraformer 不带标点模型）。未将识别文本改写成参考文本。

## 模型与运行

| 项 | 值 |
|---|---|
| 适配器 | funasr-paraformer（`asr/adapter.py`，仅从本地目录加载） |
| 模型 | `iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`（ModelScope 公开快照） |
| 本地目录 | `.cache/asr-models/paraformer-zh`（10 文件、889,147,099 字节；文件级 SHA-256 清单见目录内 `PROVENANCE.json`） |
| 环境 | Windows 11 / Python 3.12.7 / torch 2.14.0+cpu / funasr 1.4.16 + kaldi-native-fbank + av 18.1.0 |
| 运行 | 音频解码→16k 单声道→本地推理；载入约 2.6 秒、转写 375 毫秒（本轮记录） |
| 置信度 | 后端未提供，记录为 null（不伪造） |

## 复现命令

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-asr-transcribe.py `
  --model-dir .cache\asr-models\paraformer-zh `
  --audio .cache\t020-audio\tts-sample.wav `
  --reference "缓考申请须经所在学院批准，并报教务处备案。" `
  --audio-origin "本地 Windows TTS 合成（Microsoft Huihui Desktop, zh-CN），非真人录音" `
  --out asr-evidence.json
```

说明：funasr 导入时会在 stdout 打印无关横幅（ffmpeg 提示），请以 `--out` 文件为准读取 JSON。未录制任何用户或周围人的声音；未向第三方上传音频；未调用收费 TTS/推理。

## 边界

- 一段合成语音的转写仅证明本地链路可用（local_asr_verified=true），**不代表真人语音识别准确率**。
- TTS 为合成语音，已在来源栏标注。
