"""T031 auxiliary-condition comparison: retrieval with an added user
file-selection condition vs the same retrieval without it.

Framing (required): this is "增加用户文件选择条件后的辅助检索对照" — an extra
user-supplied input narrows the candidate set. It is NOT a claim of pure
algorithm improvement, automatic version understanding, or campus-wide
accuracy. Without the selection condition, mixed-version mixing can still
happen — a known limitation.

Setup:
- 10 fixed questions: T030 v1.3 version-constrained items (question text
  names a document number/title). The per-question file choice comes from
  the FROZEN selection-map.json (manual mapping: question wording + manifest
  catalog) — never inferred from gold document IDs or retrieval rankings.
- Baseline branch: no document_id (previous behaviour). Cross-checked
  against T030 stored rankings for the same questions.
- Selection branch: document_id from the map. Same query, same four
  conditions, same TopK=5, three modes.
- Gold is used for scoring only; questions and gold are unmodified.
- One app build per run (documents encoded once); all queries reuse the
  built indexes. Local BGE only — zero external model calls.
- Aggregates are recomputed from this run's per-question rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient  # noqa: E402

from campus_assistant.evaluation.metrics import compute_summary, evaluate_question  # noqa: E402
from campus_assistant.main import create_app  # noqa: E402

EXP_DIR = ROOT / "data/evaluations/sicau-rag-source-selection-v1"
MAP_PATH = EXP_DIR / "selection-map.json"
QUESTIONS_PATH = ROOT / "data/evaluations/sicau-rag-pilot-eval-v1/questions.json"
T030_RESULTS_DIR = ROOT / "data/evaluations/sicau-rag-pilot-eval-v1/results"
MANIFEST = ROOT / "data/corpora/sicau-rag-pilot-v1.1/manifest.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hit_key(h: dict) -> tuple:
    chunk = h.get("chunk") or h
    return (chunk.get("document_id"), chunk.get("block_id"),
            chunk.get("char_start"), chunk.get("char_end"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-path", default=str(BACKEND / "models/bge-small-zh-v1.5"))
    ap.add_argument("--out", default=str(EXP_DIR / "experiment.json"))
    args = ap.parse_args()

    sel_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    questions = {q["question_id"]: q for q in
                 json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]}
    t030 = {}
    for mode in ("bm25", "dense", "hybrid"):
        doc = json.loads((T030_RESULTS_DIR / f"{mode}.json").read_text(encoding="utf-8"))
        t030[mode] = {r["question_id"]: r for r in doc["per_question"]}

    app = create_app(
        manifest_path=MANIFEST,
        corpus_root=MANIFEST.parent,
        embedding_model_path=args.model_path if Path(args.model_path).exists() else None,
    )
    c = TestClient(app, raise_server_exceptions=False)
    modes = ["bm25", "dense", "hybrid"]

    rows = []
    for item in sel_map["items"]:
        qid = item["question_id"]
        q = questions[qid]
        filters = q.get("conditions") or {}
        active = {k: v for k, v in filters.items() if v is not None}
        for mode in modes:
            entry = {"question_id": qid, "mode": mode,
                     "query": q["query"], "selected_document_id": item["selected_document_id"],
                     "selection_basis": item["selection_basis"]}
            branches = {}
            for branch, doc_id in (("baseline", None), ("selection", item["selected_document_id"])):
                body = {"query": q["query"], "top_k": 5, "mode": mode}
                if active:
                    body["filters"] = active
                if doc_id:
                    body["document_id"] = doc_id
                r = c.post("/api/v1/search", json=body)
                assert r.status_code == 200, f"{qid}/{mode}/{branch}: HTTP {r.status_code}"
                d = r.json()
                hits = d.get("hits") or []
                scored = evaluate_question(q, hits, top_k=5)
                branches[branch] = {
                    "recall": scored["recall"], "hit": scored["hit"], "mrr": scored["mrr"],
                    "returned_count": scored["returned_count"],
                    "hit_documents": sorted({h["chunk"]["document_id"] for h in hits}),
                    "hit_sequence": [_hit_key(h) for h in hits],
                    "source_selection": d.get("source_selection"),
                }
            # baseline vs T030 stored ranking cross-check (same question/mode)
            stored = t030[mode].get(qid)
            stored_seq = [(_h.get("document_id"), _h.get("block_id"),
                           _h.get("char_start"), _h.get("char_end"))
                          for _h in (stored or {}).get("hit_summary") or []]
            branches["baseline_matches_t030_ranking"] = (
                branches["baseline"]["hit_sequence"] == stored_seq
            )
            entry["branches"] = branches
            rows.append(entry)

    # Aggregates recomputed from this run's rows (no stale grouping reuse).
    aggregates = {}
    for mode in modes:
        for branch in ("baseline", "selection"):
            per_q = []
            for entry in rows:
                if entry["mode"] != mode:
                    continue
                b = entry["branches"][branch]
                per_q.append({
                    "question_id": entry["question_id"], "answerable": True,
                    "recall": b["recall"], "hit": b["hit"], "mrr": b["mrr"],
                    "returned_count": b["returned_count"],
                })
            aggregates[f"{mode}/{branch}"] = compute_summary(per_q)

    by_group = {}
    for entry in rows:
        qid = entry["question_id"]
        for branch in ("baseline", "selection"):
            key = f"{entry['mode']}/{branch}"
            by_group.setdefault(key, []).append(entry["branches"][branch]["recall"])

    baseline_checks = Counter(e["branches"]["baseline_matches_t030_ranking"] for e in rows)
    out = {
        "note": "T031 增加用户文件选择条件后的辅助检索对照（非纯算法提升）；"
                "baseline=无选择（旧行为），selection=题面文号人工映射的显式文件选择；"
                "gold 仅用于评分；零外部模型调用",
        "selection_map_sha256": _sha(MAP_PATH),
        "questions_sha256": _sha(QUESTIONS_PATH),
        "corpus_manifest_sha256": _sha(MANIFEST),
        "questions_per_branch": len(sel_map["items"]),
        "modes": modes,
        "rows": rows,
        "aggregates": aggregates,
        "baseline_vs_t030_ranking_match": {
            "matched": baseline_checks.get(True, 0),
            "total": sum(baseline_checks.values()),
        },
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # freeze: selection map + current implementation hashes + model identity
    impl_files = [
        "src/campus_assistant/retrieval/source_selection.py",
        "src/campus_assistant/retrieval/service.py",
        "src/campus_assistant/api/search.py",
        "src/campus_assistant/api/ask.py",
        "src/campus_assistant/qa/evidence.py",
    ]
    model_dir = Path(args.model_path)
    identity = {}
    if model_dir.exists():
        for name in ("config.json", "sentence_bert_config.json"):
            p = model_dir / name
            if p.exists():
                identity[name] = _sha(p)
    freeze = {
        "note": "T031 对照实验冻结（选择映射+当前产品实现+模型身份）；T030 冻结保持只读不动",
        "frozen_at": "2026-10-07",
        "selection_map_sha256": _sha(MAP_PATH),
        "questions_sha256": _sha(QUESTIONS_PATH),
        "corpus_manifest_sha256": _sha(MANIFEST),
        "implementation_sha256": {f: _sha(BACKEND / f) for f in impl_files},
        "embedding_model": {"dir": "models/bge-small-zh-v1.5", "identity_files_sha256": identity},
    }
    freeze_path = EXP_DIR / "freeze.json"
    freeze_path.write_text(json.dumps(freeze, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("wrote", out_path)
    print("wrote", freeze_path)
    for key, s in aggregates.items():
        print(f"{key}: R={s['evidence_recall']:.3f} H={s['hit']:.3f} M={s['mrr']:.3f}")
    print("baseline vs T030 ranking match:",
          out["baseline_vs_t030_ranking_match"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
