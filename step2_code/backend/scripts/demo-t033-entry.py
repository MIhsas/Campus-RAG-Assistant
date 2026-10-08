"""T033 local evidence — related-entry metadata from the configured catalog.

Loads the real pack + the real template (serve-corpus equivalent) and shows
GET /api/v1/procedures entry fields (related_keywords / source_document_ids),
plus the deterministic entry decisions the ask page performs for the 2026 vs
2023 source cases (computed with the same rule: keyword match ∧ source set).
In-process only; no external calls; no model.

Output: docs/collaboration/submissions/T033/entry-api-demo.json
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
PROCEDURES = ROOT / "data/procedures/sicau-transfer-2026-v1/procedures.json"
DOC_2026 = "5cb2ac21497c2dade0961bedb355b3ed568b4ea409fb964e3064ea9197209e76"
DOC_2023 = "d1fe991c41377ab75fb3d93283de95b274f98b9d99f9e18463f9d374d8327b93"


def decide(entries, query, document_id):
    """Same deterministic rule as ask.html: keyword match, then source set."""
    matched, mismatch = [], []
    for p in entries:
        if not any(k in query for k in (p.get("related_keywords") or [])):
            continue
        if document_id is None:
            matched.append(p["procedure_id"])
        elif document_id in (p.get("source_document_ids") or []):
            matched.append(p["procedure_id"])
        else:
            mismatch.append(p["procedure_id"])
    return {"matched": matched, "source_mismatch": mismatch}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/collaboration/submissions/T033/entry-api-demo.json"))
    args = ap.parse_args()

    app = create_app(manifest_path=MANIFEST, corpus_root=MANIFEST.parent, procedures_path=PROCEDURES)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/api/v1/procedures")
    entries = r.json().get("procedures", [])
    out = {
        "note": "T033 本地证据：配置目录的入口元数据 + ask 页确定性入口判定（关键词∩来源集合）；零外部调用",
        "list_http": r.status_code,
        "entries": [{k: e.get(k) for k in
                     ("procedure_id", "title", "template_version", "is_synthetic",
                      "related_keywords", "source_document_ids")}
                    for e in entries],
        "decisions": {
            "query=转专业, source=2026版": decide(entries, "申请转专业 课程要求", DOC_2026),
            "query=转专业, source=2023版": decide(entries, "申请转专业 课程要求", DOC_2023),
            "query=转专业, source=未指定": decide(entries, "申请转专业 课程要求", None),
            "query=无关问题, source=未指定": decide(entries, "缓考申请须由谁批准", None),
        },
        "link_contract": "办事链接带 procedure_id+四条件快照；document_id 不进入办事参数（所选文件仅界定本次问答范围）",
    }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", p)
    print(json.dumps(out["decisions"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
