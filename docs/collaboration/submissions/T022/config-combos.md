# T022 配置组合 → 预期/实测能力表

实测对象：现有合成语料（examples/parse-corpus）与现有本地模型/配置；测试资料为合成性质，不代表真实校园效果。零外部调用。

| 配置组合 | 预期能力 | 实测结果 | 一致 |
|---|---|---|---|
| C1 最小（仅语料） | BM25、摘录可用；生成器/ASR/模板/规则未配置 | 检索模式=bm25；生成器=未配置；ASR=未配置；办事/自查=未配置 | ✓ |
| C2 + embedding-model-dir | 三模式可用（bm25、dense、hybrid）；dense 单查询可返回 | 检索模式=bm25、dense、hybrid；dense 查询 HTTP 200 命中 3 条 | ✓ |
| C3 + asr-model-dir | ASR 状态为已配置（模型按需加载） | ASR=已配置（funasr-paraformer / paraformer-zh@provenance-8b449f3ba655） | ✓ |
| C4 + procedures + self-check | 办事模板与自查规则接口可用 | procedures=200；self-check=200 | ✓ |
| C5 生成器（计数桩） | 启动/状态/摘录零生成调用；显式生成可达（桩） | 摘录后调用数=0；显式生成 HTTP 200，调用数=1 | ✓ |
| C6 生成器缺配置 | 明确提示降级，摘录仍可用，不静默当成功启用 | 报告含「请求启用但配置不完整」=True；generator_configured=False | ✓ |

总体：全部一致。

## 可复制 Windows 命令（路径含空格已加引号）

```powershell
Set-Location 'F:\Collage Paper\step2_code\backend'
& .\.venv\Scripts\python.exe scripts\serve-corpus.py `
  --manifest 'F:\Collage Paper\step2_code\backend\examples\parse-corpus\manifest.json' `
  --corpus-root 'F:\Collage Paper\step2_code\backend\examples\parse-corpus'
# 可选功能（均默认关闭，显式指定才启用；模型仅本地目录、不自动下载）：
#   --embedding-model-dir 'F:\Collage Paper\step2_code\backend\models\bge-small-zh-v1.5'
#   --asr-model-dir 'F:\Collage Paper\step2_code\backend\.cache\asr-models\paraformer-zh'
#   --procedures 'F:\Collage Paper\step2_code\backend\examples\procedures\procedures.json'
#   --self-check 'F:\Collage Paper\step2_code\backend\examples\self-check\rule.json'
#   --generator deepseek   # 密钥仅放本地环境变量 CAMPUS_GENERATOR/DEEPSEEK_API_KEY，不进命令行
```
