"""Tests for the DeepSeekAnswerProvider (T013) against a loopback mock.

The mock exists only inside this test module — it is not part of the
product runtime and its outputs are NOT real DeepSeek answers. Coverage is
focused: valid answer, insufficient, bad JSON, one illegal citation,
truncation, timeout/HTTP failure mapping, config-off extractive fallback,
and request shape (model / json mode / actual evidence).
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from campus_assistant.main import create_app
from campus_assistant.qa.deepseek import (
    DeepSeekAnswerProvider,
    chat_completions_url,
    provider_from_env,
)

TEST_KEY = "sk-test-placeholder"  # placeholder only — never a real key


class MockDeepSeek:
    """Loopback mock of POST /chat/completions for tests only."""

    def __init__(self, respond):
        self.received: list[dict] = []
        self.respond = respond
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length))
                outer.received.append({
                    "path": self.path,
                    "request": req,
                    "auth_header_present": self.headers.get("Authorization", "").startswith("Bearer "),
                })
                status, resp = outer.respond(req)
                data = json.dumps(resp).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self):
        self._server.shutdown()
        self._server.server_close()


def _chat_response(content, *, finish_reason="stop", model="deepseek-flash", rid="mock-req-1"):
    return {
        "id": rid,
        "model": model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": finish_reason}
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 40, "total_tokens": 160},
    }


def _write_corpus(tmp_path: Path) -> Path:
    content = "缓考申请须经所在学院批准，附医院证明。补考成绩最高记为60分。"
    fpath = tmp_path / "doc.txt"
    fpath.write_text(content, encoding="utf-8")
    sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "documents": [{
            "document_id": "doc-1", "policy_group_id": "g", "title": "缓考办法",
            "source_url": "https://example.org/p", "source_site": "测试站",
            "local_path": "doc.txt", "sha256": sha, "version_label": "v1",
            "published_at": "2025-01-01", "effective_from": "2025-03-01", "effective_to": None,
            "scope": {"campus": [], "student_type": [], "admission_years": []},
            "is_synthetic": True,
        }],
    }
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return mp


def _client(tmp_path: Path, provider) -> TestClient:
    mp = _write_corpus(tmp_path)
    return TestClient(
        create_app(manifest_path=mp, corpus_root=tmp_path, answer_provider=provider),
        raise_server_exceptions=False,
    )


def _ask(client, **kw):
    body = {"query": "缓考申请需要什么材料", "top_k": 5, "mode": "bm25", "answer_mode": "generated"}
    body.update(kw)
    return client.post("/api/v1/ask", json=body)


@pytest.fixture()
def mock_server():
    servers = []

    def start(respond):
        s = MockDeepSeek(respond)
        servers.append(s)
        return s

    yield start
    for s in servers:
        s.close()


class TestValidAnswerChain:
    def test_full_chain_and_request_shape(self, tmp_path, mock_server):
        answer = {
            "type": "answer",
            "paragraphs": [{"text": "缓考申请须经所在学院批准。", "evidence_ids": ["E1"]}],
        }
        mock = mock_server(lambda req: (200, _chat_response(json.dumps(answer, ensure_ascii=False))))
        provider = DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url + "/", trust_env=False)
        client = _client(tmp_path, provider)

        st = client.get("/api/v1/ask/status").json()
        assert st["generator_configured"] is True
        assert st["generator_identity"] == "deepseek:deepseek-flash"

        r = _ask(client)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "generated"
        assert d["answer"]["paragraphs"][0]["evidence_ids"] == ["E1"]
        assert d["answer"]["paragraphs"][0]["citations"][0]["evidence_id"] == "E1"

        # exactly one HTTP call, correct path rule (no duplicated /v1)
        assert len(mock.received) == 1
        req = mock.received[0]
        assert req["path"] == "/chat/completions"
        assert req["auth_header_present"] is True
        body = req["request"]
        assert body["model"] == "deepseek-flash"
        assert body["stream"] is False
        assert body["response_format"] == {"type": "json_object"}
        assert body["thinking"] == {"type": "disabled"}
        assert body["max_tokens"] == 1500
        # system prompt carries the json structure example; user message
        # carries only the actual evidence text (no gold)
        system, user = body["messages"][0]["content"], body["messages"][1]["content"]
        assert "json" in system and "evidence_ids" in system
        assert "缓考申请须经所在学院批准" in user and "【E1】" in user

        # audit metadata: real response fields + config, never fabricated
        meta = d["generation_meta"]
        assert meta["model"] == "deepseek-flash"
        assert meta["request_id"] == "mock-req-1"
        assert meta["usage"]["total_tokens"] == 160
        assert meta["max_tokens"] == 1500
        assert meta["latency_ms"] >= 0
        assert meta["finish_reason"] == "stop"

    def test_insufficient_evidence(self, tmp_path, mock_server):
        result = {"type": "insufficient_evidence", "reason": "摘录未覆盖证明材料"}
        mock = mock_server(lambda req: (200, _chat_response(json.dumps(result, ensure_ascii=False))))
        client = _client(tmp_path, DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, trust_env=False))
        d = _ask(client).json()
        assert d["status"] == "insufficient_evidence"
        assert d["answer"] is None
        assert d["insufficient_reason"] == "摘录未覆盖证明材料"


class TestFailureMapping:
    def test_bad_json_content(self, tmp_path, mock_server):
        mock = mock_server(lambda req: (200, _chat_response("这不是 json")))
        client = _client(tmp_path, DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, trust_env=False))
        r = _ask(client)
        assert r.status_code == 502
        d = r.json()
        assert d["code"] == "GENERATOR_ERROR"
        assert "json" in d["message"]
        assert TEST_KEY not in d["message"]  # never leak the key
        assert "answer" not in d

    def test_illegal_citation_rejected(self, tmp_path, mock_server):
        answer = {"type": "answer", "paragraphs": [{"text": "结论", "evidence_ids": ["E99"]}]}
        mock = mock_server(lambda req: (200, _chat_response(json.dumps(answer))))
        client = _client(tmp_path, DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, trust_env=False))
        r = _ask(client)
        assert r.status_code == 502
        assert r.json()["code"] == "GENERATOR_INVALID_OUTPUT"

    def test_truncation_not_shown_as_complete(self, tmp_path, mock_server):
        mock = mock_server(lambda req: (200, _chat_response('{"type": "answer', finish_reason="length")))
        client = _client(tmp_path, DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, trust_env=False))
        r = _ask(client)
        assert r.status_code == 502
        assert "截断" in r.json()["message"]

    def test_empty_content(self, tmp_path, mock_server):
        mock = mock_server(lambda req: (200, _chat_response("")))
        client = _client(tmp_path, DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, trust_env=False))
        r = _ask(client)
        assert r.status_code == 502
        assert "空内容" in r.json()["message"]

    def test_http_500_mapped_without_retry(self, tmp_path, mock_server):
        mock = mock_server(lambda req: (500, {"error": "internal"}))
        client = _client(tmp_path, DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, trust_env=False))
        r = _ask(client)
        assert r.status_code == 502
        d = r.json()
        assert "HTTP 500" in d["message"]
        assert TEST_KEY not in d["message"]
        assert len(mock.received) == 1  # no automatic retry

    def test_timeout_mapped(self, tmp_path, mock_server):
        def slow(req):
            time.sleep(1.0)
            return (200, _chat_response("{}"))

        mock = mock_server(slow)
        provider = DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, timeout=0.2, trust_env=False)
        client = _client(tmp_path, provider)
        r = _ask(client)
        assert r.status_code == 502
        assert "超时" in r.json()["message"]

    def test_search_still_works_after_generator_error(self, tmp_path, mock_server):
        mock = mock_server(lambda req: (500, {"error": "internal"}))
        client = _client(tmp_path, DeepSeekAnswerProvider(TEST_KEY, base_url=mock.url, trust_env=False))
        assert _ask(client).status_code == 502
        s = client.post("/api/v1/search", json={"query": "缓考申请"})
        assert s.status_code == 200 and len(s.json()["hits"]) > 0


class TestConfig:
    def test_default_off_keeps_extractive(self, tmp_path):
        assert provider_from_env({}) is None
        # explicit enable but incomplete config → still off
        assert provider_from_env({"CAMPUS_GENERATOR": "deepseek"}) is None
        client = _client(tmp_path, None)
        d = _ask(client, answer_mode="extractive").json()
        assert d["status"] == "evidence_only" and d["evidence"]
        r = _ask(client, answer_mode="generated")
        assert r.status_code == 503 and r.json()["code"] == "GENERATOR_NOT_CONFIGURED"

    def test_explicit_enable_with_complete_config(self):
        p = provider_from_env({
            "CAMPUS_GENERATOR": "deepseek",
            "DEEPSEEK_API_KEY": TEST_KEY,
        })
        assert p is not None
        assert p.model == "deepseek-flash"
        assert p.provider_id == "deepseek:deepseek-flash"
        p2 = provider_from_env({
            "CAMPUS_GENERATOR": "deepseek",
            "DEEPSEEK_API_KEY": TEST_KEY,
            "DEEPSEEK_BASE_URL": "http://127.0.0.1:9",
            "DEEPSEEK_MODEL": "deepseek-flash",
        })
        assert p2.max_tokens == 1500 and p2.timeout == 30.0

    def test_url_join_rule(self):
        assert chat_completions_url("https://api.deepseek.com") == "https://api.deepseek.com/chat/completions"
        assert chat_completions_url("https://api.deepseek.com/") == "https://api.deepseek.com/chat/completions"
        assert chat_completions_url("http://127.0.0.1:8765") == "http://127.0.0.1:8765/chat/completions"
