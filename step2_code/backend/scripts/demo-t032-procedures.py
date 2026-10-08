"""T032 local API demo — real transfer-major procedure template (2026 edition).

Assembles the app with the real v1.1 pack + the new procedures template
(exactly what serve-corpus.py --procedures does) and exercises the user flow
at API level (in-process ASGI client; no external calls):

1. template listing (is_synthetic=false, real source identity);
2. draft with no filters / with student_type=本科 — saveable, citations ok;
3. draft under an excluding condition (as_of_date before effective_from)
   — not saveable, no quoted original text leaked for failed citations;
4. saved-basis snapshot verify → 'unchanged'; tampered snapshot → 'changed'.

Output: docs/collaboration/submissions/T032/api-demo.json
"""

from __future__ import annotations

import argparse
import copy
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
PROCEDURES = ROOT / "data/procedures/sicau-transfer-2026-v1/procedures.json"
PID = "sicau-transfer-2026"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/collaboration/submissions/T032/api-demo.json"))
    args = ap.parse_args()

    app = create_app(manifest_path=MANIFEST, corpus_root=MANIFEST.parent, procedures_path=PROCEDURES)
    c = TestClient(app, raise_server_exceptions=False)
    demo = {"note": "T032 本地 API 演示（真实包 v1.1 + sicau-transfer-2026 模板；in-process；零外部调用）",
            "steps": []}

    # 1. listing
    r = c.get("/api/v1/procedures")
    listing = r.json()
    demo["steps"].append({
        "step": "list", "http": r.status_code,
        "procedures": [{k: p.get(k) for k in ("procedure_id", "title", "template_version", "is_synthetic")}
                       for p in listing.get("procedures", [])],
    })

    # 2. drafts
    drafts = {}
    for label, filters in (("draft-no-filters", None), ("draft-student-type-本科", {"student_type": "本科"})):
        body = {"filters": filters} if filters else {}
        r = c.post(f"/api/v1/procedures/{PID}/draft", json=body)
        d = r.json()
        drafts[label] = d
        ok_cits = sum(1 for s in d["steps"] for cit in s["citations"] if cit["status"] == "ok")
        demo["steps"].append({
            "step": label, "http": r.status_code,
            "saveable": d["saveable"], "status": d["status"],
            "steps_count": len(d["steps"]),
            "citations_ok": ok_cits,
            "sample_step": {"step_id": d["steps"][0]["step_id"], "title": d["steps"][0]["title"],
                            "detail_head": (d["steps"][0]["detail"] or "")[:60],
                            "first_citation": {k: d["steps"][0]["citations"][0].get(k)
                                               for k in ("document_id", "block_id", "char_start", "char_end", "status", "usable")}},
            "disclaimer": d["disclaimer"],
        })

    # 3. excluding condition (as_of_date before 2026-01-08 effective_from)
    r = c.post(f"/api/v1/procedures/{PID}/draft", json={"filters": {"as_of_date": "2020-01-01"}})
    d = r.json()
    failed_cits = [cit for s in d["steps"] for cit in s["citations"] if not cit["usable"]]
    demo["steps"].append({
        "step": "draft-excluded-by-date", "http": r.status_code,
        "saveable": d["saveable"], "status": d["status"],
        "issues": d["issues"][:3],
        "failed_citation_statuses": sorted({cit["status"] for cit in failed_cits}),
        "failed_quotes_are_null": all(cit["quote"] is None for cit in failed_cits),
        "failed_details_suppressed": all(s["detail"] is None for s in d["steps"] if s["status"] == "failed"),
    })

    # 4. save-snapshot verify (what the page stores), then tamper check
    good = drafts["draft-student-type-本科"]
    snapshot = {
        "template_version": good["template_version"],
        "filters": good["filters"],
        "steps": [{"step_id": s["step_id"], "title": s["title"],
                   "citations": [cit for cit in s["citations"] if cit["usable"] and cit["quote"]]}
                  for s in good["steps"]],
    }
    r = c.post(f"/api/v1/procedures/{PID}/verify", json=snapshot)
    demo["steps"].append({
        "step": "verify-saved-snapshot", "http": r.status_code,
        "verdict": r.json().get("status"), "issues": r.json().get("issues"),
    })
    tampered = copy.deepcopy(snapshot)
    tampered["steps"][0]["citations"][0]["char_start"] = tampered["steps"][0]["citations"][0]["char_start"] + 1
    r = c.post(f"/api/v1/procedures/{PID}/verify", json=tampered)
    demo["steps"].append({
        "step": "verify-tampered-snapshot", "http": r.status_code,
        "verdict": r.json().get("status"), "issues": r.json().get("issues", [])[:2],
    })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)
    for s in demo["steps"]:
        print(s["step"], "|", {k: v for k, v in s.items()
                               if k in ("http", "saveable", "status", "verdict", "citations_ok", "failed_quotes_are_null")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
