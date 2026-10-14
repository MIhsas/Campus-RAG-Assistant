"""T040 A 阶段：真实资料生成质量质检准备（仅本地 dry-run）。

从冻结题集 v2.0 原样读取 q08/q10/u03/u04 的 query/conditions，用真实包
v1.2 与现有 /api/v1/ask extractive 管线收集正式 E 证据包，调用现有
qa.deepseek.build_messages 构造**未来**生成请求材料，并输出：

  dry-run.json             四题实际请求/证据/跨度/来源/messages/检查结果
  input-hashes.json        输入与源文件 SHA 对照
  generation-review-sheet.md  逐题人工核对表（初值全部“待真实运行/待核对”）
  live-smoke-plan.md       未来 B 阶段调用计划（≤4 次外部尝试；本次不执行）

边界（严格执行）：
- 零外部请求：answer_provider=None；build_messages 只构造文本，
  不实例化 HTTP provider、不读取 DEEPSEEK_API_KEY、不发送 HTTP。
- 导入 campus_assistant.main 前，仅在自身进程内暂时关闭
  CAMPUS_GENERATOR / CAMPUS_PLANNER / CAMPUS_ASR 三个启用标志，
  导入后恢复这些非密钥设置（main 模块级默认 app 按标志建 provider）。
- 不添加 --live 或任何可被误执行的付费分支；无下载安装。
- 输出目录非空不覆盖；失败非零退出，不写“完整准备成功”。
- 金标准只做离线支持性对照，绝不插入 messages 或补充检索未发出的证据。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
if str(BACKEND / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND / "src"))

DEFAULT_CORPUS_DIR = ROOT / "data" / "corpora" / "sicau-rag-pilot-v1.2"
DEFAULT_QUESTIONS = ROOT / "data" / "evaluations" / "sicau-rag-pilot-eval-v2" / "questions.json"
DEFAULT_OUT_DIR = BACKEND / ".cache" / "real-qa-smoke" / "T040-A"

QUESTION_IDS = ("q08", "q10", "u03", "u04")
ENV_ENABLE_FLAGS = ("CAMPUS_GENERATOR", "CAMPUS_PLANNER", "CAMPUS_ASR")

# 任务书 §1 四道人工核对标准（固定文本；初值全部“待真实运行/待核对”）
REVIEW_CRITERIA: dict[str, dict[str, str]] = {
    "q08": {
        "focus": "简洁说明带小抄属于作弊；回答避免把“将……修改为”当作结论，证据仍原字保留",
        "must_not": "提示存在不等于真实回答已改善",
    },
    "q10": {
        "focus": "普通 50/50 与开展互评 40/10/50 的前提分别核对；引用是否支持主体与各比例",
        "must_not": "不按年份宣布 2016 已废止；合法 E 编号不等于语义正确",
    },
    "u03": {
        "focus": "as_of=2026-10-03；2019 已核实来源中的 30 分钟禁入与逾时后果",
        "must_not": "不从日期未知来源补答案、不宣称现行性认证",
    },
    "u04": {
        "focus": "本科筛选下 83eb 未进严格依据；已有命中可能不相关，需要核对是否推测办理部门",
        "must_not": "不把候选或 gold 放进上下文，不保证模型会拒答",
    },
}

# 候选/未核实来源不得混入正式证据（任务书语义边界）
CANDIDATE_EXCLUSIONS: dict[str, dict[str, str]] = {
    "u03": {"db05e0": "日期未知来源不入严格 gold，不得作为正式证据"},
    "u04": {"83eb": "scope 未知，本科筛选下未进严格依据"},
}

MATERIAL_FIELD_CLASSES = {
    "api_result": "实际 API 结果：POST /api/v1/ask（answer_mode=extractive）本地返回的正式 E 证据包与预算/状态字段",
    "future_plan": "未来计划材料：build_messages 构造的生成请求 messages（本次未发送、B 阶段未授权）",
    "offline_standard": "离线人工标准：四道核对标准与金标准支持性对照（机器辅助，非人工结论，不进 messages）",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@contextmanager
def guard_enable_flags():
    """导入前关闭三个启用标志，导入后恢复（仅本进程；非密钥设置）。"""
    saved = {f: os.environ.pop(f, None) for f in ENV_ENABLE_FLAGS}
    try:
        yield
    finally:
        for flag, value in saved.items():
            if value is not None:
                os.environ[flag] = value


def import_create_app():
    """在启用标志关闭期间导入 main（其模块级 app 按标志建 provider）。"""
    with guard_enable_flags():
        from campus_assistant.main import create_app
    return create_app


def load_frozen_questions(questions_path: Path) -> dict[str, dict[str, Any]]:
    """从冻结题集原样读取四题（query/conditions 不改写）。"""
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    by_id = {q["question_id"]: q for q in data["questions"]}
    missing = [qid for qid in QUESTION_IDS if qid not in by_id]
    if missing:
        raise RuntimeError(f"冻结题集缺少题目: {missing}")
    return {qid: by_id[qid] for qid in QUESTION_IDS}


def build_app(create_app, manifest_path: Path, corpus_root: Path):
    """显式 answer_provider=None；不启用 planner/ASR/向量/模板；仅真实包。"""
    return create_app(
        manifest_path=manifest_path,
        corpus_root=corpus_root,
        embedding_model_path=None,
        answer_provider=None,
        procedures_path=None,
        self_check_path=None,
        asr_adapter=None,
        planner=None,
    )


def request_body_for(question: dict[str, Any]) -> dict[str, Any]:
    """冻结 query/conditions 原样进入请求体；不添加文件选择/候选。"""
    return {
        "query": question["query"],
        "mode": "bm25",
        "top_k": 5,
        "answer_mode": "extractive",
        "filters": dict(question["conditions"]),
    }


def collect_extractive(client, question: dict[str, Any]) -> dict[str, Any]:
    body = request_body_for(question)
    resp = client.post("/api/v1/ask", json=body)
    if resp.status_code != 200:
        raise RuntimeError(
            f"/api/v1/ask 失败 {question['question_id']}: HTTP {resp.status_code} {resp.text[:200]}"
        )
    return {"request_body": body, "response": resp.json()}


def check_frozen_consistency(question: dict[str, Any], api: dict[str, Any]) -> None:
    """四题请求与冻结 query/conditions 相同（硬校验）。"""
    if api["query"] != question["query"]:
        raise RuntimeError(f"{question['question_id']}: 回显 query 与冻结不一致")
    echoed = api.get("filters") or {}
    for key in ("campus", "student_type", "admission_year", "as_of_date"):
        if echoed.get(key) != question["conditions"].get(key):
            raise RuntimeError(f"{question['question_id']}: 回显条件 {key} 与冻结不一致")
    if api.get("answer_mode") != "extractive" or api.get("status") != "evidence_only":
        raise RuntimeError(f"{question['question_id']}: 不是 extractive/evidence_only 形态")


def index_blocks(app) -> dict[tuple[str, str], str]:
    blocks: dict[tuple[str, str], str] = {}
    for doc in app.state.corpus_data or []:
        for block in doc.get("blocks", []):
            blocks[(doc.get("document_id", ""), block.get("block_id", ""))] = block.get("text", "")
    return blocks


def check_evidence_slices(
    question: dict[str, Any], evidence: list[dict[str, Any]], blocks: dict[tuple[str, str], str]
) -> None:
    """证据切片正确：text == 原块 [char_start,char_end) 逐字；准入（候选不混入）。"""
    for ev in evidence:
        key = (ev["document_id"], ev["block_id"])
        if key not in blocks:
            raise RuntimeError(f"{question['question_id']}: 证据块不在解析结果中 {key}")
        slice_text = blocks[key][ev["char_start"] : ev["char_end"]]
        if slice_text != ev["text"]:
            raise RuntimeError(f"{question['question_id']}: 证据切片不一致 {ev['evidence_id']}")
        if ev.get("is_synthetic"):
            raise RuntimeError(f"{question['question_id']}: 混入合成资料 {ev['evidence_id']}")
    for prefix, reason in CANDIDATE_EXCLUSIONS.get(question["question_id"], {}).items():
        bad = [ev["evidence_id"] for ev in evidence if ev["document_id"].startswith(prefix)]
        if bad:
            raise RuntimeError(f"{question['question_id']}: 候选来源混入 {prefix} -> {bad}（{reason}）")


def check_messages_clean(
    question: dict[str, Any],
    evidence: list[dict[str, Any]],
    messages: list[dict[str, str]],
    build_messages,
    filters: dict[str, Any],
) -> dict[str, Any]:
    """messages 与现有 builder 一致；gold 不在证据里就不在 messages 里。"""
    rebuilt = build_messages(query=question["query"], evidence=evidence, filters=filters)
    if rebuilt != messages:
        raise RuntimeError(f"{question['question_id']}: messages 与 build_messages 输出不一致")
    user_content = messages[1]["content"]
    for ev in evidence:
        block = f"【{ev['evidence_id']}】\n{ev['text']}"
        if block not in user_content:
            raise RuntimeError(f"{question['question_id']}: messages 缺少证据块 {ev['evidence_id']}")
    joined_evidence = "\n".join(ev["text"] for ev in evidence)
    gold_leaks = []
    for gold in question.get("evidence", []):
        quote = gold.get("quote", "")
        if quote and quote in user_content and quote not in joined_evidence:
            gold_leaks.append(gold.get("fact_id"))
    if gold_leaks:
        raise RuntimeError(f"{question['question_id']}: gold 文本被塞入 messages: {gold_leaks}")
    return {"builder_consistent": True, "evidence_blocks_in_messages": len(evidence), "gold_leaks": 0}


def gold_coverage_offline(question: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """离线支持性对照（非人工结论）：按 fact_id 组检查检索证据是否覆盖 gold 跨度。"""
    facts: dict[str, list[dict[str, Any]]] = {}
    for gold in question.get("evidence", []):
        facts.setdefault(gold.get("fact_id", "?"), []).append(gold)
    per_fact = []
    for fact_id, items in facts.items():
        matched = []
        for gold in items:
            for ev in evidence:
                same_block = (
                    ev["document_id"] == gold.get("document_id")
                    and ev["block_id"] == gold.get("block_id")
                )
                span_covered = (
                    same_block
                    and gold.get("char_start", -1) >= ev["char_start"]
                    and gold.get("char_end", -1) <= ev["char_end"]
                )
                quote_covered = bool(gold.get("quote")) and gold["quote"] in ev["text"]
                if span_covered or quote_covered:
                    matched.append(ev["evidence_id"])
        per_fact.append({
            "fact_id": fact_id,
            "source_count": len(items),
            "covered_by_evidence_ids": sorted(set(matched)),
            "covered": bool(matched),
        })
    gaps = [f["fact_id"] for f in per_fact if not f["covered"]]
    return {
        "kind": "离线机器对照（金标准支持性；非人工结论、不进 messages）",
        "per_fact": per_fact,
        "gap_fact_ids": gaps,
    }


def per_question_plan(question_id: str, response: dict[str, Any]) -> dict[str, Any]:
    """未来 B 阶段单题计划：零证据本地短路、外部尝试为零；否则至多一次。"""
    evidence = response.get("evidence", [])
    state = response.get("evidence_state")
    if not evidence:
        return {
            "planned_external_attempts": 0,
            "rule": "零证据本地短路：不调用外部、不补跑（evidence_state=%s）" % state,
        }
    return {
        "planned_external_attempts": 1,
        "rule": "至多一次外部 HTTP 尝试；首次技术失败即停，不补跑凑成功",
    }


def _evidence_brief(ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "evidence_id": ev["evidence_id"],
        "title": ev.get("title"),
        "version_label": ev.get("version_label"),
        "document_id_prefix": ev["document_id"][:8],
        "block_id": ev.get("block_id"),
        "char_start": ev.get("char_start"),
        "char_end": ev.get("char_end"),
        "locator": ev.get("locator"),
        "text_chars": len(ev.get("text", "")),
        "text_preview": ev.get("text", "")[:80],
    }


def build_dry_run(
    questions: dict[str, dict[str, Any]],
    collected: dict[str, dict[str, Any]],
    messages_by_id: dict[str, list[dict[str, str]]],
    checks_by_id: dict[str, dict[str, Any]],
    coverage_by_id: dict[str, dict[str, Any]],
    status_payload: dict[str, Any],
    input_hashes: dict[str, Any],
) -> dict[str, Any]:
    items = {}
    for qid in QUESTION_IDS:
        api = collected[qid]["response"]
        items[qid] = {
            "frozen_query": questions[qid]["query"],
            "frozen_conditions": questions[qid]["conditions"],
            "request_body": collected[qid]["request_body"],
            "api_result": {
                "status": api.get("status"),
                "evidence_state": api.get("evidence_state"),
                "evidence": api.get("evidence", []),
                "budget": api.get("budget"),
                "filter_summary": api.get("filter_summary"),
                "source_selection": api.get("source_selection"),
                "query_tokens": api.get("query_tokens"),
                "request_id": api.get("request_id"),
            },
            "future_messages": messages_by_id[qid],
            "checks": checks_by_id[qid],
            "gold_coverage_offline": coverage_by_id[qid],
            "plan": per_question_plan(qid, api),
        }
    return {
        "kind": "T040-A 本地 dry-run（零外部请求）",
        "field_classes": MATERIAL_FIELD_CLASSES,
        "inputs_sha256": input_hashes,
        "app_identity": {
            "corpus_pack": "data/corpora/sicau-rag-pilot-v1.2/",
            "questions": "data/evaluations/sicau-rag-pilot-eval-v2/questions.json",
            "dataset_version": "2.0",
            "answer_provider": None,
            "generator_configured": status_payload.get("generator_configured"),
            "available_modes": status_payload.get("available_modes"),
            "mode": "bm25",
            "top_k": 5,
            "evidence_budget": {"max_items": 5, "max_total_chars": 6000},
        },
        "external_requests": 0,
        "external_request_proof": [
            "create_app 显式 answer_provider=None（/api/v1/ask/status generator_configured=false）",
            "build_messages 只构造文本，不实例化 HTTP provider、不读取 DEEPSEEK_API_KEY",
            "本脚本无网络调用代码路径；TestClient 为进程内 ASGI，不发出网络请求",
        ],
        "questions": items,
    }


def build_review_sheet(dry_run: dict[str, Any]) -> str:
    lines = [
        "# T040 生成质量逐题人工核对表（generation-review-sheet.md）",
        "",
        "> 用途：B 阶段真实运行后逐项人工评阅。**当前全部初值=待真实运行/待核对**；",
        "> 本表不含任何模型答案，不代签、不给通过勾选。完整原引与出处见",
        "> [T039 review-supplement](../T039/review-supplement.md)（四项补充）。",
        "> 字段归属：实际 API 结果=/ask extractive 正式 E 证据包；未来计划=未发送的 messages；",
        "> 离线人工标准=核对重点/金标准支持性对照（机器辅助，非人工结论）。",
        "",
    ]
    for qid in QUESTION_IDS:
        item = dry_run["questions"][qid]
        api = item["api_result"]
        crit = REVIEW_CRITERIA[qid]
        plan = item["plan"]
        lines += [
            f"## {qid}",
            "",
            f"- **问题（冻结原样）**：{item['frozen_query']}",
            f"- **适用条件（冻结原样）**：`{json.dumps(item['frozen_conditions'], ensure_ascii=False)}`",
            f"- **核对重点**：{crit['focus']}",
            f"- **不可冒称**：{crit['must_not']}",
            f"- **实际证据状态（API 结果）**：evidence_state=`{api['evidence_state']}`，"
            f"预算内 E 条数={api['budget']['included_items']}（字符 {api['budget']['included_chars']}，"
            f"跳过 {api['budget']['skipped_items']}）",
            f"- **未来生成计划**：外部尝试 {plan['planned_external_attempts']} 次——{plan['rule']}",
            "",
            "### 实际请求证据（正式 E，实际 API 结果）",
            "",
            "| E | 标题 | 版本 | 文档 | 块 | 字符跨度 | 定位 | 字符数 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for ev in api["evidence"]:
            brief = _evidence_brief(ev)
            locator = brief["locator"] or {}
            loc = locator.get("label") or locator.get("page") or ""
            lines.append(
                f"| {brief['evidence_id']} | {brief['title']} | {brief['version_label']} | "
                f"`{brief['document_id_prefix']}` | `{brief['block_id'][:12]}` | "
                f"[{brief['char_start']},{brief['char_end']}) | {loc} | {brief['text_chars']} |"
            )
        if not api["evidence"]:
            lines.append("| （无证据） | | | | | | | |")
        coverage = item["gold_coverage_offline"]
        gap_note = (
            f"缺口 fact：{', '.join(coverage['gap_fact_ids'])}（已记录缺口，不修数据补齐）"
            if coverage["gap_fact_ids"]
            else "机器对照未见缺口（≠人工确认）"
        )
        lines += [
            "",
            "### 金标准支持性对照（离线人工标准；机器辅助，非人工结论，不进 messages）",
            "",
        ]
        for fact in coverage["per_fact"]:
            mark = "已覆盖" if fact["covered"] else "**缺口**"
            lines.append(
                f"- fact `{fact['fact_id']}`（{fact['source_count']} 源）：{mark}"
                + (f"，命中 {', '.join(fact['covered_by_evidence_ids'])}" if fact["covered"] else "")
            )
        lines += [
            f"- 汇总：{gap_note}",
            "",
            "### 人工核对栏（初值=待真实运行/待核对）",
            "",
            "| 核对项 | 初值 |",
            "|---|---|",
            "| 答案是否忠于证据（逐段引用支持性） | 待真实运行/待核对 |",
            "| 核对重点逐项结论 | 待真实运行/待核对 |",
            "| 是否违反“不可冒称” | 待真实运行/待核对 |",
            "| 证据适用条件/现行性 | 待真实运行/待核对 |",
            f"| 业务不足 vs 技术失败区分 | 待真实运行/待核对 |",
            "",
        ]
        if qid == "u04":
            lines += [
                "> u04 专项：已有命中可能不相关——需人工核对模型是否推测办理部门；",
                "> 不保证模型会拒答；候选原文是独立查看功能，本次未混入。",
                "",
            ]
    return "\n".join(lines)


def build_live_smoke_plan(dry_run: dict[str, Any], system_prompt_sha: str) -> str:
    lines = [
        "# T040 未来 B 阶段调用计划（live-smoke-plan.md，本次只写计划）",
        "",
        "> **状态：A 阶段本地准备完成；真实调用 B 未授权、未执行、未验证。**",
        "> 以下参数是**当前代码计划参数**（deepseek.py 默认值），不是重新访问官网",
        "> 或确认服务可用的结论。不伪造价格/预计 usage；max_tokens 不是费用上限。",
        "",
        "## 1. 计划参数（现有适配器当前默认）",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 端点 | `https://api.deepseek.com/chat/completions`（官方；base+`/chat/completions`） |",
        "| model | `deepseek-flash` |",
        "| max_tokens | 1500 |",
        "| timeout | 30 秒 |",
        "| 重试 | **零重试**（适配器无自动重试） |",
        f"| 系统提示 | 现有 SYSTEM_PROMPT（SHA256 `{system_prompt_sha[:16]}…`，不改写） |",
        "",
        "## 2. 尝试约束（一次、四题、≤4 次外部 HTTP 尝试）",
        "",
        "1. 固定四题 q08/q10/u03/u04，每题至多 **1 次**外部尝试，合计 **≤4 次**。",
        "2. **首次技术失败即停**（HTTP 错误/超时/连接失败），不补跑凑成功。",
        "3. **零证据本地短路**：证据包为空的题不调用外部、外部尝试为零。",
        "4. 业务不足（模型返回 insufficient_evidence）与技术失败分开记录。",
        "5. 密钥仅未来本地环境配置；不出现在报告/命令/日志；未授权不询问/读取密钥。",
        "",
        "## 3. 出站内容清单（本次实际构造的材料，未发送）",
        "",
    ]
    for qid in QUESTION_IDS:
        item = dry_run["questions"][qid]
        plan = item["plan"]
        msgs = item["future_messages"]
        user_chars = len(msgs[1]["content"])
        ev_ids = [ev["evidence_id"] for ev in item["api_result"]["evidence"]]
        lines += [
            f"### {qid}（计划尝试 {plan['planned_external_attempts']} 次）",
            "",
            f"- 出站=问题：{item['frozen_query']}",
            f"- 出站=适用条件：`{json.dumps(item['frozen_conditions'], ensure_ascii=False)}`",
            f"- 出站=选定正式证据：{', '.join(ev_ids) if ev_ids else '（无——本地短路）'}"
            f"（messages user 内容共 {user_chars} 字符；**字符数≠token 数**）",
            f"- 出站=现有系统提示（SHA256 `{system_prompt_sha[:16]}…`）",
            "- **不发送**：用户复核记录、gold、未核实候选、个人待办、全库、API 密钥、本机路径。",
            "",
        ]
    lines += [
        "## 4. B 阶段记录要求（届时执行，本次不填）",
        "",
        "- 每题记录：完整答案、E 映射（paragraph→evidence_ids）、status（generated/insufficient_evidence/错误码）。",
        "- 真实审计：model/request_id/usage/latency/max_tokens（供应商未返回的字段为 null，不伪造）。",
        "- 实际尝试次数与停止原因；业务不足与技术失败分开。",
        "- 逐段引用支持性、答案忠于证据与否——**待人工核对**（generation-review-sheet.md）。",
        "",
        "## 5. 授权与边界声明",
        "",
        "- 本计划**未获授权执行**：A 阶段由 Astra 先验收，用户随后决定真实调用与费用约束。",
        "- 不探测供应商/账户/网络；不因本机已有密钥发请求；T014/T025 旧授权不延续。",
        "- `live_verified=false`、`external_model_calls=0`；真实模型是否忠于证据/能否拒答都待验证。",
    ]
    return "\n".join(lines)


def collect_input_hashes(
    questions_path: Path,
    manifest_path: Path,
    questions: dict[str, dict[str, Any]],
    system_prompt: str,
) -> dict[str, Any]:
    from campus_assistant.qa.deepseek import SYSTEM_PROMPT

    assert system_prompt == SYSTEM_PROMPT
    sources = {
        "questions.json": questions_path,
        "freeze.json": questions_path.parent / "freeze.json",
        "manifest.json": manifest_path,
        "review-supplement.md": ROOT / "docs/collaboration/submissions/T039/review-supplement.md",
        "main.py": BACKEND / "src/campus_assistant/main.py",
        "api/ask.py": BACKEND / "src/campus_assistant/api/ask.py",
        "qa/evidence.py": BACKEND / "src/campus_assistant/qa/evidence.py",
        "qa/deepseek.py": BACKEND / "src/campus_assistant/qa/deepseek.py",
        "retrieval/service.py": BACKEND / "src/campus_assistant/retrieval/service.py",
        "prepare-real-qa-smoke.py": Path(__file__).resolve(),
    }
    result = {
        "kind": "输入与源文件 SHA 对照（生成时实测）",
        "files": {name: sha256_file(path) for name, path in sources.items()},
        "frozen_question_entries": {
            qid: sha256_text(json.dumps(questions[qid], ensure_ascii=False, sort_keys=True))
            for qid in QUESTION_IDS
        },
        "system_prompt_sha256": sha256_text(system_prompt),
    }
    return result


def write_outputs(out_dir: Path, payloads: dict[str, str]) -> None:
    """新目录写入；非空输出目录不覆盖。"""
    if out_dir.exists() and any(out_dir.iterdir()):
        raise RuntimeError(f"输出目录非空，拒绝覆盖: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in payloads.items():
        (out_dir / name).write_text(content, encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Path]:
    questions_path = Path(args.questions)
    manifest_path = Path(args.manifest)
    corpus_root = Path(args.corpus_root)
    out_dir = Path(args.out_dir)

    questions = load_frozen_questions(questions_path)
    create_app = import_create_app()
    app = build_app(create_app, manifest_path, corpus_root)
    blocks = index_blocks(app)

    from campus_assistant.qa.deepseek import SYSTEM_PROMPT, build_messages

    from fastapi.testclient import TestClient

    client = TestClient(app)
    status_resp = client.get("/api/v1/ask/status")
    if status_resp.status_code != 200:
        raise RuntimeError(f"/api/v1/ask/status 失败: HTTP {status_resp.status_code}")
    status_payload = status_resp.json()
    if status_payload.get("generator_configured"):
        raise RuntimeError("生成器被配置——A 阶段必须 answer_provider=None")

    collected: dict[str, dict[str, Any]] = {}
    messages_by_id: dict[str, list[dict[str, str]]] = {}
    checks_by_id: dict[str, dict[str, Any]] = {}
    coverage_by_id: dict[str, dict[str, Any]] = {}

    for qid in QUESTION_IDS:
        question = questions[qid]
        got = collect_extractive(client, question)
        api = got["response"]
        check_frozen_consistency(question, api)
        evidence = api.get("evidence", [])
        check_evidence_slices(question, evidence, blocks)
        messages = build_messages(
            query=question["query"], evidence=evidence, filters=dict(question["conditions"])
        )
        checks_by_id[qid] = check_messages_clean(
            question, evidence, messages, build_messages, dict(question["conditions"])
        )
        coverage_by_id[qid] = gold_coverage_offline(question, evidence)
        collected[qid] = got
        messages_by_id[qid] = messages

    input_hashes = collect_input_hashes(
        questions_path, manifest_path, questions, SYSTEM_PROMPT
    )
    dry_run = build_dry_run(
        questions, collected, messages_by_id, checks_by_id, coverage_by_id, status_payload, input_hashes
    )
    payloads = {
        "dry-run.json": json.dumps(dry_run, ensure_ascii=False, indent=2) + "\n",
        "input-hashes.json": json.dumps(input_hashes, ensure_ascii=False, indent=2) + "\n",
        "generation-review-sheet.md": build_review_sheet(dry_run),
        "live-smoke-plan.md": build_live_smoke_plan(dry_run, input_hashes["system_prompt_sha256"]),
    }
    write_outputs(out_dir, payloads)
    return {name: out_dir / name for name in payloads}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="T040 A 阶段本地 dry-run 准备（零外部请求；无 --live/付费分支）"
    )
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--manifest", default=str(DEFAULT_CORPUS_DIR / "manifest.json"))
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args(argv)
    try:
        written = run(args)
    except Exception as exc:  # 失败非零退出，不写“完整准备成功”
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print("PREPARE OK: 4 题 dry-run 完成；外部请求 0")
    for name, path in written.items():
        print(f"written: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
