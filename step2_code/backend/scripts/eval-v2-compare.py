"""T027 three-mode retrieval comparison merge (offline).

Merges the per-mode evaluation JSON outputs (bm25/dense/hybrid, same corpus/
questions/conditions/top_k) into reviewable per-question + aggregate results:

- per-question JSON/CSV: actual ranking, scores, evidence coverage, conditions,
  metrics per mode (K=5 main; K=3 supplement computed from the SAME recorded
  top-5 hits — no re-search, no parameter search);
- aggregate JSON: counts/denominators overall, by question_type, by filter
  group; unanswerable kept on a SEPARATE denominator (empty-result ratio and
  with-results count). "有命中不等于有依据、空检索不等于模型可靠拒答" is
  recorded verbatim in the output notes.

Never modifies evaluation inputs or mode outputs. All results synthetic.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND / "src") not in sys.path:
    sys.path.insert(0, str(BACKEND / "src"))

K_MAIN = 5
K_SUPP = 3


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _k3_from_hit_summary(question: dict, hit_summary: list[dict]) -> dict:
    """K=3 supplement from recorded top-K hits (no re-search)."""
    from campus_assistant.evaluation.metrics import evaluate_question

    hits = [{
        "score": h.get("score", 0),
        "chunk": {
            "document_id": h.get("document_id", ""),
            "block_id": h.get("block_id", ""),
            "chunk_id": h.get("chunk_id", ""),
            "char_start": h.get("char_start", 0),
            "char_end": h.get("char_end", 0),
        },
    } for h in hit_summary]
    r = evaluate_question(question, hits, top_k=K_SUPP)
    return {"recall": r["recall"], "hit": r["hit"], "mrr": r["mrr"], "returned_count": r["returned_count"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="T027 三模式对照聚合（离线合并）")
    parser.add_argument("--questions", required=True)
    parser.add_argument("--results", nargs=3, required=True, metavar=("BM25_JSON", "DENSE_JSON", "HYBRID_JSON"))
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--commands", default="", help="三次正式运行的命令（记录进结果）")
    args = parser.parse_args()

    questions_path = Path(args.questions)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    q_by_id = {q["question_id"]: q for q in questions["questions"]}

    modes = ["bm25", "dense", "hybrid"]
    runs = {}
    for mode, path in zip(modes, args.results):
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["valid"], f"{mode} 结果无效"
        assert data["mode"] == mode
        runs[mode] = {"path": p, "data": data, "sha256": _sha256(p)}
        assert data["questions_sha256"] == _sha256(questions_path), f"{mode} 题集哈希不一致"
        assert data["manifest_sha256"] == runs[modes[0]]["data"]["manifest_sha256"], "语料哈希不一致"
        assert data["parameters"]["top_k"] == K_MAIN

    # ---- 逐题合并 ----
    per_question = []
    for qid in [q["question_id"] for q in questions["questions"]]:
        gold = q_by_id[qid]
        row = {
            "question_id": qid,
            "query": gold["query"],
            "answerable": gold["answerable"],
            "question_type": gold.get("question_type"),
            "group_id": gold.get("group_id"),
            "conditions": gold.get("conditions"),
            "gold_evidence": [
                {"evidence_id": e["evidence_id"], "document_id": e["document_id"],
                 "block_id": e["block_id"], "char_start": e["char_start"], "char_end": e["char_end"],
                 "quote": e["quote"]}
                for e in gold.get("evidence", [])
            ],
            "rationale": gold.get("rationale"),
            "missing": gold.get("missing"),
            "modes": {},
        }
        for mode in modes:
            rec = next(r for r in runs[mode]["data"]["per_question"] if r["question_id"] == qid)
            row["modes"][mode] = {
                "recall": rec["recall"], "hit": rec["hit"], "mrr": rec["mrr"],
                "returned_count": rec["returned_count"],
                "covered_evidence_ids": rec["covered_evidence_ids"],
                "fact_count": rec.get("fact_count"),
                "covered_fact_count": rec.get("covered_fact_count"),
                "facts": rec.get("facts"),
                "ranking": [
                    {"rank": h["rank"], "score": h["score"], "document_id": h["document_id"],
                     "block_id": h["block_id"], "char_start": h["char_start"], "char_end": h["char_end"]}
                    for h in rec["hit_summary"]
                ],
                "k3": _k3_from_hit_summary(gold, rec["hit_summary"]),
            }
        metrics = {m: (row["modes"][m]["recall"], row["modes"][m]["hit"], row["modes"][m]["mrr"]) for m in modes}
        row["modes_agree"] = len(set(metrics.values())) == 1
        per_question.append(row)

    # ---- 聚合 ----
    def agg(rows: list[dict], k: str = "main") -> dict:
        ans = [r for r in rows if r["answerable"]]
        una = [r for r in rows if not r["answerable"]]

        def mv(mode, field):
            if not ans:
                return None
            if k == "main":
                return sum(r["modes"][mode][field] for r in ans) / len(ans)
            return sum(r["modes"][mode]["k3"][field] for r in ans) / len(ans)

        out = {
            "question_count": len(rows),
            "answerable_count": len(ans),
            "unanswerable_count": len(una),
            "denominator_note": "recall/hit/mrr 仅在可回答题上平均；材料不足题单独分母，不计入 recall 稀释",
        }
        for mode in modes:
            out[mode] = {
                "evidence_recall": mv(mode, "recall"),
                "hit": mv(mode, "hit"),
                "mrr": mv(mode, "mrr"),
            }
        if una:
            for mode in modes:
                empty = sum(1 for r in una if r["modes"][mode]["returned_count"] == 0)
                out[mode]["unanswerable_empty_rate"] = empty / len(una)
                out[mode]["unanswerable_with_results_count"] = len(una) - empty
        out["unanswerable_note"] = "有命中不等于有依据、空检索不等于模型可靠拒答"
        return out

    by_type: dict[str, list] = {}
    for r in per_question:
        by_type.setdefault(r.get("question_type") or "untyped", []).append(r)
    by_filter: dict[str, list] = {}
    for r in per_question:
        cond = r.get("conditions") or {}
        has_filter = any(cond.get(f) is not None for f in ("campus", "student_type", "admission_year", "as_of_date"))
        key = (r["group_id"] + "|filtered") if (r.get("group_id") and has_filter) else ("filtered" if has_filter else "no_filter")
        by_filter.setdefault(key, []).append(r)

    aggregate = {
        "note": "T027 三模式对照聚合（合成评测；K=5 主口径，K=3 为同命中补充口径，非参数搜索）",
        "dataset_id": questions["dataset_id"],
        "dataset_version": questions["dataset_version"],
        "questions_sha256": _sha256(questions_path),
        "manifest_sha256": runs["bm25"]["data"]["manifest_sha256"],
        "embedding_model_id": runs["dense"]["data"]["embedding_model_id"],
        "embedding_model_revision": runs["dense"]["data"]["embedding_model_revision"],
        "parameters": runs["bm25"]["data"]["parameters"] | {"rrf_k": 60},
        "retriever_version": runs["bm25"]["data"]["retriever_version"],
        "commands": args.commands,
        "result_files": {m: {"path": str(runs[m]["path"]), "sha256": runs[m]["sha256"]} for m in modes},
        "overall_k5": agg(per_question, "main"),
        "overall_k3_supplement": agg(per_question, "k3"),
        "by_type_k5": {k: agg(v, "main") for k, v in sorted(by_type.items())},
        "by_filter_group_k5": {k: agg(v, "main") for k, v in sorted(by_filter.items())},
    }

    (out_dir / "per-question.json").write_text(
        json.dumps(per_question, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with open(out_dir / "per-question.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["question_id", "query", "answerable", "question_type", "group_id", "conditions",
                    "mode", "k", "recall", "hit", "mrr", "returned_count", "covered_evidence_ids", "modes_agree"])
        for r in per_question:
            for mode in modes:
                m = r["modes"][mode]
                w.writerow([r["question_id"], r["query"], r["answerable"], r["question_type"], r["group_id"],
                            json.dumps(r["conditions"], ensure_ascii=False), mode, K_MAIN,
                            m["recall"], m["hit"], m["mrr"], m["returned_count"],
                            ";".join(m["covered_evidence_ids"]), r["modes_agree"]])
                w.writerow([r["question_id"], r["query"], r["answerable"], r["question_type"], r["group_id"],
                            json.dumps(r["conditions"], ensure_ascii=False), mode, K_SUPP,
                            m["k3"]["recall"], m["k3"]["hit"], m["k3"]["mrr"], m["k3"]["returned_count"], "", r["modes_agree"]])

    print("overall K=5:")
    for mode in modes:
        a = aggregate["overall_k5"][mode]
        print(f"  {mode}: recall={a['evidence_recall']:.4f} hit={a['hit']:.4f} mrr={a['mrr']:.4f}")
    print("wrote:", out_dir / "per-question.json", out_dir / "per-question.csv", out_dir / "aggregate.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
