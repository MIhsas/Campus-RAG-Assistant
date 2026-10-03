"""DeepSeek live smoke script (T014 local preparation, revision 2).

Default mode is DRY-RUN (Part A, authorized): runs LOCAL retrieval over the
two synthetic questions and prints a review summary — no network I/O, no
API key required, key never printed.

Real calls (--live, Part B) are NOT authorized at publication time. Execute
them only after the user explicitly authorizes calls and configures a local
key. Policy even after authorization: at most 2 external HTTP attempts
total, no retries, stop immediately on the first technical failure.

Preflight rules (T014-R1 fixes — all checked BEFORE any call):
- the corpus must parse valid, be non-empty and mark EVERY document
  is_synthetic=true; invalid / empty / non-synthetic corpora exit non-zero
  without touching the provider;
- --live without a configured generator exits non-zero (not a successful
  preparation);
- --live reviews the ACTUAL provider config (endpoint / model / max_tokens
  resolved from the provider, not hardcoded plan values) and refuses to call
  if it does not match this task's authorized official values
  (https://api.deepseek.com, model=deepseek-flash, max_tokens=1500).
  Explicit test injections (loopback) skip only the official-value gate —
  corpus and preflight exit-code rules always apply.

Recording rules (kept from revision 1 / T013-R1 fixes):
- failures exit non-zero; each record separately marks HTTP success,
  generation success or insufficient material;
- structured audit fields are preserved COMPLETE — only the answer PREVIEW
  is truncated (--answer-preview-chars capped 1—2000, a preview limit only,
  NOT a token/cost limit). --full-answers-out saves complete answers as a
  separate local JSON; preview truncation != model truncation;
- ask_requests (generated /ask calls) and external_http_attempts (actual
  provider HTTP attempts) are counted separately; a short-circuited /ask is
  NOT a model call;
- `ask_http_status_code` is the LOCAL /ask HTTP status — never the vendor's
  raw status. Unknown vendor status is not guessed.

Output streams: the review summary is displayed on STDERR (flushed BEFORE
the first HTTP call); the complete structured result (including the same
review summary) is one JSON document on STDOUT.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\live-smoke-deepseek.py                    # dry-run
    .venv\\Scripts\\python.exe scripts\\live-smoke-deepseek.py --live --full-answers-out live-answers-full.local.json   # later, authorized
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

MAX_EXTERNAL_HTTP_ATTEMPTS = 2
MAX_TOKENS = 1500
ANSWER_PREVIEW_CHARS_MIN = 1
ANSWER_PREVIEW_CHARS_MAX = 2000
EVIDENCE_BUDGET_CHARS = 6000

# This task's authorized official values (T014 Part B scope).
OFFICIAL_TARGET = "https://api.deepseek.com/chat/completions"
OFFICIAL_MODEL = "deepseek-flash"

# Two synthetic questions over examples/parse-corpus (T014). Retrieval gold
# is untouched. mode=bm25, max_tokens=1500, evidence <= 6000 chars each.
QUESTIONS = [
    {
        "question_id": "smoke-01-answerable",
        "kind": "answerable",
        "query": "缓考申请须由谁批准，之后还需要向哪个部门备案？",
        "filters": {"admission_year": 2023},
        "expectation": "对照 parse-corpus TXT 第二条：所在学院批准、教务处备案（答案措辞可不同）",
    },
    {
        "question_id": "smoke-02-insufficient",
        "kind": "insufficient",
        "query": "宿舍门禁时间是几点？",
        "filters": None,
        "expectation": "语料无此事实：应说明材料不足，不得用模型常识作答；若无候选则本地短路，真实 HTTP 次数为 0",
    },
]


def _ensure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream.encoding and stream.encoding.lower().replace("-", "") == "utf8":
                continue
            wrapped = io.TextIOWrapper(stream.buffer, encoding="utf-8", line_buffering=True)
            if stream is sys.stdout:
                sys.stdout = wrapped
            else:
                sys.stderr = wrapped
        except (AttributeError, OSError):
            pass


class CountingProvider:
    """Counts actual provider.generate invocations (= external HTTP attempts;
    the adapter performs no retries). A short-circuited /ask that never calls
    generate() is not counted as a model call."""

    def __init__(self, inner):
        self._inner = inner
        self.external_http_attempts = 0

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

    def generate(self, **kwargs):
        self.external_http_attempts += 1
        return self._inner.generate(**kwargs)


def validate_corpus(corpus: Path) -> dict:
    """Preflight: corpus must parse valid, be non-empty and be fully synthetic."""
    base = {
        "path": str(corpus),
        "document_count": 0,
        "synthetic_count": 0,
        "all_synthetic": False,
        "ok": False,
        "reason": None,
    }
    manifest = corpus / "manifest.json"
    if not manifest.is_file():
        return {**base, "reason": "拒绝调用：语料无效（缺少 manifest.json）"}
    from campus_assistant.corpus.parse import parse_manifest

    try:
        parsed = parse_manifest(manifest, corpus)
    except Exception as e:
        return {**base, "reason": f"拒绝调用：语料解析失败（{type(e).__name__}）"}
    docs = parsed.get("documents", [])
    synthetic = sum(
        1 for d in docs if (d.get("metadata") or {}).get("is_synthetic") is True
    )
    base.update({
        "document_count": len(docs),
        "synthetic_count": synthetic,
        "all_synthetic": bool(docs) and synthetic == len(docs),
    })
    if not parsed.get("valid", False):
        return {**base, "reason": "拒绝调用：语料无效（登记/解析校验未通过）"}
    if not docs:
        return {**base, "reason": "拒绝调用：语料无效（没有可解析文档）"}
    if not base["all_synthetic"]:
        return {**base, "reason": "拒绝调用：语料包含未标记 is_synthetic=true 的文档，本任务仅允许合成资料"}
    base["ok"] = True
    return base


def _resolve_config(provider) -> dict | None:
    """Actual provider config for the review summary — never plan values."""
    if provider is None:
        return None
    base_url = getattr(provider, "base_url", None)
    endpoint = None
    if isinstance(base_url, str) and base_url:
        from campus_assistant.qa.deepseek import chat_completions_url

        endpoint = chat_completions_url(base_url)
    return {
        "endpoint": endpoint,
        "model": getattr(provider, "model", None),
        "max_tokens": getattr(provider, "max_tokens", None),
        "provider_identity": getattr(provider, "provider_id", None),
    }


def _check_official_config(resolved: dict) -> dict:
    """CLI --live gate: only this task's authorized official values pass."""
    problems = []
    if resolved.get("endpoint") != OFFICIAL_TARGET:
        problems.append(f"endpoint 不是本任务授权的官方地址（已解析：{resolved.get('endpoint')}）")
    if resolved.get("model") != OFFICIAL_MODEL:
        problems.append(f"model 不是 {OFFICIAL_MODEL}（已解析：{resolved.get('model')}）")
    if resolved.get("max_tokens") != MAX_TOKENS:
        problems.append(f"max_tokens 不是 {MAX_TOKENS}（已解析：{resolved.get('max_tokens')}）")
    return {"ok": not problems, "reason": "；".join(problems) or None}


