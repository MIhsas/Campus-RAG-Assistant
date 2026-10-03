"""Real extractive /ask API demo (T012).

Runs the real app (local corpus, BM25 — no generation model) through the
actual FastAPI endpoints: ask status, extractive evidence organizing with
and without filters, and the generated-mode 503 when no provider is
configured. No external model is called. Output: UTF-8 JSON on stdout.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-ask.py --corpus examples\\parse-corpus
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path


def _ensure_utf8_stdout() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") == "utf8":
        return
    try:
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", line_buffering=True
        )
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="extractive /ask API 演示")
    parser.add_argument("--corpus", default="examples/parse-corpus")
    args = parser.parse_args(argv)

    from campus_assistant.main import create_app
    from fastapi.testclient import TestClient

    corpus = Path(args.corpus)
    app = create_app(manifest_path=corpus / "manifest.json", corpus_root=corpus)
    client = TestClient(app)

    status = client.get("/api/v1/ask/status").json()

    scenarios = []

    def record(name, response, body=None):
        d = response.json()
        scenarios.append({
            "scenario": name,
            "request": body,
            "status_code": response.status_code,
            "response": d,
        })

    record("status", client.get("/api/v1/ask/status"))

    body = {"query": "缓考申请需要什么材料", "top_k": 5, "mode": "bm25", "answer_mode": "extractive"}
    record("extractive-no-filters", client.post("/api/v1/ask", json=body), body)

    body2 = {
        "query": "缓考申请需要什么材料", "top_k": 5, "mode": "bm25", "answer_mode": "extractive",
        "filters": {"campus": "成都校区", "admission_year": 2023, "as_of_date": "2026-09-22"},
    }
    record("extractive-filtered-2023", client.post("/api/v1/ask", json=body2), body2)

    body3 = {
        "query": "缓考申请需要什么材料", "top_k": 5, "mode": "bm25", "answer_mode": "extractive",
        "filters": {"admission_year": 1900},
    }
    record("extractive-no-admissible-docs", client.post("/api/v1/ask", json=body3), body3)

    body4 = {"query": "缓考申请需要什么材料", "top_k": 5, "mode": "bm25", "answer_mode": "generated"}
    record("generated-not-configured", client.post("/api/v1/ask", json=body4), body4)

    out = {
        "demo": "T012 extractive /ask API demo (local corpus, BM25, no generation model)",
        "corpus": args.corpus,
        "notes": [
            "合成语料，不代表四川农业大学真实政策。",
            "answer_mode=extractive 只整理原文摘录，status=evidence_only、answer=null。",
            "generated 在未注入 AnswerProvider 时返回 503/GENERATOR_NOT_CONFIGURED，摘录不会伪装成生成答案。",
            "本演示未调用任何外部或付费模型。",
        ],
        "ask_status": {
            "answer_mode_default": status.get("answer_mode_default"),
            "answer_modes_available": status.get("answer_modes_available"),
            "generator_configured": status.get("generator_configured"),
            "corpus_status": status.get("corpus_status"),
        },
        "scenarios": scenarios,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
