# TinyAgent 适配评估（T023）

**tinyagent_integration_kind = `reference`**（参考 TinyAgent，自研受限编排；未导入其代码、未接入真实 Agent）

## 1. 来源与快照

| 项 | 值 |
|---|---|
| 候选仓库 | Datawhale `tiny-universe`，子目录 `content/TinyAgent` |
| 官方入口 | https://github.com/datawhalechina/tiny-universe |
| 代码 | https://github.com/datawhalechina/tiny-universe/blob/main/content/TinyAgent/tinyAgent/Agent.py |
| 模型层 | https://github.com/datawhalechina/tiny-universe/blob/main/content/TinyAgent/tinyAgent/LLM.py |
| 抓取时间 | 2026-09-27 |
| 快照 commit（main HEAD） | `a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2` |
| TinyAgent 目录最近变更 commit | `0437012db4f86d353bc23fb4033f69c8abb61198`（2024-05-31） |
| 抓取方式 | HTTPS 只读（`curl` raw + GitHub contents API），未运行任何示例 |

### 文件哈希（本地快照 `tinyagent-snapshot/`，SHA-256）

| 文件 | 字节 | SHA-256 | 上游 blob SHA |
|---|---|---|---|
| Agent.py | 3098 | `9e666ef04526d5af505b955acd620482339496c1caa85520ea11f695324538a1` | `4f4f143bee935a7d1904dac8d0840d5d070f1b02` |
| LLM.py | 1240 | `8eeadc7995f5f5d560f3854b29efec77b622829ff581475560ffa5d7c487ce4e` | `51a5b8ad6115b4ec3d44c0956e478c5f95d19162` |
| tool.py | 1361 | `191e4600e3d082169ac322d67f8d0a429f446e3d095747d344245e8731ac75ca` | `9202c6744fca3524b0729e42a7ab2f9506172229` |
| readme.md | 10021 | `1bc0465319cd7917741c68739b92e374b2ebf79c6688c4c2ef4bb58b9b6e036a` | `90fd06eadd90d76a315d074ea7531503eee0e11e` |
| requirements.txt | 64 | `33d35af9ae40a056a8d454b31341cad026b183f53b7ccc0b331e59f878da5a41` | `f3c402c677cc311e684beb311faca9370cb8c4c8` |

字节数与上游 contents API 的 `size` 一致，blob SHA 与 GitHub 返回一致，快照未被改动。

## 2. 许可

- GitHub 仓库元数据 `"license": null`，仓库根与 `content/TinyAgent` 均无 LICENSE 文件（`https://raw.../LICENSE` 返回 404）。
- readme.md 未声明明确开源许可证。
- **结论：无明确可复用许可。** 因此不复制其源码进入本项目、不引入其依赖栈，仅做接口/思路层面的参考，源码快照只作为评估留档放在提交目录（不进 `src/`、不进后端包）。

## 3. 源码审阅（仅阅读，未运行）

- **Agent.py**：`Agent` 类在 `__init__` 里直接 `InternLM2Chat(path)`（模型层硬耦合）；`build_system_input` 用 ReAct 提示词拼接工具描述；`parse_latest_plugin_call` 从模型输出解析 `Action/Action Input/Observation`；`call_plugin` 里**硬编码 `google_search` 一个工具**，`json5.loads` 解析参数后直接调用；`text_completion` 为两轮 chat + 一次工具调用。
- **LLM.py**：`BaseModel` 抽象 + `InternLM2Chat`，用 `transformers.AutoModelForCausalLM.from_pretrained(...).cuda().eval()`——**依赖本地 InternLM 权重 + CUDA**，`chat()` 是 InternLM 特定签名。
- **tool.py**：`Tools` 类只有一个 `google_search` 工具，走 `requests.post("https://google.serper.dev/search")`（**外部收费搜索 API + API key 占位**），返回首个 organic snippet。
- **requirements.txt**：`torch/torchvision/transformers/json5/sentencepiece` 等——重量级本地推理栈。

## 4. 适配结论

### 直接可复用的接口
- **无运行时代码可直接复用**（许可缺失 + 运行时强耦合）。
- 可复用**接口形状/思路**（非代码）：① 工具用「名称 + 描述 + 参数 schema」声明式注册；② Agent 执行为「动作→工具→观察」循环；③ 从模型输出解析结构化动作。

### 必须替换的耦合（逐项）
| 耦合点 | 官方实现 | 本项目替换 |
|---|---|---|
| 模型层 | `InternLM2Chat` + `transformers` + `.cuda()` | 不接模型。本轮仅 `Planner` 协议 + 脚本化模拟规划器；未来 DeepSeek 走 HTTP 适配器（未实现） |
| 工具层 | 硬编码 `google_search` + serper.dev 付费搜索 | `ToolRegistry` 只读两工具 `search_policy` / `build_checklist_draft`，直接调既有 service |
| 参数解析 | `json5.loads` 后直接 `**kwargs` 调用 | 严格参数校验（类型/范围/枚举 + 范围条件锁），不合法在调用业务前拒绝 |
| 执行循环 | 无预算/无停止条件/无参数校验 | 预算（≤4 轮 / ≤6 工具）+ 单调时钟时限 + 无进展重复停止 |
| 依赖栈 | torch/transformers/json5/sentencepiece | 无新增依赖 |
| 许可 | 无 LICENSE | 不复制源码，仅留档快照 |

### 落地边界（诚实声明）
- **只有参考其思路，故明确写「参考 TinyAgent，自研受限编排」**；本项目 `agent/` 模块为自研，未 import 该仓库任何模块。
- **未写「已集成」**：未运行其官方代码/示例，未下载 InternLM，未开启 `google_search` 默认工具。
- **未据其声称 Windows CPU + DeepSeek 已兼容**：官方示例是本地 InternLM + CUDA，与本项目运行时无关，兼容性未经其官方实现验证。
- **真实 Agent 未接入**：`planner_live_verified=false`。本轮只有固定流程与显式模拟规划器；不新增任何真实 DeepSeek 规划接口，仅在 `planner.py` 留未来连接契约（注释）。

## 5. 未来连接契约（本轮仅设计，未实现）

`campus_assistant/agent/planner.py` 定义 `Planner` 协议（`planner_kind` / `label` / `next_action(round_no, snapshot, observations) -> {type: call|finish, tool, args}`）。未来若接真实 DeepSeek 规划，需一个适配器把工具 schema + 观察序列送给远端模型、解析返回的结构化动作、并实现同样的预算/停止/参数校验；该适配器**不在本轮范围**，运行前不得称「已接入」。
