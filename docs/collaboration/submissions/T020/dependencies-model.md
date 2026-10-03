# T020 依赖与模型来源记录

## 依赖（项目 venv 局部安装，无全局升级、无系统服务、未改代理/TLS）

| 包 | 版本 | 用途 | 安装方式 |
|---|---|---|---|
| torch | 2.14.0+cpu（既有，未改动） | 推理底座 | T010 既有 |
| funasr | 1.4.16 | Paraformer 推理框架 | `pip install funasr`（dry-run 核对零覆盖既有包后安装） |
| kaldi-native-fbank | （wheel） | fbank 特征（FunASR 明确报错提示的两种后端之一，选不耦合 torch 版本者） | `pip install kaldi-native-fbank` |
| av (PyAV) | 18.1.0 | 浏览器 WebM/Opus 与 WAV 解码 → 16k 单声道 | `pip install av` |

选型过程（按任务书顺序）：
1. `pip install --dry-run funasr` 核对：不升级/不覆盖任何既有包（含 torch）→ 安装。
2. 导入正常；首次推理报“缺 fbank 后端（torchaudio 或 kaldi-native-fbank 二选一）”→ 安装 kaldi-native-fbank（不装 torchaudio，避免与 torch 版本耦合）。
3. 修正两处集成问题（均为实现细节，非框架阻断）：Windows 上被进程持有的临时文件 libsndfile 打不开 → 写后关闭再解析、用后即删；`Path.name` 误传文件名 → 传完整路径。随后 Windows CPU 真实转写成功。
4. **结论：FunASR + Paraformer 路径兼容可用，未启用 faster-whisper 替代**（无需第二套实现）。
5. 模型快照下载时系统代理曾 TLS 劫持 modelscope.cn（T014 同款）→ 以 `NO_PROXY=modelscope.cn` 直连下载（仅进程级，不改系统代理）。

## 模型（一份公开模型，项目 .cache，下载与运行分离）

| 项 | 值 |
|---|---|
| 模型 ID | `iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` |
| 来源 | ModelScope 公开模型快照（`scripts/download-asr-model.py`） |
| 本地目录 | `.cache/asr-models/paraformer-zh`（10 文件 / 889,147,099 字节） |
| revision/哈希 | 目录内 `PROVENANCE.json` 为逐文件 SHA-256 清单（可核验身份；不猜测 revision 字段） |
| 运行加载 | 服务仅从已配置本地目录加载（`FunASRParaformerAdapter` / `CAMPUS_ASR_MODEL_DIR` / `demo-campus --asr-model-dir`）；**不自动下载**，未配置即明确不可用 |

## 无远端推理

external_model_calls=0：全部推理为本地 CPU。模型下载是文件获取（单独记录于上表），不含任何推理请求；未使用云端 ASR、收费调用或 DeepSeek。
