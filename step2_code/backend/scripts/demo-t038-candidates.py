"""T038 local API demo — uncertain-source candidates on the real v1.2 pack.

In-process ASGI client; BM25 only; zero external calls; no browser claim.
Shows: strict admission unchanged (5/20 under as_of=2026-10-03 after the
bed3ac date correction), date-unknown candidates (db05e0 still unknown),
student_type-unknown candidates (83eb etc. — scope kept unknown), both-
dimension double-unknown rule, and document_id intersection. Output:
docs/collaboration/submissions/T038/candidate-api-demo.json
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

MANIFEST = ROOT / "data/corpora/sicau-rag-pilot-v1.2/manifest.json"


def _hits(d, n=3):
    return [{
        "document_id": h["chunk"]["document_id"][:12],
        "title": (h["chunk"].get("metadata") or {}).get("title"),
        "version_label": (h["chunk"].get("metadata") or {}).get("version_label"),
        "unknown_dimensions": h.get("unknown_dimensions"),
        "preview_url": h.get("preview_url"),
    } for h in (d.get("hits") or [])[:n]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/collaboration/submissions/T038/candidate-api-demo.json"))
    args = ap.parse_args()

    app = create_app(manifest_path=MANIFEST, corpus_root=MANIFEST.parent)
    c = TestClient(app, raise_server_exceptions=False)
    out = {"note": "T038 候选 API 真实演示（语料包 v1.2、BM25、in-process；零外部调用；非浏览器证据）",
           "steps": []}

    base = {"query": "考试开始多久后迟到考生不得进入考场", "mode": "bm25", "top_k": 5}

    # 0) strict reference: as_of admission 5/20 (v1.2)
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.retrieval.filters import compute_allowed_document_ids
    r = parse_manifest(MANIFEST, MANIFEST.parent)
    strict = compute_allowed_document_ids(r["documents"], {"campus": None, "student_type": None,
                                                           "admission_year": None, "as_of_date": "2026-10-03"})
    out["steps"].append({"step": "strict-as_of-2026-10-03", "allowed_count": len(strict["allowed_document_ids"]),
                         "excluded": strict["excluded_counts"],
                         "bed3ac_admitted": any(i.startswith("bed3ac95") for i in strict["allowed_document_ids"]),
                         "db05e0_admitted": any(i.startswith("db05e0") for i in strict["allowed_document_ids"])})

    # 1) date-unknown candidates (u03 scenario)
    body = dict(base, filters={"student_type": None, "as_of_date": "2026-10-03"},
                uncertainty_dimensions=["date"])
    resp = c.post("/api/v1/search/candidates", json=body)
    d = resp.json()
    out["steps"].append({
        "step": "candidates-date-u03", "http": resp.status_code,
        "candidate_count": d["candidate_summary"]["candidate_document_count"],
        "strict_allowed": d["candidate_summary"]["strict_allowed_count"],
        "disclaimer": d.get("disclaimer"),
        "hits": _hits(d),
    })

    # 2) student_type-unknown candidates (u04 scenario)
    body = {"query": "学籍基本信息有误去哪里办理", "mode": "bm25", "top_k": 5,
            "filters": {"student_type": "本科"}, "uncertainty_dimensions": ["student_type"]}
    resp = c.post("/api/v1/search/candidates", json=body)
    d = resp.json()
    out["steps"].append({
        "step": "candidates-student-type-u04", "http": resp.status_code,
        "candidate_count": d["candidate_summary"]["candidate_document_count"],
        "hits": _hits(d),
    })

    # 3) both dimensions (double-unknown rule demo)
    body = {"query": "办理", "mode": "bm25", "top_k": 5,
            "filters": {"student_type": "本科", "as_of_date": "2026-10-03"},
            "uncertainty_dimensions": ["date", "student_type"]}
    resp = c.post("/api/v1/search/candidates", json=body)
    d = resp.json()
    out["steps"].append({
        "step": "candidates-both-dimensions", "http": resp.status_code,
        "candidate_count": d["candidate_summary"]["candidate_document_count"],
        "hits": _hits(d, 6),
    })

    # 4) 422 contract samples
    samples = {
        "empty-dims": {"query": "q", "mode": "bm25", "uncertainty_dimensions": []},
        "invalid-dim": {"query": "q", "mode": "bm25", "filters": {"as_of_date": "2026-10-03"},
                        "uncertainty_dimensions": ["campus"]},
        "dim-without-filter": {"query": "q", "mode": "bm25", "uncertainty_dimensions": ["date"]},
        "unknown-document": {"query": "q", "mode": "bm25", "filters": {"as_of_date": "2026-10-03"},
                             "document_id": "unavailable-file", "uncertainty_dimensions": ["date"]},
    }
    for label, b in samples.items():
        resp = c.post("/api/v1/search/candidates", json=b)
        out["steps"].append({"step": f"contract-{label}", "http": resp.status_code,
                             "code": resp.json().get("code"), "message": resp.json().get("message")})

    # 5) strict search/ask unchanged (no candidate leakage)
    resp = c.post("/api/v1/search", json=dict(base, filters={"as_of_date": "2026-10-03"}))
    d = resp.json()
    out["steps"].append({"step": "strict-search-unchanged", "http": resp.status_code,
                         "has_candidate_fields": ("candidate_summary" in d or "disclaimer" in d),
                         "hits": len(d.get("hits") or [])})
    resp = c.post("/api/v1/ask", json={"query": "考试迟到", "mode": "bm25",
                                       "filters": {"as_of_date": "2026-10-03"}})
    d = resp.json()
    out["steps"].append({"step": "strict-ask-unchanged", "http": resp.status_code,
                         "evidence_count": len(d.get("evidence") or []),
                         "has_candidate_fields": ("candidate_summary" in d)})

    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", p)
    for s in out["steps"]:
        print(s["step"], "|", {k: v for k, v in s.items()
                               if k in ("http", "allowed_count", "candidate_count", "has_candidate_fields", "bed3ac_admitted")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