def _ask_body(question: dict, answer_mode: str) -> dict:
    body = {
        "query": question["query"],
        "top_k": 5,
        "mode": "bm25",
        "answer_mode": answer_mode,
    }
    if question.get("filters"):
        body["filters"] = question["filters"]
    return body


def _local_retrieval_record(client, question: dict) -> dict:
    """Extractive /ask over the question's own filters — local only."""
    r = client.post("/api/v1/ask", json=_ask_body(question, "extractive"))
    d = r.json()
    evidence = [
        {"evidence_id": e["evidence_id"], "chars": len(e["text"])}
        for e in d.get("evidence", [])
    ]
    total = sum(e["chars"] for e in evidence)
    return {
        "ask_status": d.get("status"),
        "evidence_state": d.get("evidence_state"),
        "evidence": evidence,
        "evidence_total_chars": total,
        "within_char_budget": total <= EVIDENCE_BUDGET_CHARS,
    }


def _preview(answer_body: dict | None, limit: int) -> dict:
    """Answer preview only — the sole truncated field in the record."""
    if not answer_body or not answer_body.get("paragraphs"):
        return {"text": None, "truncated": False, "limit": limit}
    text = "\n\n".join(p.get("text", "") for p in answer_body["paragraphs"])
    truncated = len(text) > limit
    return {"text": text[:limit], "truncated": truncated, "limit": limit}


def _default_emit(obj) -> None:
    """Human review display — flushed before any HTTP call."""
    print(json.dumps(obj, ensure_ascii=False, indent=2), file=sys.stderr, flush=True)


def _result_skeleton(*, live: bool, answer_preview_chars: int) -> dict:
    return {
        "mode": "live" if live else "dry-run (no network I/O)",
        "live_verified": False,
        "live_verified_note": "仅 Part C 逐条人工核对后由验收认定；进程退出 0 不等于 live_verified。",
        "external_model_calls": 0,
        "config_planned": {
            "target": OFFICIAL_TARGET,
            "model": OFFICIAL_MODEL,
            "max_tokens": MAX_TOKENS,
        },
        "config_resolved": None,
        "max_external_http_attempts": MAX_EXTERNAL_HTTP_ATTEMPTS,
        "retries": 0,
        "stop_on_first_technical_failure": True,
        "answer_preview_chars_limit": answer_preview_chars,
        "answer_preview_note": "仅答案预览截短；status/generation_meta/调用记录完整保留。预览截断≠模型截断。本参数不是 token/费用限制。",
        "preflight": {},
        "review_summary": None,
        "counters": {
            "local_retrieval_calls": 0,
            "ask_requests": 0,
            "external_http_attempts": 0,
        },
        "records": [],
        "errors": [],
        "exit_ok": False,
    }


