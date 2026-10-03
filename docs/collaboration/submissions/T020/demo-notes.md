# T020 本地语音输入演示记录与步骤

## 证据层级（先读）

| 层级 | 内容 | 性质 |
|---|---|---|
| 真实本地转写 | `asr-evidence.md` / `asr-evidence.json`（FunASR Paraformer，合成 TTS 音频） | **真实本地推理**（local_asr_verified=true），非 mock |
| 后端 pytest | `tests/test_asr.py` 10 项（限额/解码/未配置/繁忙/错误映射）+ 受影响回归 | 真实本地运行 |
| 页面 stub 行为 | `check-ask-behavior.cjs` 22 场景（+5 语音闭环） | **不是**真实浏览器证据 |
| 依赖/模型来源 | `dependencies-model.md`（选型过程与哈希清单指引） | 真实记录 |

mock 仅存在于测试注入（`MockASRAdapter`，输出标注模拟），不进正常服务默认路径。零外部推理调用（external_model_calls=0）；模型下载为文件获取，单独记录。

## Windows 启动（含真实本地识别）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\demo-campus.py --port 8030 --asr-model-dir .cache\asr-models\paraformer-zh
# 打开 http://127.0.0.1:8030/ask
```

（或环境变量方式：`$env:CAMPUS_ASR='funasr'; $env:CAMPUS_ASR_MODEL_DIR='<模型目录>'` 后启动 demo:app。）

## Astra 可运行检查表（页面闭环 + 权限/上传/确认）

| # | 操作 | 预期 |
|---|---|---|
| a 录音转写 | 点“开始录音”→允许麦克风→说一句中文→“停止”→“转写音频” | 出现“识别结果（funasr-paraformer / …时长/耗时…置信度：未提供）”与可编辑文本；**问题框未被修改**；无自动提问 |
| b 确认填入 | 编辑文本 → 点“使用此文本” | 写入问题框并提示“请手动点击「整理依据」或「生成答案」”；**不自动提问/生成/保存** |
| c 手动提问 | 再点“整理依据” | 走原有摘录流程（快照/历史语义不变） |
| d 已有文字替换 | 问题框已有文字时转写 | 按钮显示“替换问题输入”；点击才替换（明确操作） |
| e 权限拒绝 | 拒绝麦克风权限 | 提示“无法获取麦克风…原问题未被修改”；上传与文字入口保留 |
| f 上传转写 | 选一段 ≤30s/≤5MB 音频 → 转写 | 同 b；超限/损坏音频得到清晰中文提示且原问题保留 |
| g 取消释放 | 录音中点“取消” | 提示“已取消并释放麦克风”，音轨停止（浏览器指示灯熄灭） |
| h 未配置 | 不带 --asr-model-dir 启动 | 转写返回“本地语音识别未配置（可继续使用文字提问）”，文字问答正常 |

## 真实转写演示命令（可复现）

见 `asr-evidence.md`“复现命令”（`scripts/demo-asr-transcribe.py`）。注意 funasr 导入时 stdout 有无关横幅，请以 `--out` 文件为准。

## 边界

- 本地推理、离线加载；未接云端 ASR/DeepSeek；不上传音频；未录制任何真人声音（测试音频为本地 TTS 合成并标注）。
- 一段合成语音转写证明链路可用，不代表真人语音识别准确率。
- 浏览器录音实测（含权限流）留待 Astra；stub 不冒充浏览器证据。
