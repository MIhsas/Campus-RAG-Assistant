"""T027-R1 rescore from saved rankings (no re-retrieval).

Re-scores questions against ALREADY-SAVED hit rankings (per-mode run JSON's
hit_summary) using the current questions file. Permitted for gold-only
changes (query/conditions unchanged). Questions whose query/conditions
changed must be re-retrieved — this script reports them as changed and does
NOT rescore them.

Used as the cross-check: for unchanged-query questions the rescored metrics
must equal the metrics from the fresh re-run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND / "src"))


def _hits_from_summary(hit_summary: list[dict]) -> list[dict]:
    return [{
        "score": h.get("score", 0),
        "chunk": {
            "document_id": h.get("document_id", ""),
            "block_id": h.get("block_id", ""),
            "chunk_id": h.get("chunk_id", ""),
            "char_start": h.get("char_start", 0),
            "char_end": h.get("char_end", 0),
        },
    } for h in hit_summary]


def main() -> int:
    parser = argparse.ArgumentParser(description="T027-R1/R2 已存排名重计分 + 受影响题重检索合并")
    parser.add_argument("--questions", required=True, help="当前（修订后）questions.json")
    parser.add_argument("--rev1-questions", required=True, help="上一版 questions.json（判定查询/条件是否变化）")
    parser.add_argument("--results", nargs="+", required=True, help="已存的各模式运行 JSON（含 hit_summary）")
    parser.add_argument("--out", required=True)
    parser.add_argument("--rerun-results", nargs="+", default=None,
                        help="受影响题的子集重检索各模式 JSON（查询/条件变化的题从此取记录）")
    parser.add_argument("--merged-out-dir", default=None,
                        help="输出合并后的各模式完整结果目录（上一版记录+重计分+重检索拼接）")
    args = parser.parse_args()

    from campus_assistant.evaluation.metrics import compute_summary, evaluate_question

    new_qs = json.loads(Path(args.questions).read_text(encoding="utf-8"))["questions"]
    old_qs = {q["question_id"]: q for q in json.loads(Path(args.rev1_questions).read_text(encoding="utf-8"))["questions"]}
    saved = {json.loads(Path(p).read_text(encoding="utf-8"))["mode"]: json.loads(Path(p).read_text(encoding="utf-8")) for p in args.results}
    rerun = {}
    if args.rerun_results:
        rerun = {json.loads(Path(p).read_text(encoding="utf-8"))["mode"]: json.loads(Path(p).read_text(encoding="utf-8")) for p in args.rerun_results}

    rows = []
    changed_for_rerun = []
    merged_records = {m: [] for m in saved}
    for q in new_qs:
        old = old_qs.get(q["question_id"])
        query_changed = old is None or old["query"] != q["query"] or (old.get("conditions") or {}) != (q.get("conditions") or {})
        row = {"question_id": q["question_id"], "query_changed": query_changed, "modes": {}}
        if query_changed:
            changed_for_rerun.append(q["question_id"])
            if not rerun:
                rows.append(row)
                continue
            for mode, data in rerun.items():
                rec = next(r for r in data["per_question"] if r["question_id"] == q["question_id"])
                merged_records[mode].append(rec)
                row["modes"][mode] = {
                    "recall": rec["recall"], "hit": rec["hit"], "mrr": rec["mrr"],
                    "covered_evidence_ids": rec["covered_evidence_ids"],
                    "fact_count": rec.get("fact_count"), "covered_fact_count": rec.get("covered_fact_count"),
                    "source": "rerun",
                }
            rows.append(row)
            continue
        for mode, data in saved.items():
            rec = next(r for r in data["per_question"] if r["question_id"] == q["question_id"])
            r = evaluate_question(q, _hits_from_summary(rec["hit_summary"]), top_k=data["parameters"]["top_k"])
            merged = dict(rec)
            merged.update({
                "recall": r["recall"], "hit": r["hit"], "mrr": r["mrr"],
                "covered_evidence_ids": r["covered_evidence_ids"],
                "fact_count": r.get("fact_count"), "covered_fact_count": r.get("covered_fact_count"),
                "facts": r.get("facts"),
            })
            merged_records[mode].append(merged)
            row["modes"][mode] = {
                "recall": r["recall"], "hit": r["hit"], "mrr": r["mrr"],
                "covered_evidence_ids": r["covered_evidence_ids"],
                "fact_count": r.get("fact_count"), "covered_fact_count": r.get("covered_fact_count"),
                "source": "rescored_from_saved_ranking",
            }
        rows.append(row)

    out = {
        "note": "T027-R2 已存排名重计分 + 受影响题重检索合并；未变化题复用排名（不重复全库编码）",
        "changed_for_rerun": changed_for_rerun,
        "per_question": rows,
    }
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("rescored:", len(rows) - len(changed_for_rerun), "| rerun:", changed_for_rerun)
    print("wrote", p)

    if args.merged_out_dir:
        out_dir = Path(args.merged_out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        q_hash = __import__("hashlib").sha256(Path(args.questions).read_bytes()).hexdigest()
        for mode, data in saved.items():
            records = merged_records[mode]
            merged_doc = dict(data)
            merged_doc["questions_sha256"] = q_hash
            merged_doc["per_question"] = records
            merged_doc["question_count"] = len(records)
            merged_doc["answerable_count"] = sum(1 for r in records if r.get("answerable"))
            merged_doc["unanswerable_count"] = sum(1 for r in records if not r.get("answerable"))
            merged_doc["summary"] = compute_summary(records)
            merged_doc["merge_note"] = (
                "T027-R2 合并结果：未变化题=上一版已存排名重计分；"
                f"受影响重检索题={changed_for_rerun}（子集重跑）"
            )
            fp = out_dir / f"{mode}.json"
            fp.write_text(json.dumps(merged_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print("merged ->", fp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
