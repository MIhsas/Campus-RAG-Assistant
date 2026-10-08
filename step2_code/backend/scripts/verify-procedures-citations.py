"""T032: programmatic citation cross-check for a procedures template.

Fresh-parses the real corpus pack and reuses the procedures service checks
(document existence / sha256 / verbatim span / quote) for EVERY citation,
then builds one filterless draft to confirm the template is saveable.

Usage:
  python scripts/verify-procedures-citations.py \
    --procedures data/procedures/sicau-transfer-2026-v1/procedures.json \
    --manifest data/corpora/sicau-rag-pilot-v1.1/manifest.json

Exit 0 only when every citation passes (status ok) and the draft is saveable.
This is programmatic span/hash verification only — semantic organisation is
model-assisted and NOT human-reviewed (stated in the template note).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from campus_assistant.procedures.service import (  # noqa: E402
    _check_citation,
    _index_documents,
    build_draft,
    load_procedures,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--procedures", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--corpus-root", default=None)
    args = ap.parse_args()

    manifest = Path(args.manifest)
    corpus_root = Path(args.corpus_root) if args.corpus_root else manifest.parent

    template = load_procedures(Path(args.procedures))

    from campus_assistant.corpus.parse import parse_manifest

    result = parse_manifest(manifest, corpus_root)
    if not result.get("valid"):
        print("FAIL corpus parse:", result.get("errors"))
        return 1
    documents = result["documents"]
    documents_by_id, blocks_by_doc = _index_documents(documents)

    fails = 0
    rows = []
    for proc in template["procedures"]:
        for step in proc["steps"]:
            for c in step["citations"]:
                status = _check_citation(c, documents_by_id, blocks_by_doc, None)
                ok = status == "ok"
                fails += 0 if ok else 1
                q = c["quote"].replace("\n", "⏎")
                rows.append((proc["procedure_id"], step["step_id"], c["block_id"][:8],
                             f"[{c['char_start']}:{c['char_end']}]", status, q[:52]))

    print(f"{'proc':22s} {'step':4s} {'block':8s} {'span':12s} {'status':8s} quote")
    for r in rows:
        print(f"{r[0]:22s} {r[1]:4s} {r[2]:8s} {r[3]:12s} {r[4]:8s} {r[5]}…")
    total = len(rows)
    print(f"citations: {total - fails}/{total} ok")

    draft = build_draft(template, template["procedures"][0]["procedure_id"], None, documents)
    print("draft saveable:", draft["saveable"], "| steps:", len(draft["steps"]),
          "| status:", draft["status"])
    if not draft["saveable"]:
        print("FAIL draft issues:", draft["issues"])
        fails += 1

    if fails:
        print(f"CHECK FAILED: {fails} 项")
        return 1
    print("CHECK OK: 全部引用逐字/跨度/哈希核对通过，草稿可保存")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
