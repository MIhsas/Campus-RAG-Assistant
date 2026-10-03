"""Real-model applicability filter API demo (T011).

Builds the app with the real local BGE model over examples/filter-demo,
then runs the same query under different filters (admission year / as-of
date / campus) through the real FastAPI endpoints. Verifies that document
encoding happens once at app build — repeated queries never re-encode the
corpus. Output: UTF-8 JSON on stdout.

Usage (from step2_code/backend):
    .venv\\Scripts\\python.exe scripts\\demo-filter-search.py ^
        --model-path models\\bge-small-zh-v1.5 --corpus examples\\filter-demo
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
    parser = argparse.ArgumentParser(description="筛选 API 真实模型演示")
    parser.add_argument("--model-path", default="models/bge-small-zh-v1.5")
    parser.add_argument("--corpus", default="examples/filter-demo")
    parser.add_argument("--query", default="缓考申请")
    parser.add_argument("--mode", default="hybrid", choices=["bm25", "dense", "hybrid"])
    args = parser.parse_args(argv)

    # Count document encodings — must stay at 1 across repeated queries.
    from campus_assistant.retrieval import embedding as emb_mod

    orig_encode = emb_mod.EmbeddingService.encode_documents
    calls = {"encode_documents": 0}

    def counting_encode(self, texts):
        calls["encode_documents"] += 1
        return orig_encode(self, texts)

    emb_mod.EmbeddingService.encode_documents = counting_encode

    try:
        from campus_assistant.main import create_app
        from fastapi.testclient import TestClient

        corpus = Path(args.corpus)
        app = create_app(
            manifest_path=corpus / "manifest.json",
            corpus_root=corpus,
            embedding_model_path=args.model_path,
        )
        client = TestClient(app)

        status = client.get("/api/v1/search/status").json()

        scenarios = [
            ("no-filters", None),
            ("year-2024", {"admission_year": 2024}),
            ("year-2025", {"admission_year": 2025}),
            ("as-of-2024-10-01", {"as_of_date": "2024-10-01"}),
            ("as-of-2025-09-10", {"as_of_date": "2025-09-10"}),
            (
                "chengdu-2024-as-of-2025-09-10",
                {"campus": "成都校区", "admission_year": 2024, "as_of_date": "2025-09-10"},
            ),
        ]

        results = []
        for name, filters in scenarios:
            body = {"query": args.query, "top_k": 10, "mode": args.mode}
            if filters:
                body["filters"] = filters
            r = client.post("/api/v1/search", json=body)
            d = r.json()
            results.append({
                "scenario": name,
                "request": body,
                "status_code": r.status_code,
                "hits": [
                    {
                        "rank": h["rank"],
                        "document_id": h["chunk"]["document_id"],
                        "score": h["score"],
                    }
                    for h in d.get("hits", [])
                ],
                "filters": d.get("filters"),
                "filter_summary": d.get("filter_summary"),
            })

        # Repeat one query — corpus must not be re-encoded.
        repeat_body = {
            "query": args.query, "top_k": 10, "mode": args.mode,
            "filters": {"admission_year": 2024},
        }
        r_repeat = client.post("/api/v1/search", json=repeat_body)
        repeat_hits = [h["chunk"]["document_id"] for h in r_repeat.json().get("hits", [])]

        out = {
            "demo": "T011 filter API demo (real local BGE over synthetic corpus)",
            "corpus": args.corpus,
            "model_path_arg": args.model_path,
            "mode": args.mode,
            "query": args.query,
            "status": {
                "available_modes": status.get("available_modes"),
                "embedding_model": status.get("embedding_model"),
                "embedding_model_revision": status.get("embedding_model_revision"),
                "embedding_max_seq_length": status.get("embedding_max_seq_length"),
                "truncated_chunk_count": status.get("truncated_chunk_count"),
                "embedding_error": status.get("embedding_error"),
                "filter_options": status.get("filter_options"),
                "document_count": status.get("document_count"),
                "chunk_count": status.get("chunk_count"),
            },
            "encode_documents_calls": calls["encode_documents"],
            "scenarios": results,
            "repeat_query": {
                "request": repeat_body,
                "hit_document_ids": repeat_hits,
                "encode_documents_calls_after_repeat": calls["encode_documents"],
            },
            "notes": [
                "语料为合成测试资料，不代表四川农业大学真实政策。",
                "encode_documents_calls 必须为 1：正文向量在应用创建时批量构建，重复查询只编码 query。",
                "无匹配场景的 filters 回显与提交一致，不会悄悄取消条件。",
            ],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    finally:
        emb_mod.EmbeddingService.encode_documents = orig_encode


if __name__ == "__main__":
    sys.exit(main())
