"""T040 B：真实资料限定生成冒烟（单次执行入口）。

默认 dry-run（只做前置核对与安全摘要，零外部请求）；显式 `--live` 才发真实
HTTP。固定 q08→q10→u03→u04、真实包 v1.2、A 阶段已验收的问题/条件/正式
E/messages，端点 https://api.deepseek.com/chat/completions、model
deepseek-flash、max_tokens=1500、timeout=30 秒、零重试。

预算语义：合计最多 4 次实际外部 HTTP 尝试、每题至多 1 次；HTTP 计数在
实际发送位置（provider.generate 调用即一次尝试，连接失败同样占用）；/ask
条数与外部次数分开；零证据本地短路不计尝试。首次技术失败即停，未执行题
not_attempted；业务不足（insufficient_evidence）可继续。

前置核对：A input-hashes 与 A 材料 SHA、四题 query/conditions/TopK=5/BM25、
当前管线整理的 E/messages 与 A 一致（请求 UUID 不作差异）；实际 provider
只读属性必须为授权官方值。缺密钥/配置不符/材料漂移 → 零请求、非零退出。

密钥仅本地环境读取，不进入命令行/输出/日志；不打印全量环境/HTTP headers/
原始异常。NO_PROXY 保留既有项并补 api.deepseek.com（仅本进程）。

不改产品代码/适配器/提示/旧冒烟脚本；不下载安装；不重试、不换模型/地址/
题目；失败保留，不自修再试。
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
DEFAULT_A_DIR = ROOT / "docs" / "collaboration" / "submissions" / "T040"
DEFAULT_OUT_DIR = BACKEND / ".cache" / "real-qa-smoke" / "T040-B"

QUESTION_ORDER = ("q08", "q10", "u03", "u04")
ENV_ENABLE_FLAGS = ("CAMPUS_GENERATOR", "CAMPUS_PLANNER", "CAMPUS_ASR")
A_MATERIALS = ("dry-run.json", "input-hashes.json", "generation-review-sheet.md", "live-smoke-plan.md")

OFFICIAL_ENDPOINT = "https://api.deepseek.com/chat/completions"
OFFICIAL_MODEL = "deepseek-flash"
OFFICIAL_MAX_TOKENS = 1500
OFFICIAL_TIMEOUT_SECONDS = 30.0
MAX_EXTERNAL_HTTP_ATTEMPTS = 4


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


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
    with guard_enable_flags():
        from campus_assistant.main import create_app
    return create_app


def load_frozen_questions(questions_path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(questions_path.read_text(encoding="utf-8"))
    by_id = {q["question_id"]: q for q in data["questions"]}
    missing = [qid for qid in QUESTION_ORDER if qid not in by_id]
    if missing:
        raise RuntimeError(f"冻结题集缺少题目: {missing}")
    return {qid: by_id[qid] for qid in QUESTION_ORDER}


def request_body_for(question: dict[str, Any], answer_mode: str) -> dict[str, Any]:
    return {
        "query": question["query"],
        "mode": "bm25",
        "top_k": 5,
        "answer_mode": answer_mode,
        "filters": dict(question["conditions"]),
    }


class SendCountingClient:
    """本脚本装配的计数 HTTP 客户端（经适配器 client 注入参数传入）。

    **外部 HTTP 次数只在本客户端 post 发送处计数**：发送前检查总预算并递增
    一次（预算<=4）；连接失败同样计 1（已尝试发送）；发送前本地异常/零证据
    不经过本客户端 → 计 0。不修改产品适配器，不做全局猴子补丁。
    """

    def __init__(self, inner, budget: int = MAX_EXTERNAL_HTTP_ATTEMPTS):
        self._inner = inner
        self._budget = budget
        self.posts = 0
        self.post_log: list[dict[str, Any]] = []

    @property
    def external_http_attempts(self) -> int:
        return self.posts

    @property
    def budget(self) -> int:
        return self._budget

    def post(self, url, **kwargs):
        if self.posts >= self._budget:
            raise RuntimeError(f"外部 HTTP 预算已耗尽（上限 {self._budget} 次），拒绝发送")
        self.posts += 1  # 发送位置计数：连接失败同样占用一次
        entry: dict[str, Any] = {
            "index": self.posts,
            "endpoint": url,
            "outcome": None,
            "response_status": None,
            "error_type": None,
        }
        self.post_log.append(entry)
        try:
            resp = self._inner.post(url, **kwargs)
        except Exception as exc:
            entry["outcome"] = "send_failed"
            entry["error_type"] = type(exc).__name__
            raise
        entry["outcome"] = "response"
        entry["response_status"] = getattr(resp, "status_code", None)
        return resp


class _UnwiredSendCounter:
    """自定义工厂未装配计数客户端时的占位：不谎报外部次数，post 直接拒绝。"""

    posts = 0
    post_log: list = []
    wired = False

    @property
    def external_http_attempts(self) -> int:
        return 0

    def post(self, url, **kwargs):
        raise RuntimeError("未装配计数客户端，拒绝发送")


class AttemptRecordingProvider:
    """provider 调用层审计包装（provider_calls 另列；外部次数以计数客户端为准）。

    仅记录已观察值：成功返回蕴含供应商 HTTP 200（适配器仅在 200 时返回）；
    DeepSeekHTTPError 携带真实状态码；连接/超时/发送前本地异常无供应商状态 → null。
    """

    def __init__(self, inner, send_counter):
        self._inner = inner
        self._send_counter = send_counter
        self.attempts: list[dict[str, Any]] = []
        self.provider_calls = 0

    @property
    def provider_id(self):
        return getattr(self._inner, "provider_id", None)

    @property
    def base_url(self):
        return getattr(self._inner, "base_url", None)

    @property
    def model(self):
        return getattr(self._inner, "model", None)

    @property
    def max_tokens(self):
        return getattr(self._inner, "max_tokens", None)

    @property
    def timeout(self):
        return getattr(self._inner, "timeout", None)

    @property
    def external_http_attempts(self) -> int:
        return self._send_counter.external_http_attempts

    @property
    def send_counter(self):
        return self._send_counter

    def generate(self, **kwargs):
        self.provider_calls += 1
        entry: dict[str, Any] = {
            "index": len(self.attempts) + 1,
            "outcome": None,
            "supplier_http_status": None,
            "supplier_status_note": None,
            "error_type": None,
            "user_message": None,
            "generation_meta": None,
        }
        self.attempts.append(entry)
        try:
            result = self._inner.generate(**kwargs)
        except Exception as exc:
            entry["error_type"] = type(exc).__name__
            entry["user_message"] = getattr(exc, "user_message", None)
            status = getattr(exc, "status_code", None)
            if isinstance(status, int):
                entry["supplier_http_status"] = status
                entry["supplier_status_note"] = "适配器映射的 HTTP 错误所携状态码"
            else:
                entry["supplier_status_note"] = "未观察到供应商状态（发送前本地异常/连接失败/映射错误不暴露原始状态）"
            raise
        entry["outcome"] = "returned"
        entry["supplier_http_status"] = 200
        entry["supplier_status_note"] = "generate() 成功返回蕴含供应商 HTTP 200（适配器仅在 status==200 时返回）"
        meta = result.get("metadata") if isinstance(result, dict) else None
        entry["generation_meta"] = meta if isinstance(meta, dict) else None
        return result


def build_counting_provider(*, api_key: str, base_url: str | None = None, model: str | None = None,
                            inner_client: Any | None = None, trust_env: bool = True):
    """本脚本装配：计数客户端经 client 注入进适配器；不改产品适配器。"""
    import httpx

    from campus_assistant.qa.deepseek import DeepSeekAnswerProvider

    raw = inner_client if inner_client is not None else httpx.Client(trust_env=trust_env)
    counting = SendCountingClient(raw)
    kw: dict[str, Any] = {"client": counting}
    if base_url:
        kw["base_url"] = base_url
    if model:
        kw["model"] = model
    inner = DeepSeekAnswerProvider(api_key, **kw)
    inner._t040_send_counter = counting  # 本脚本实例标记，供 run_b 发现计数句柄
    return inner, counting


def instrument_provider(inner):
    """为工厂产出的 provider 挂接审计包装；外部次数取计数客户端。"""
    counting = getattr(inner, "_t040_send_counter", None) or _UnwiredSendCounter()
    return AttemptRecordingProvider(inner, counting)


def resolve_config(provider) -> dict[str, Any] | None:
    """实际 provider 只读属性——不用计划值冒充。"""
    if provider is None:
        return None
    from campus_assistant.qa.deepseek import chat_completions_url

    base_url = getattr(provider, "base_url", None)
    endpoint = chat_completions_url(base_url) if isinstance(base_url, str) and base_url else None
    return {
        "endpoint": endpoint,
        "model": getattr(provider, "model", None),
        "max_tokens": getattr(provider, "max_tokens", None),
        "timeout_seconds": getattr(provider, "timeout", None),
        "provider_identity": getattr(provider, "provider_id", None),
    }


def check_official_config(resolved: dict[str, Any] | None) -> dict[str, Any]:
    if resolved is None:
        return {"ok": False, "reason": "无已解析配置（生成器未构造）"}
    problems = []
    if resolved.get("endpoint") != OFFICIAL_ENDPOINT:
        problems.append(f"endpoint 非授权官方地址（已解析：{resolved.get('endpoint')}）")
    if resolved.get("model") != OFFICIAL_MODEL:
        problems.append(f"model 非 {OFFICIAL_MODEL}（已解析：{resolved.get('model')}）")
    if resolved.get("max_tokens") != OFFICIAL_MAX_TOKENS:
        problems.append(f"max_tokens 非 {OFFICIAL_MAX_TOKENS}（已解析：{resolved.get('max_tokens')}）")
    if resolved.get("timeout_seconds") != OFFICIAL_TIMEOUT_SECONDS:
        problems.append(f"timeout 非 {OFFICIAL_TIMEOUT_SECONDS}（已解析：{resolved.get('timeout_seconds')}）")
    return {"ok": not problems, "reason": "；".join(problems) or None}


def collect_reference(client, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """当前管线整理的四题正式 E 与 messages（本地 /ask extractive，零外部）。"""
    from campus_assistant.qa.deepseek import build_messages

    out: dict[str, Any] = {}
    for qid in QUESTION_ORDER:
        q = questions[qid]
        body = request_body_for(q, "extractive")
        resp = client.post("/api/v1/ask", json=body)
        if resp.status_code != 200:
            raise RuntimeError(f"{qid}: /api/v1/ask extractive 失败 HTTP {resp.status_code}")
        data = resp.json()
        messages = build_messages(query=q["query"], evidence=data.get("evidence", []), filters=dict(q["conditions"]))
        out[qid] = {
            "request_body": body,
            "evidence": data.get("evidence", []),
            "budget": data.get("budget"),
            "evidence_state": data.get("evidence_state"),
            "messages": messages,
        }
    return out


def verify_a_identity(
    *,
    a_dir: Path,
    a_rev1_dir: Path,
    cache_a_dir: Path,
    current: dict[str, Any],
    questions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """前置核对：A 材料 SHA、输入 SHA、四题 E/messages 与 A 一致（UUID 不作差异）。"""
    problems: list[str] = []

    # 1) A 材料 SHA：提交件 == 归档 == 本地缓存原件（三处一致且未被改写）
    for name in A_MATERIALS:
        main_p, rev1_p, cache_p = a_dir / name, a_rev1_dir / name, cache_a_dir / name
        for p in (main_p, rev1_p, cache_p):
            if not p.exists():
                problems.append(f"A 材料缺失：{p}")
        if main_p.exists() and rev1_p.exists() and cache_p.exists():
            shas = {sha256_file(main_p), sha256_file(rev1_p), sha256_file(cache_p)}
            if len(shas) != 1:
                problems.append(f"A 材料 SHA 不一致：{name}")

    # 2) input-hashes.json 的输入/源文件 SHA 未漂移
    input_hashes_path = a_dir / "input-hashes.json"
    files_checked = 0
    if input_hashes_path.exists():
        recorded = json.loads(input_hashes_path.read_text(encoding="utf-8")).get("files", {})
        for rel, expected in recorded.items():
            if rel == "prepare-real-qa-smoke.py":
                p = BACKEND / "scripts" / rel
            elif rel in ("questions.json", "freeze.json"):
                p = DEFAULT_QUESTIONS.parent / rel
            elif rel == "manifest.json":
                p = DEFAULT_CORPUS_DIR / "manifest.json"
            elif rel == "review-supplement.md":
                p = ROOT / "docs/collaboration/submissions/T039/review-supplement.md"
            else:
                p = BACKEND / "src/campus_assistant" / rel
            if not p.exists():
                problems.append(f"输入缺失：{rel}")
            elif sha256_file(p) != expected:
                problems.append(f"输入 SHA 漂移：{rel}")
            files_checked += 1
    else:
        problems.append("input-hashes.json 缺失")

    # 3) 当前 E/messages 与 A dry-run 一致（请求 UUID 不作差异）
    content_checked = 0
    dry_path = a_dir / "dry-run.json"
    if dry_path.exists():
        a_dry = json.loads(dry_path.read_text(encoding="utf-8"))
        for qid in QUESTION_ORDER:
            a_item = a_dry.get("questions", {}).get(qid)
            if not a_item:
                problems.append(f"A dry-run 缺题目：{qid}")
                continue
            cur = current[qid]
            q = questions[qid]
            a_body = a_item.get("request_body", {})
            for key in ("query", "mode", "top_k", "filters"):
                if a_body.get(key) != cur["request_body"].get(key):
                    problems.append(f"{qid}: 请求字段 {key} 与 A 不一致")
            if a_body.get("query") != q["query"] or a_body.get("filters") != q["conditions"]:
                problems.append(f"{qid}: 请求 query/conditions 与冻结不一致")
            if a_item.get("api_result", {}).get("evidence") != cur["evidence"]:
                problems.append(f"{qid}: 正式 E 证据与 A 不一致（UUID 已排除，比较的是证据全文/跨度/身份）")
            if a_item.get("api_result", {}).get("budget") != cur["budget"]:
                problems.append(f"{qid}: 证据预算与 A 不一致")
            if a_item.get("api_result", {}).get("evidence_state") != cur["evidence_state"]:
                problems.append(f"{qid}: evidence_state 与 A 不一致")
            if a_item.get("future_messages") != cur["messages"]:
                problems.append(f"{qid}: messages 与 A 不一致")
            content_checked += 1
    else:
        problems.append("A dry-run.json 缺失")

    return {
        "ok": not problems,
        "problems": problems,
        "a_materials_sha_checked": len(A_MATERIALS) * 3,
        "input_files_sha_checked": files_checked,
        "questions_content_checked": content_checked,
        "request_uuid_note": "请求 UUID 不作为证据差异；比较字段=query/conditions/mode/top_k/filters/E 全文/预算/messages",
    }


def execute_live_loop(
    *,
    client,
    recording: AttemptRecordingProvider,
    questions: dict[str, dict[str, Any]],
    max_attempts: int = MAX_EXTERNAL_HTTP_ATTEMPTS,
) -> dict[str, Any]:
    """固定题序生成循环：预算内每题至多一次；首次技术失败即停。"""
    results: dict[str, Any] = {}
    stopped_reason = None
    ask_calls = 0

    for qid in QUESTION_ORDER:
        q = questions[qid]
        if stopped_reason is not None:
            results[qid] = {
                "query": q["query"], "conditions": q["conditions"],
                "outcome": "not_attempted", "ask_status": None,
                "local_http_status": None, "supplier_http_status": None,
                "paragraphs": None, "generation_meta": None,
                "attempts": 0, "error": None,
            }
            continue
        if recording.external_http_attempts >= max_attempts:
            stopped_reason = f"预算耗尽（{max_attempts} 次）"
            results[qid] = {
                "query": q["query"], "conditions": q["conditions"],
                "outcome": "not_attempted", "ask_status": None,
                "local_http_status": None, "supplier_http_status": None,
                "paragraphs": None, "generation_meta": None,
                "attempts": 0, "error": None,
            }
            continue

        body = request_body_for(q, "generated")
        attempts_before = recording.external_http_attempts
        provider_before = recording.provider_calls
        ask_calls += 1
        resp = client.post("/api/v1/ask", json=body)
        try:
            data = resp.json()
        except ValueError:
            data = {}
        attempt_delta = recording.external_http_attempts - attempts_before
        provider_delta = recording.provider_calls - provider_before
        last_attempt = recording.attempts[-1] if provider_delta else None
        supplier_status = last_attempt["supplier_http_status"] if last_attempt else None
        supplier_note = (last_attempt or {}).get("supplier_status_note")
        if attempt_delta == 0 and provider_delta > 0:
            supplier_note = "发送前本地失败（未经计数客户端 post），无供应商状态"

        record: dict[str, Any] = {
            "query": q["query"], "conditions": q["conditions"],
            "request_body": body,
            "local_http_status": resp.status_code,
            "local_http_status_note": "本地 /ask 接口状态，非供应商 HTTP 状态",
            "supplier_http_status": supplier_status,
            "supplier_status_note": supplier_note,
            "attempts": attempt_delta,
            "provider_calls": provider_delta,
            "ask_calls_included": 1,
        }

        if resp.status_code == 200 and data.get("status") == "generated":
            paragraphs = [
                {"text": p.get("text"), "evidence_ids": p.get("evidence_ids"), "citations": p.get("citations")}
                for p in (data.get("answer") or {}).get("paragraphs", [])
            ]
            record.update({
                "outcome": "answered",
                "ask_status": "generated",
                "paragraphs": paragraphs,
                "generation_meta": data.get("generation_meta"),
                "error": None,
            })
        elif resp.status_code == 200 and data.get("status") == "insufficient_evidence":
            record.update({
                "outcome": "local_short_circuit" if provider_delta == 0 else "business_insufficient",
                "ask_status": "insufficient_evidence",
                "paragraphs": None,
                "generation_meta": data.get("generation_meta"),
                "insufficient_reason": data.get("insufficient_reason"),
                "error": None,
            })
        else:
            record.update({
                "outcome": "technical_failure",
                "ask_status": data.get("status"),
                "paragraphs": None,
                "generation_meta": data.get("generation_meta"),
                "error_code": data.get("code"),
                "error": data.get("message") or f"本地 /ask HTTP {resp.status_code}",
            })
            stopped_reason = f"技术失败即停（{qid}）：" + str(record["error"])

        results[qid] = record

    return {
        "questions": results,
        "ask_calls": ask_calls,
        "external_http_attempts": recording.external_http_attempts,
        "provider_calls": recording.provider_calls,
        "attempt_log": recording.attempts,
        "send_log": list(getattr(recording.send_counter, "post_log", [])),
        "stop": {
            "reason": stopped_reason or "completed_all",
            "completed": [q for q in QUESTION_ORDER if results[q]["outcome"] in ("answered", "business_insufficient", "local_short_circuit")],
            "not_attempted": [q for q in QUESTION_ORDER if results[q]["outcome"] == "not_attempted"],
        },
        "exit_ok": stopped_reason is None,
    }


def write_outputs(out_dir: Path, payloads: dict[str, str]) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise RuntimeError(f"输出目录非空，拒绝覆盖: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, content in payloads.items():
        (out_dir / name).write_text(content, encoding="utf-8")


def safe_summary(resolved, questions, ref) -> dict[str, Any]:
    return {
        "event": "preflight_summary",
        "provider_config_resolved": resolved,
        "key_present": bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
        "key_note": "仅密钥存在性；不输出密钥值",
        "budget": {
            "max_external_http_attempts": MAX_EXTERNAL_HTTP_ATTEMPTS,
            "max_tokens_per_call": OFFICIAL_MAX_TOKENS,
            "timeout_seconds": OFFICIAL_TIMEOUT_SECONDS,
            "retry": 0,
            "note": "max_tokens 是单次输出限制，不是费用上限；无人民币上限指定，不虚构价格",
        },
        "question_order": list(QUESTION_ORDER),
        "evidence_per_question": {
            qid: {"items": len(ref[qid]["evidence"]), "state": ref[qid]["evidence_state"]}
            for qid in QUESTION_ORDER
        },
    }


def run_b(
    *,
    live: bool,
    a_dir: Path,
    out_dir: Path | None,
    questions_path: Path,
    corpus_root: Path,
    provider_factory=None,
    require_official_config: bool = True,
    a_rev1_dir: Path | None = None,
    cache_a_dir: Path | None = None,
    emit=None,
) -> tuple[dict[str, Any], bool]:
    """前置核对 →（--live）单次执行 → 写输出。返回 (结果, exit_ok)。"""
    say = emit or (lambda obj: print(json.dumps(obj, ensure_ascii=False, indent=2), file=sys.stderr, flush=True))

    # 必修1：输出目录前置门——任何生成/发送之前检查并准备；非空立即拒绝（零发送）。
    # 保留最终写入时的防覆盖；已有输出不删除。恢复真实执行必须使用新的明确目录。
    if out_dir is not None:
        outp = Path(out_dir)
        if outp.exists() and any(outp.iterdir()):
            raise RuntimeError(f"输出目录非空，拒绝覆盖: {outp}")
        outp.mkdir(parents=True, exist_ok=True)

    a_rev1_dir = a_rev1_dir or (a_dir / "rev1")
    cache_a_dir = cache_a_dir or (BACKEND / ".cache" / "real-qa-smoke" / "T040-A")

    questions = load_frozen_questions(Path(questions_path))
    create_app = import_create_app()
    manifest_path = Path(corpus_root) / "manifest.json"

    # 前置 1：A 身份与当前 E/messages（本地 extractive，零外部）
    factory = provider_factory
    if factory is None:
        def factory():
            key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if not key:
                return None
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "").strip() or None
            model = os.environ.get("DEEPSEEK_MODEL", "").strip() or None
            inner, _counting = build_counting_provider(
                api_key=key, base_url=base_url, model=model,
                trust_env=True,  # 真实 API 保留系统代理支持
            )
            return inner

    inner = factory()
    recording = instrument_provider(inner) if inner is not None else None
    app = create_app(
        manifest_path=manifest_path,
        corpus_root=Path(corpus_root),
        embedding_model_path=None,
        answer_provider=recording,
        procedures_path=None,
        self_check_path=None,
        asr_adapter=None,
        planner=None,
    )
    from fastapi.testclient import TestClient

    client = TestClient(app)
    ref = collect_reference(client, questions)
    result_ask_calls_extractive = len(QUESTION_ORDER)  # 前置本地 extractive 核对（非模型次数）
    identity = verify_a_identity(
        a_dir=Path(a_dir), a_rev1_dir=Path(a_rev1_dir), cache_a_dir=Path(cache_a_dir),
        current=ref, questions=questions,
    )

    resolved = resolve_config(inner)
    if inner is None:
        config_check = {"ok": False, "reason": "缺密钥或未构造生成器（DEEPSEEK_API_KEY 不存在/为空）：零请求拒绝"}
    elif require_official_config:
        config_check = check_official_config(resolved)
    else:
        config_check = {
            "ok": True, "reason": None, "note": "显式测试注入，仅跳过官方数值核对；预算/停止/记录规则照常",
        }

    result: dict[str, Any] = {
        "kind": "T040-B 真实资料限定生成冒烟执行记录",
        "responds_to": "T040-B",
        "task_revision": "B-v1",
        "mode": "live" if live else "dry-run",
        "authorization_note": (
            "用户 2026-10-09 对四题/官方端点/deepseek-flash/≤4 次尝试/1500 输出 tokens/"
            "30s/零重试/首次技术失败即停回复“授权”；无人民币上限指定，不虚构金额或价格"
        ),
        "run_identity": {
            "endpoint": (resolved or {}).get("endpoint"),
            "model": (resolved or {}).get("model"),
            "max_tokens": (resolved or {}).get("max_tokens"),
            "timeout_seconds": (resolved or {}).get("timeout_seconds"),
            "config_source": "实际 provider 只读属性（非计划值）" if resolved else "未构造 provider",
            "question_order": list(QUESTION_ORDER),
            "corpus": str(corpus_root),
            "questions_path": str(questions_path),
            "a_identity": identity,
        },
        "preflight": {
            "a_identity_ok": identity["ok"],
            "config_check": config_check,
            "key_present": bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
        },
        "attempt_accounting": {
            "budget_max_external_http_attempts": MAX_EXTERNAL_HTTP_ATTEMPTS,
            "max_attempts_per_question": 1,
            "external_http_attempts": 0,
            "ask_calls": result_ask_calls_extractive,
            "ask_calls_note": "含前置本地 extractive 核对（非模型次数）；外部 HTTP 次数单独计数",
        },
        "questions": {},
        "stop": None,
        "unavailable_fields_note": (
            "供应商未返回或适配器未暴露的字段记 null（含连接/超时/映射错误的供应商原始状态）；"
            "不伪造 usage/价格/请求 ID；本地 /ask HTTP 状态与供应商 HTTP 状态分开记录"
        ),
        "exit_ok": False,
    }

    preflight_ok = identity["ok"] and config_check["ok"]
    if not preflight_ok:
        reason = "；".join([p for p in identity["problems"] if p] + [str(config_check.get("reason") or "") if not config_check["ok"] else ""]).strip("；")
        result["preflight"]["reason"] = "前置未通过：零外部请求"
        say({"event": "preflight_failed", "problems": identity["problems"] + [config_check.get("reason")], "key_present": result["preflight"]["key_present"]})
        result["exit_ok"] = False
        result["stage_note"] = "前置未通过 → B 未发出任何外部请求；本记录即实际执行证据"
        result["questions"] = {
            qid: {
                "query": questions[qid]["query"], "conditions": questions[qid]["conditions"],
                "outcome": "not_attempted", "ask_status": None,
                "local_http_status": None, "supplier_http_status": None,
                "paragraphs": None, "generation_meta": None,
                "attempts": 0, "provider_calls": 0, "error": None,
            }
            for qid in QUESTION_ORDER
        }
        result["stop"] = {"reason": f"前置未通过（{reason or '见 preflight'}），零外部请求", "completed": [], "not_attempted": list(QUESTION_ORDER)}
        if out_dir is not None:
            result["output_dir"] = str(out_dir)
            write_outputs(Path(out_dir), {
                "live-results.json": json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            })
        return result, False

    say(safe_summary(resolved, questions, ref))

    if not live:
        result["attempt_accounting"]["ask_calls"] = result_ask_calls_extractive  # 本地 extractive 核对四次，非模型次数
        result["questions"] = {
            qid: {"query": questions[qid]["query"], "conditions": questions[qid]["conditions"], "outcome": "dry_run_not_sent"}
            for qid in QUESTION_ORDER
        }
        result["stop"] = {"reason": "dry_run_no_requests", "completed": [], "not_attempted": list(QUESTION_ORDER)}
        result["exit_ok"] = True
        return result, True

    if out_dir is None or not getattr(recording.send_counter, "wired", True):
        guard_reason = "无可用输出路径，拒绝开始付费调用" if out_dir is None else "计数客户端未装配，拒绝发送"
        result["preflight"]["reason"] = guard_reason
        result["exit_ok"] = False
        result["stage_note"] = guard_reason + "；零外部请求"
        result["questions"] = {
            qid: {
                "query": questions[qid]["query"], "conditions": questions[qid]["conditions"],
                "outcome": "not_attempted", "ask_status": None,
                "local_http_status": None, "supplier_http_status": None,
                "paragraphs": None, "generation_meta": None,
                "attempts": 0, "provider_calls": 0, "error": None,
            }
            for qid in QUESTION_ORDER
        }
        result["stop"] = {"reason": guard_reason, "completed": [], "not_attempted": list(QUESTION_ORDER)}
        if out_dir is not None:
            result["output_dir"] = str(out_dir)
            write_outputs(Path(out_dir), {"live-results.json": json.dumps(result, ensure_ascii=False, indent=2) + "\n"})
        return result, False

    loop = execute_live_loop(client=client, recording=recording, questions=questions)
    result["questions"] = loop["questions"]
    result["stop"] = loop["stop"]
    result["attempt_accounting"]["external_http_attempts"] = loop["external_http_attempts"]
    result["attempt_accounting"]["provider_calls"] = loop["provider_calls"]
    result["attempt_accounting"]["provider_calls_note"] = "provider.generate 调用数（另列，不作外部次数）"
    result["attempt_accounting"]["ask_calls"] = loop["ask_calls"] + result_ask_calls_extractive
    result["attempt_accounting"]["ask_calls_generated_only"] = loop["ask_calls"]
    result["attempt_accounting"]["attempt_log"] = loop["attempt_log"]
    result["attempt_accounting"]["send_log"] = loop["send_log"]
    result["exit_ok"] = loop["exit_ok"]

    if out_dir is not None:
        full = {
            "kind": "T040-B 完整答案与出站材料（供人工核对）",
            "responds_to": "T040-B",
            "note": "完整文本不截断；与 A 材料同源（E/messages 与 A 一致经前置核对）；不含密钥",
            "questions": {},
        }
        for qid in QUESTION_ORDER:
            item = result["questions"][qid]
            full["questions"][qid] = {
                "query": item["query"],
                "conditions": item["conditions"],
                "outcome": item["outcome"],
                "evidence_full": [
                    {
                        "evidence_id": e["evidence_id"], "text": e["text"],
                        "document_id": e["document_id"], "block_id": e["block_id"],
                        "char_start": e["char_start"], "char_end": e["char_end"],
                        "title": e.get("title"), "version_label": e.get("version_label"),
                        "locator": e.get("locator"), "preview_url": e.get("preview_url"),
                    }
                    for e in ref[qid]["evidence"]
                ],
                "messages_full": ref[qid]["messages"],
                "messages_sha256": hashlib.sha256(
                    json.dumps(ref[qid]["messages"], ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                "answer_paragraphs_full": item.get("paragraphs"),
                "generation_meta": item.get("generation_meta"),
                "insufficient_reason": item.get("insufficient_reason"),
                "attempts": item.get("attempts"),
            }
        payloads = {
            "live-results.json": json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            "live-answers-full.json": json.dumps(full, ensure_ascii=False, indent=2) + "\n",
        }
        write_outputs(Path(out_dir), payloads)
        result["output_dir"] = str(out_dir)

    return result, loop["exit_ok"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="T040 B 真实资料限定生成冒烟（默认 dry-run；--live 才发请求）")
    parser.add_argument("--live", action="store_true", help="显式授权后的真实单次执行（无此标志零请求）")
    parser.add_argument("--a-dir", default=str(DEFAULT_A_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--questions", default=str(DEFAULT_QUESTIONS))
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_DIR))
    args = parser.parse_args(argv)

    if args.live:
        # NO_PROXY：保留既有项并补 api.deepseek.com（仅本进程；不发试探请求）
        for var in ("NO_PROXY", "no_proxy"):
            existing = os.environ.get(var, "")
            parts = [p.strip() for p in existing.split(",") if p.strip()]
            if "api.deepseek.com" not in parts:
                os.environ[var] = ",".join(parts + ["api.deepseek.com"])

    try:
        result, ok = run_b(
            live=args.live,
            a_dir=Path(args.a_dir),
            out_dir=Path(args.out_dir) if args.live else None,
            questions_path=Path(args.questions),
            corpus_root=Path(args.corpus_root),
        )
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.live:
        print(json.dumps({"event": "live_done", "exit_ok": ok, "stop": result.get("stop"),
                          "attempt_accounting": result.get("attempt_accounting"),
                          "output_dir": result.get("output_dir")}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"event": "dry_run_done", "preflight": result.get("preflight"),
                          "run_identity": {"a_identity_ok": result["run_identity"]["a_identity"]["ok"],
                                           "config_check": result.get("preflight", {}).get("config_check")}},
                         ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