def run_smoke(
    *,
    live: bool,
    corpus: Path,
    answer_preview_chars: int,
    full_answers_out: Path | None = None,
    provider_factory=None,
    require_official_config: bool = False,
    emit=None,
) -> dict:
    """Run preflight + dry-run retrieval + optional live calls.

    Returns the structured result; `exit_ok` maps to the process exit code
    (True → 0, False → 1). `require_official_config=True` (the CLI --live
    path) refuses any endpoint/model/max_tokens outside this task's
    authorized official values. `emit` receives the review summary before
    the first HTTP call (tests inject a recorder).
    """
    from campus_assistant.main import create_app
    from fastapi.testclient import TestClient

    say = emit or _default_emit
    out = _result_skeleton(live=live, answer_preview_chars=answer_preview_chars)
    errors = out["errors"]

    # --- Preflight 1: corpus must be valid, non-empty, fully synthetic ---
    corpus_check = validate_corpus(corpus)
    out["preflight"]["corpus_check"] = corpus_check
    if not corpus_check["ok"]:
        errors.append(corpus_check["reason"])
        say({"event": "preflight_failed", "errors": errors})
        return out

    # --- Preflight 2/3 (live): generator configured + actual config review ---
    counting = None
    resolved = None
    if live:
        factory = provider_factory
        if factory is None:
            from campus_assistant.qa.deepseek import provider_from_env

            factory = provider_from_env
        provider = factory()
        resolved = _resolve_config(provider)
        out["config_resolved"] = resolved
        if provider is None:
            out["preflight"]["generator_check"] = {
                "ok": False,
                "reason": "生成器未配置：需要 CAMPUS_GENERATOR=deepseek 且 DEEPSEEK_API_KEY 非空；本次未调用任何模型",
            }
            out["preflight"]["config_check"] = {"ok": False, "reason": "生成器未配置，无法核对实际配置"}
            errors.append(out["preflight"]["generator_check"]["reason"])
            say({"event": "preflight_failed", "errors": errors})
            return out
        out["preflight"]["generator_check"] = {"ok": True, "reason": None}
        if require_official_config:
            cfg = _check_official_config(resolved)
        else:
            cfg = {"ok": True, "reason": None, "note": "显式测试注入，仅跳过官方数值核对；语料与退出码规则照常"}
        out["preflight"]["config_check"] = cfg
        if not cfg["ok"]:
            errors.append("已拒绝调用：" + cfg["reason"])
            say({"event": "preflight_failed", "errors": errors})
            return out
        counting = CountingProvider(provider)
    else:
        out["preflight"]["generator_check"] = {
            "ok": True, "reason": None, "note": "dry-run 不需要生成器；未读取任何密钥值",
        }
        out["preflight"]["config_check"] = {
            "ok": True, "reason": None, "note": "dry-run 未构造 provider：仅展示计划配置，已解析配置为 null",
        }

    app = create_app(
        manifest_path=corpus / "manifest.json",
        corpus_root=corpus,
        answer_provider=counting,
    )
    client = TestClient(app)

    # --- Local retrieval (dry-run core) — always, no network ---
    for question in QUESTIONS:
        record = {
            "question_id": question["question_id"],
            "kind": question["kind"],
            "query": question["query"],
            "filters": question["filters"],
            "expectation": question["expectation"],
        }
        out["counters"]["local_retrieval_calls"] += 1
        record["local_retrieval"] = _local_retrieval_record(client, question)
        record["live_call"] = None
        out["records"].append(record)

    # --- Review summary: displayed and flushed BEFORE the first HTTP call ---
    out["review_summary"] = {
        "config_planned": out["config_planned"],
        "config_resolved": out["config_resolved"],
        "config_note": (
            "已解析配置来自实际 provider（可为测试注入）；计划配置为本任务授权的官方数值。"
            if live
            else "dry-run 无已解析配置（未构造 provider），仅计划配置。"
        ),
        "corpus": corpus_check,
        "questions": [
            {
                "question_id": r["question_id"],
                "query": r["query"],
                "filters": r["filters"],
                "evidence": r["local_retrieval"]["evidence"],
                "evidence_total_chars": r["local_retrieval"]["evidence_total_chars"],
            }
            for r in out["records"]
        ],
        "planned_max_external_http_attempts": MAX_EXTERNAL_HTTP_ATTEMPTS,
        "max_tokens_planned": MAX_TOKENS,
    }
    say({"event": "review_summary", "review_summary": out["review_summary"]})

    if not live:
        out["exit_ok"] = True
        return out

    # --- Live calls ---
    stopped = False
    for record in out["records"]:
        question = next(q for q in QUESTIONS if q["question_id"] == record["question_id"])
        if stopped:
            record["live_call"] = {
                "outcome_kind": "not_attempted",
                "http_success": None,
                "generation_success": False,
            }
            continue

        out["counters"]["ask_requests"] += 1
        attempts_before = counting.external_http_attempts
        body = _ask_body(question, "generated")
        r = client.post("/api/v1/ask", json=body)
        try:
            d = r.json()
        except ValueError:
            d = {}
        http_attempted = counting.external_http_attempts > attempts_before

        live_call: dict = {
            "request": body,
            "http_attempted": http_attempted,
            "ask_http_status_code": r.status_code,
            "ask_http_status_code_note": "本地 /ask 接口状态，非供应商原始 HTTP 状态；未知供应商状态不猜测",
        }
        if r.status_code == 200 and d.get("status") == "generated":
            live_call.update({
                "outcome_kind": "generated",
                "http_success": True,
                "generation_success": True,
                "ask_status": "generated",
                "generation_meta": d.get("generation_meta"),
                "answer_preview": _preview(d.get("answer"), answer_preview_chars),
            })
        elif r.status_code == 200 and d.get("status") == "insufficient_evidence":
            live_call.update({
                "outcome_kind": "insufficient_evidence" if http_attempted else "short_circuit_no_evidence",
                "http_success": True if http_attempted else None,
                "generation_success": False,
                "ask_status": "insufficient_evidence",
                "generation_meta": d.get("generation_meta"),
                "insufficient_reason": d.get("insufficient_reason"),
                "answer_preview": {"text": None, "truncated": False, "limit": answer_preview_chars},
            })
        else:
            live_call.update({
                "outcome_kind": "technical_failure",
                "http_success": False if r.status_code >= 400 else None,
                "generation_success": False,
                "ask_status": d.get("status"),
                "error_code": d.get("code"),
                "error": d.get("message") or f"本地 /ask HTTP {r.status_code}",
                "answer_preview": {"text": None, "truncated": False, "limit": answer_preview_chars},
            })

        record["live_call"] = live_call
        if live_call["outcome_kind"] == "generated":
            out.setdefault("_full_answers", []).append({
                "question_id": question["question_id"],
                "answer": d.get("answer"),
            })
        if live_call["outcome_kind"] == "technical_failure":
            stopped = True  # first technical failure stops immediately

    out["counters"]["external_http_attempts"] = counting.external_http_attempts
    out["external_model_calls"] = counting.external_http_attempts

    if out.get("_full_answers") and full_answers_out is not None:
        full_answers_out.write_text(
            json.dumps({
                "note": "完整回答文本，供人工核对；与主输出中的预览截断无关，不代表模型截断。",
                "answers": out["_full_answers"],
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        out["full_answers_file"] = str(full_answers_out)
    elif out.get("_full_answers"):
        out["full_answers_file"] = None
        out["full_answers_note"] = "本次未提供 --full-answers-out，完整回答未另存。"
    out.pop("_full_answers", None)

    out["exit_ok"] = not any(
        r["live_call"] and r["live_call"]["outcome_kind"] == "technical_failure"
        for r in out["records"]
    )
    return out


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_streams()
    parser = argparse.ArgumentParser(
        description="DeepSeek 冒烟（默认 dry-run：本地检索 + 审查摘要，无网络）"
    )
    parser.add_argument("--live", action="store_true", help="真实官方调用（须用户事先明确授权）")
    parser.add_argument("--corpus", default="examples/parse-corpus")
    parser.add_argument("--answer-preview-chars", type=int, default=400,
                        help="答案预览截短上限（1—2000，仅预览，不是 token/费用限制）")
    parser.add_argument("--full-answers-out", default=None,
                        help="可选：完整回答另存的本地 JSON 路径（供人工核对）")
    args = parser.parse_args(argv)

    if not (ANSWER_PREVIEW_CHARS_MIN <= args.answer_preview_chars <= ANSWER_PREVIEW_CHARS_MAX):
        parser.error(
            f"--answer-preview-chars 必须在 {ANSWER_PREVIEW_CHARS_MIN}—{ANSWER_PREVIEW_CHARS_MAX} 之间"
            "（仅限制答案预览长度，不是 token/费用限制）"
        )

    result = run_smoke(
        live=args.live,
        corpus=Path(args.corpus),
        answer_preview_chars=args.answer_preview_chars,
        full_answers_out=Path(args.full_answers_out) if args.full_answers_out else None,
        require_official_config=args.live,  # CLI --live enforces official values
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["exit_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
