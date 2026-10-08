"""T031 local API demo — user-selected single-file retrieval (real v1.1 pack).

Demonstrates the user-visible contract end to end (in-process ASGI client, no
external calls, no DeepSeek, no browser claimed):

1. document catalog (identity fields only);
2. same query restricted to the 2023 vs the 2026 transfer-major file —
   hits and preview links stay inside the selected document;
3. selected file excluded by a date condition -> no admissible evidence,
   no fallback to other files;
4. unknown document_id -> explicit 422;
5. /ask extractive honours the same source selection.

Output: docs/collaboration/submissions/T031/api-demo.json (path via --out).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402

from campus_assistant.main import create_app  # noqa: E402

MANIFEST = ROOT / "data/corpora/sicau-rag-pilot-v1.1/manifest.json"
DOC_2023_PREFIX = "d1fe991c"  # 本科生转专业实施办法（校教发[2023]1号）
DOC_2026_PREFIX = "5cb2ac21"  # 本科生转专业实施办法（校教发[2026]1号）
QUERY = "申请转专业必须符合哪些条件 课程要求"


def _pick(docs: list[dict], prefix: str) -> str:
    ids = [d["document_id"] for d in docs if d["document_id"].startswith(prefix)]
    assert len(ids) == 1, f"prefix {prefix} matched {len(ids)} documents"
    return ids[0]


def _trim_hits(hits: list[dict], n: int = 3) -> list[dict]:
    out = []
    for h in hits[:n]:
        out.append({
            "rank": h["rank"],
            "document_id": h["chunk"]["document_id"],
            "block_id": h["chunk"]["block_id"],
            "preview_url": h["preview_url"],
            "title": (h["chunk"].get("metadata") or {}).get("title"),
            "version_label": (h["chunk"].get("metadata") or {}).get("version_label"),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/collaboration/submissions/T031/api-demo.json"))
    ap.add_argument("--model-path", default=str(BACKEND / "models/bge-small-zh-v1.5"))
    args = ap.parse_args()

    app = create_app(
        manifest_path=MANIFEST,
        corpus_root=MANIFEST.parent,
        embedding_model_path=args.model_path if Path(args.model_path).exists() else None,
    )
    c = TestClient(app, raise_server_exceptions=False)
    demo: dict = {"note": "T031 本地 API 演示（真实包 v1.1，in-process ASGI client；零外部模型调用）",
                  "query": QUERY, "steps": []}

    # 1. catalog
    r = c.get("/api/v1/search/documents")
    cat = r.json()
    docs = cat["documents"]
    id_2023 = _pick(docs, DOC_2023_PREFIX)
    id_2026 = _pick(docs, DOC_2026_PREFIX)
    demo["steps"].append({
        "step": "catalog",
        "status": cat["status"], "count": cat["count"],
        "sample": [d for d in docs if d["document_id"] in (id_2023, id_2026)],
    })

    # 2. same query, 2023 vs 2026 file (bm25 + available dense/hybrid)
    modes = ["bm25"] + ([m for m in ("dense", "hybrid")
                         if m in (c.get("/api/v1/search/status").json().get("available_modes") or [])])
    for label, doc_id in (("select-2023", id_2023), ("select-2026", id_2026)):
        for mode in modes:
            r = c.post("/api/v1/search", json={"query": QUERY, "top_k": 5, "mode": mode,
                                               "document_id": doc_id})
            d = r.json()
            hits = _trim_hits(d.get("hits") or [])
            demo["steps"].append({
                "step": label, "mode": mode, "http": r.status_code,
                "document_id": d.get("document_id"),
                "source_selection": d.get("source_selection"),
                "hit_documents": sorted({h["document_id"] for h in hits}),
                "hits": hits,
                "all_hits_inside_selected": all(h["chunk"]["document_id"] == doc_id for h in (d.get("hits") or [])),
                "preview_prefix_ok": all(h["preview_url"].startswith("/preview#" + doc_id) for h in hits),
            })

    # 3. file + date condition excluded (2026 file not yet effective in 2020)
    r = c.post("/api/v1/search", json={"query": QUERY, "top_k": 5, "mode": "bm25",
                                       "document_id": id_2026,
                                       "filters": {"as_of_date": "2020-01-01"}})
    d = r.json()
    demo["steps"].append({
        "step": "file-plus-date-excluded", "http": r.status_code,
        "source_selection": d.get("source_selection"),
        "filter_summary": d.get("filter_summary"),
        "hits": _trim_hits(d.get("hits") or []),
        "hits_empty": not (d.get("hits") or []),
    })

    # 4. unknown id -> 422
    r = c.post("/api/v1/search", json={"query": QUERY, "mode": "bm25",
                                       "document_id": "doc-not-exist"})
    demo["steps"].append({
        "step": "unknown-id", "http": r.status_code,
        "body": r.json(),
    })

    # 5. /ask extractive with selection
    r = c.post("/api/v1/ask", json={"query": QUERY, "top_k": 5, "mode": "bm25",
                                    "document_id": id_2023, "answer_mode": "extractive"})
    d = r.json()
    demo["steps"].append({
        "step": "ask-extractive-select-2023", "http": r.status_code,
        "status": d.get("status"), "evidence_state": d.get("evidence_state"),
        "document_id": d.get("document_id"),
        "evidence_documents": sorted({e["document_id"] for e in (d.get("evidence") or [])}),
        "evidence_previews": [e["preview_url"] for e in (d.get("evidence") or [])][:3],
    })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)
    for s in demo["steps"]:
        print(s["step"], "|", {k: v for k, v in s.items()
                               if k in ("http", "mode", "hit_documents", "hits_empty", "evidence_documents")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
