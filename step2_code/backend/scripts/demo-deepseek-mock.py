"""Loopback mock integration demo for the DeepSeek adapter (T013).

Runs ONE full chain: /ask → DeepSeekAnswerProvider → local HTTP → JSON
parse → citation validation → API response, against an in-process loopback
mock of POST /chat/completions. The mock lives only in this test entry
point — it is NOT part of the product runtime, there is no user-facing
fake-model switch, and its output is NOT a real DeepSeek answer.

Uses a placeholder test key and trust_env=False (direct loopback). No
external network call is made. Output: UTF-8 JSON on stdout.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-deepseek-mock.py --corpus examples\\parse-corpus
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TEST_KEY = "sk-test-placeholder"  # placeholder only — never a real key


def _ensure_utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") == "utf8":
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
    except (AttributeError, OSError):
        pass


def _start_mock():
    """Loopback mock: replies citing the E-ids found in the request."""
    received: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length))
            received.append({
                "path": self.path,
                "request": req,
                "auth_header_present": self.headers.get("Authorization", "").startswith("Bearer "),
            })
            user = req["messages"][1]["content"]
            ev_ids = re.findall(r"【(E\d+)】", user)
            cite = ev_ids[0] if ev_ids else "E1"
            body = {
                "id": "mock-req-001",
                "model": req.get("model", "deepseek-flash"),
                "choices": [{
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "type": "answer",
                            "paragraphs": [{
                                "text": "【模拟输出，非真实 DeepSeek 回答】原文摘录显示缓考申请须经所在学院批准并附证明。",
                                "evidence_ids": [cite],
                            }],
                        }, ensure_ascii=False),
                    },
                }],
                "usage": {"prompt_tokens": 210, "completion_tokens": 42, "total_tokens": 252},
            }
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, received


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="DeepSeek 适配器 loopback mock 集成演示")
    parser.add_argument("--corpus", default="examples/parse-corpus")
    parser.add_argument("--query", default="缓考申请需要什么材料")
    args = parser.parse_args(argv)

    from campus_assistant.main import create_app
    from campus_assistant.qa.deepseek import DeepSeekAnswerProvider
    from fastapi.testclient import TestClient

    server, received = _start_mock()
    mock_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        provider = DeepSeekAnswerProvider(
            TEST_KEY, base_url=mock_url, trust_env=False  # loopback: bypass system proxy
        )
        corpus = Path(args.corpus)
        app = create_app(
            manifest_path=corpus / "manifest.json",
            corpus_root=corpus,
            answer_provider=provider,
        )
        client = TestClient(app)

        status = client.get("/api/v1/ask/status").json()
        body = {
            "query": args.query,
            "top_k": 5,
            "mode": "bm25",
            "answer_mode": "generated",
            "filters": {"campus": "成都校区", "admission_year": 2023, "as_of_date": "2026-09-22"},
        }
        r = client.post("/api/v1/ask", json=body)
        d = r.json()

        checks = []

        def check(name, ok, detail=""):
            checks.append({"check": name, "passed": bool(ok), "detail": detail})

        check("http_status_200", r.status_code == 200, f"status={r.status_code}")
        check("status_generated", d.get("status") == "generated", str(d.get("status")))
        para = (d.get("answer") or {}).get("paragraphs", [{}])[0]
        sent_ids = [e["evidence_id"] for e in d.get("evidence", [])]
        check("citation_within_sent_evidence",
              set(para.get("evidence_ids", [])) <= set(sent_ids),
              f"para={para.get('evidence_ids')} sent={sent_ids}")
        cites = para.get("citations", [])
        check("citation_resolved_by_service",
              bool(cites) and cites[0].get("preview_url", "").startswith("/preview#"),
              cites[0].get("preview_url", "") if cites else "")
        meta = d.get("generation_meta") or {}
        check("audit_metadata_present",
              meta.get("max_tokens") == 1500 and meta.get("latency_ms", -1) >= 0,
              json.dumps({k: meta.get(k) for k in ("model", "request_id", "usage", "latency_ms", "max_tokens")}, ensure_ascii=False))
        req = received[0]["request"] if received else {}
        check("request_model_json_mode",
              req.get("model") == "deepseek-flash"
              and req.get("stream") is False
              and req.get("response_format") == {"type": "json_object"}
              and req.get("thinking") == {"type": "disabled"},
              "model/stream/response_format/thinking")
        check("single_http_call", len(received) == 1, f"calls={len(received)}")

        out = {
            "demo": "T013 DeepSeek adapter loopback-mock integration (ONE full chain)",
            "evidence_kind": "loopback mock — NOT a real DeepSeek answer; mock exists only in this script entry",
            "external_model_calls": 0,
            "live_verified": False,
            "corpus": args.corpus,
            "chain": "/ask → DeepSeekAnswerProvider → local HTTP → JSON parse → citation validation → response",
            "provider_identity": status.get("generator_identity"),
            "mock_request_summary": {
                "path": received[0]["path"] if received else None,
                "model": req.get("model"),
                "stream": req.get("stream"),
                "response_format": req.get("response_format"),
                "thinking": req.get("thinking"),
                "max_tokens": req.get("max_tokens"),
                "auth_header_present": received[0]["auth_header_present"] if received else False,
                "messages": [
                    {"role": m.get("role"), "content_chars": len(m.get("content", ""))}
                    for m in req.get("messages", [])
                ],
            },
            "ask_request": body,
            "ask_response": d,
            "checks": checks,
            "notes": [
                "模拟回答文本带“【模拟输出】”标记，不得当作真实 DeepSeek 回答。",
                "trust_env=False 仅用于 loopback 直连（本机系统代理会拦截 127.0.0.1）；真实调用默认尊重系统代理。",
                "密钥为占位值，未发送任何外部请求。",
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if all(c["passed"] for c in checks) else 1
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
