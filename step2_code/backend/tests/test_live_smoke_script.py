"""Tests for the T014 live smoke script recording and preflight rules.

Covers T013-R1 recording fixes (non-zero exit on failure, complete audit
with preview-only truncation, separate ask/HTTP counters) and T014-R1
preflight fixes (synthetic-corpus gate before any provider call, missing
config exits non-zero, review summary reflects the ACTUAL provider config
and is emitted before the first call). Loopback/fake only — not a real
DeepSeek demo, no external calls.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "live-smoke-deepseek.py"
_spec = importlib.util.spec_from_file_location("live_smoke_deepseek", _SCRIPT)
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)

from campus_assistant.qa.deepseek import DeepSeekAnswerProvider  # noqa: E402

TEST_KEY = "sk-test-placeholder"
CORPUS = Path(__file__).resolve().parents[1] / "examples" / "parse-corpus"


class _Mock:
    def __init__(self, respond):
        self.received = []
        self.respond = respond
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                outer.received.append(True)
                status, resp = outer.respond()
                data = json.dumps(resp).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def close(self):
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture()
def mock():
    servers = []

    def start(respond):
        s = _Mock(respond)
        servers.append(s)
        return s

    yield start
    for s in servers:
        s.close()


class FakeProvider:
    """In-memory fake — proves preflight/gate behavior only."""

    provider_id = "fake:test"

    def __init__(self, base_url="https://api.deepseek.com", model="deepseek-flash",
                 max_tokens=1500, on_call=None):
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.calls = 0
        self._on_call = on_call

    def generate(self, **kwargs):
        self.calls += 1
        if self._on_call:
            self._on_call()
        return {"type": "insufficient_evidence", "reason": "fake 判断材料不足"}


def _write_corpus(path: Path, *, is_synthetic: bool = True, valid: bool = True) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    content = "缓考申请须经所在学院批准，附医院证明。补考成绩最高记为60分。"
    fpath = path / "doc.txt"
    fpath.write_text(content, encoding="utf-8")
    sha = hashlib.sha256(fpath.read_bytes()).hexdigest() if valid else "0" * 64
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "doc-1", "policy_group_id": "g", "title": "缓考办法",
            "source_url": "https://example.org/p", "source_site": "测试站",
            "local_path": "doc.txt", "sha256": sha, "version_label": "v1",
            "published_at": "2025-01-01", "effective_from": "2025-03-01", "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": is_synthetic,
        }],
    }
    (path / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def _ok_answer():
    return (200, {
        "id": "mock-req-001",
        "model": "deepseek-flash",
        "choices": [{
            "index": 0,
            "finish_reason": "stop",
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "type": "answer",
                    "paragraphs": [{"text": "缓考申请须经所在学院批准，并报教务处备案。" * 5, "evidence_ids": ["E1"]}],
                }, ensure_ascii=False),
            },
        }],
        "usage": {"prompt_tokens": 200, "completion_tokens": 60, "total_tokens": 260},
    })


# --- T013-R1 recording rules (kept) ---

def test_live_success_recording_and_zero_exit(tmp_path, mock):
    server = mock(lambda: _ok_answer())
    provider = lambda: DeepSeekAnswerProvider(TEST_KEY, base_url=server.url, trust_env=False)
    out_file = tmp_path / "answers-full.json"
    result = smoke.run_smoke(
        live=True, corpus=CORPUS, answer_preview_chars=10,
        full_answers_out=out_file, provider_factory=provider,
    )
    assert result["exit_ok"] is True
    assert result["live_verified"] is False  # script never self-certifies
    c = result["counters"]
    assert c["ask_requests"] == 2
    assert c["local_retrieval_calls"] == 2
    # Current parse-corpus retrieval: Q2 (宿舍门禁) has NO candidates → local
    # short-circuit without provider invocation. That is the honest record —
    # NOT a verified model refusal. external attempts stay below /ask count.
    assert c["external_http_attempts"] == 1
    kinds = [r["live_call"]["outcome_kind"] for r in result["records"]]
    assert kinds == ["generated", "short_circuit_no_evidence"]

    rec = result["records"][0]["live_call"]
    assert rec["outcome_kind"] == "generated"
    assert rec["http_success"] is True and rec["generation_success"] is True
    # audit fields complete and independent — never truncated
    meta = rec["generation_meta"]
    assert meta["model"] == "deepseek-flash"
    assert meta["request_id"] == "mock-req-001"
    assert meta["usage"]["total_tokens"] == 260
    assert meta["finish_reason"] == "stop"
    # local /ask status is labeled as such — not the vendor's raw status
    assert "ask_http_status_code" in rec
    assert "http_status_code" not in rec
    # only the answer preview is truncated, with an explicit flag
    assert rec["answer_preview"]["truncated"] is True
    assert len(rec["answer_preview"]["text"]) == 10
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(saved["answers"][0]["answer"]["paragraphs"][0]["text"]) > 10
    assert "不代表模型截断" in saved["note"]


def test_live_http_failure_nonzero_exit_and_stops(mock):
    server = mock(lambda: (500, {"error": "internal"}))
    provider = lambda: DeepSeekAnswerProvider(TEST_KEY, base_url=server.url, trust_env=False)
    result = smoke.run_smoke(
        live=True, corpus=CORPUS, answer_preview_chars=400, provider_factory=provider,
    )
    assert result["exit_ok"] is False  # failures exit non-zero
    assert result["external_model_calls"] == 1
    c = result["counters"]
    assert c["ask_requests"] == 1      # stopped before the second question
    assert c["external_http_attempts"] == 1
    kinds = [r["live_call"]["outcome_kind"] for r in result["records"]]
    assert kinds == ["technical_failure", "not_attempted"]
    first = result["records"][0]["live_call"]
    assert first["http_success"] is False
    assert first["generation_success"] is False
    assert "HTTP 500" in first["error"]


def test_dry_run_local_only_summary():
    result = smoke.run_smoke(live=False, corpus=CORPUS, answer_preview_chars=400)
    assert result["exit_ok"] is True
    assert result["mode"].startswith("dry-run")
    assert result["counters"]["ask_requests"] == 0
    assert result["counters"]["external_http_attempts"] == 0
    assert result["external_model_calls"] == 0
    # planned vs resolved config are distinct fields
    assert result["config_planned"]["target"] == "https://api.deepseek.com/chat/completions"
    assert result["config_planned"]["model"] == "deepseek-flash"
    assert result["config_resolved"] is None  # dry-run never builds a provider
    for r in result["records"]:
        assert r["local_retrieval"]["within_char_budget"] is True
        assert r["live_call"] is None


# --- T014-R1 preflight rules ---

def test_non_synthetic_corpus_blocks_provider_before_calls(tmp_path):
    corpus = _write_corpus(tmp_path / "realish", is_synthetic=False)
    fake = FakeProvider()
    result = smoke.run_smoke(
        live=True, corpus=corpus, answer_preview_chars=400,
        provider_factory=lambda: fake, require_official_config=True,
    )
    assert result["exit_ok"] is False
    assert fake.calls == 0
    assert result["external_model_calls"] == 0
    assert result["counters"]["local_retrieval_calls"] == 0  # before ANY call
    reason = result["preflight"]["corpus_check"]["reason"]
    assert "is_synthetic" in reason
    assert any("合成" in e or "is_synthetic" in e for e in result["errors"])


def test_invalid_corpus_exits_nonzero_even_in_dryrun(tmp_path):
    corpus = _write_corpus(tmp_path / "bad", valid=False)  # sha mismatch
    result = smoke.run_smoke(live=False, corpus=corpus, answer_preview_chars=400)
    assert result["exit_ok"] is False
    assert result["errors"] and "语料无效" in result["errors"][0]

    empty = tmp_path / "empty"
    empty.mkdir()
    result2 = smoke.run_smoke(live=False, corpus=empty, answer_preview_chars=400)
    assert result2["exit_ok"] is False
    assert "manifest" in result2["errors"][0]


def test_live_missing_config_exits_nonzero():
    result = smoke.run_smoke(
        live=True, corpus=CORPUS, answer_preview_chars=400,
        provider_factory=lambda: None, require_official_config=True,
    )
    assert result["exit_ok"] is False
    assert any("未配置" in e for e in result["errors"])
    assert result["external_model_calls"] == 0
    assert result["counters"]["local_retrieval_calls"] == 0


def test_review_summary_shows_actual_config_before_calls():
    events = []
    fake = FakeProvider(
        base_url="http://127.0.0.1:9", model="local-test-model", max_tokens=777,
        on_call=lambda: events.append(("generate",)),
    )
    result = smoke.run_smoke(
        live=True, corpus=CORPUS, answer_preview_chars=400,
        provider_factory=lambda: fake, require_official_config=False,
        emit=lambda obj: events.append(("emit", obj)),
    )
    # summary emitted before the first provider call
    assert events and events[0][0] == "emit"
    assert events[0][1]["event"] == "review_summary"
    emit_idx = next(i for i, e in enumerate(events) if e[0] == "emit")
    gen_idx = next(i for i, e in enumerate(events) if e[0] == "generate")
    assert emit_idx < gen_idx
    # summary reflects the ACTUAL provider config, not the planned values
    resolved = result["config_resolved"]
    assert resolved["endpoint"] == "http://127.0.0.1:9/chat/completions"
    assert resolved["model"] == "local-test-model"
    assert resolved["max_tokens"] == 777
    assert result["config_planned"]["model"] == "deepseek-flash"
    assert result["review_summary"]["config_resolved"] == resolved
    assert result["exit_ok"] is True


def test_official_config_gate_refuses_mismatch_before_calls():
    fake = FakeProvider(base_url="http://127.0.0.1:9", model="local-test-model", max_tokens=777)
    result = smoke.run_smoke(
        live=True, corpus=CORPUS, answer_preview_chars=400,
        provider_factory=lambda: fake, require_official_config=True,
    )
    assert result["exit_ok"] is False
    assert fake.calls == 0
    assert result["external_model_calls"] == 0
    assert any("已拒绝调用" in e for e in result["errors"])
    cfg = result["preflight"]["config_check"]
    assert cfg["ok"] is False and "endpoint" in cfg["reason"] and "model" in cfg["reason"]


def test_official_config_gate_passes_matching_values():
    fake = FakeProvider()  # official-looking values
    result = smoke.run_smoke(
        live=True, corpus=CORPUS, answer_preview_chars=400,
        provider_factory=lambda: fake, require_official_config=True,
    )
    assert result["exit_ok"] is True
    assert fake.calls >= 1  # Q1 reaches the provider
    assert result["preflight"]["config_check"]["ok"] is True
