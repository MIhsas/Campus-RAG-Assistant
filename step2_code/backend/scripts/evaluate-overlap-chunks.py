"""T034 offline comparison: overlap-100 chunking vs the historical no-overlap
chunking on the real T030 v1.3 development set.

Fixed single-shot design (run-frozen config, no grid search):
- inputs: real pack sicau-rag-pilot-v1.1, T030 v1.3 all 24 questions with the
  original query / filters / gold; top_k=5, BM25 k1/b, BGE model, RRF k all as
  shipped. NO T031 file-selection condition is mixed in.
- baseline: historical overlap-0 identity; rankings reused from the T030 v1.3
  stored results (explicit historical identity + input hash checks). A BM25
  re-run on the unchanged default window path is compared question-by-question
  as the compatibility check (dense/hybrid baseline not re-encoded).
- candidate: overlap_chars=100 (step 400); each mode run once; Dense/Hybrid
  share ONE candidate encoding of the candidate chunks (documents encoded
  once). Local BGE only.
- scoring: the existing metrics (multi-interval coverage semantics unchanged).
  Duplicates (same-block/overlapping intervals inside top5) are recorded, not
  removed. Gains/regressions/non-improvements all kept.

Outputs under data/evaluations/sicau-rag-overlap-v1/:
  frozen-config.json  experiment.json (per-question raw rows + aggregates)

This is a development-set experiment on a model-assisted seen gold set —
not an independent test set and not campus accuracy. No answer-quality claims;
only retrieval metrics for "fact available in candidate index" and "in top5".
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND / "src"))
sys.stdout.reconfigure(encoding="utf-8")

EXP_DIR = ROOT / "data/evaluations/sicau-rag-overlap-v1"
MANIFEST = ROOT / "data/corpora/sicau-rag-pilot-v1.1/manifest.json"
QUESTIONS = ROOT / "data/evaluations/sicau-rag-pilot-eval-v1/questions.json"
T030_RESULTS = ROOT / "data/evaluations/sicau-rag-pilot-eval-v1/results"

MAX_CHARS = 500
OVERLAP_CANDIDATE = 100
TOP_K = 5


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hit_key(h: dict) -> tuple:
    c = h.get("chunk") or h
    return (c.get("document_id"), c.get("block_id"), c.get("char_start"), c.get("char_end"))


def _flat_key(h: dict) -> tuple:
    return (h.get("document_id"), h.get("block_id"), h.get("char_start"), h.get("char_end"))


def _dup_stats(hits: list[dict]) -> dict:
    """Same-block / overlapping-interval duplicates inside one top-k list."""
    keys = [_hit_key(h) for h in hits]
    same_block = 0
    overlapping = 0
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            (d1, b1, s1, e1), (d2, b2, s2, e2) = keys[i], keys[j]
            if d1 == d2 and b1 == b2:
                same_block += 1
                if min(e1, e2) > max(s1, s2):
                    overlapping += 1
    return {"hits": len(keys), "same_block_pairs": same_block,
            "overlapping_interval_pairs": overlapping}


def _fact_available(variant_chunks_by_block: dict, question: dict) -> dict:
    """Per fact: does any chunk of this variant fully cover ≥1 OR source?"""
    out = {}
    for ev in question.get("evidence", []):
        fid = ev.get("fact_id") or ev["evidence_id"]
        span = (ev["char_start"], ev["char_end"])
        ok = False
        for c in variant_chunks_by_block.get((ev["document_id"], ev["block_id"]), []):
            if c["char_start"] <= span[0] and span[1] <= c["char_end"]:
                ok = True
                break
        out.setdefault(fid, {"sources_available": 0, "sources_total": 0})
        out[fid]["sources_total"] += 1
        if ok:
            out[fid]["sources_available"] += 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-path", default=str(BACKEND / "models/bge-small-zh-v1.5"))
    args = ap.parse_args()
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    from campus_assistant.corpus.chunk import chunk_documents
    from campus_assistant.corpus.parse import parse_manifest
    from campus_assistant.evaluation.metrics import compute_summary, evaluate_question
    from campus_assistant.retrieval.bm25 import BM25Index
    from campus_assistant.retrieval.filters import compute_allowed_document_ids

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    parse_result = parse_manifest(MANIFEST, MANIFEST.parent)
    assert parse_result.get("valid"), parse_result.get("errors")
    documents = parse_result["documents"]

    # ---- run-frozen config (written BEFORE the runs) ----
    impl_files = [
        "src/campus_assistant/corpus/chunk.py",
        "src/campus_assistant/evaluation/metrics.py",
        "src/campus_assistant/retrieval/bm25.py",
        "src/campus_assistant/retrieval/dense.py",
        "src/campus_assistant/retrieval/hybrid.py",
        "src/campus_assistant/retrieval/embedding.py",
    ]
    model_dir = Path(args.model_path)
    identity = {}
    if model_dir.exists():
        for name in ("config.json", "sentence_bert_config.json"):
            p = model_dir / name
            if p.exists():
                identity[name] = _sha(p)
    frozen = {
        "note": "T034 跑前冻结：overlap 对照固定配置（baseline overlap0 vs candidate overlap100，单次、不网格）",
        "frozen_at": "2026-10-08",
        "params": {
            "max_chars": MAX_CHARS, "overlap_baseline": 0,
            "overlap_candidate": OVERLAP_CANDIDATE,
            "step_candidate": MAX_CHARS - OVERLAP_CANDIDATE,
            "top_k": TOP_K, "bm25_k1": 1.5, "bm25_b": 0.75, "rrf_k": 60,
            "modes": ["bm25", "dense", "hybrid"], "file_selection": "无（不混入 T031 条件）",
        },
        "questions_sha256": _sha(QUESTIONS),
        "corpus_manifest_sha256": _sha(MANIFEST),
        "t030_results_identity": {
            m: {
                "questions_sha256": json.loads((T030_RESULTS / f"{m}.json").read_text(encoding="utf-8")).get("questions_sha256"),
                "dataset_version": json.loads((T030_RESULTS / f"{m}.json").read_text(encoding="utf-8")).get("dataset_version"),
            }
            for m in ("bm25", "dense", "hybrid")
        },
        "implementation_sha256": {f: _sha(BACKEND / f) for f in impl_files},
        "embedding_model": {"dir": "models/bge-small-zh-v1.5", "identity_files_sha256": identity},
    }
    (EXP_DIR / "frozen-config.json").write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- chunk both variants ----
    t_chunk = time.time()
    base_chunks = chunk_documents(documents, max_chars=MAX_CHARS)
    cand_chunks = chunk_documents(documents, max_chars=MAX_CHARS, overlap_chars=OVERLAP_CANDIDATE)
    chunk_seconds = time.time() - t_chunk

    def by_block(chunks):
        m = {}
        for c in chunks:
            m.setdefault((c["document_id"], c["block_id"]), []).append(c)
        return m

    base_by_block = by_block(base_chunks)
    cand_by_block = by_block(cand_chunks)

    # ---- baseline identity + BM25 compatibility check vs T030 stored ----
    stored = {m: json.loads((T030_RESULTS / f"{m}.json").read_text(encoding="utf-8"))
              for m in ("bm25", "dense", "hybrid")}
    compat = {"checked": 0, "matched": 0, "mismatches": []}
    t_bm = time.time()
    base_bm25 = BM25Index(base_chunks, k1=1.5, b=0.75)
    bm25_build_seconds = time.time() - t_bm
    filters_by_q = {}
    for q in questions:
        cond = q.get("conditions") or {}
        filters_by_q[q["question_id"]] = {k: v for k, v in cond.items() if v is not None} or None

    def allowed_for(q):
        r = compute_allowed_document_ids(documents, filters_by_q[q["question_id"]])
        return r["allowed_document_ids"]

    for q in questions:
        allowed = allowed_for(q)
        hits = base_bm25.search(q["query"], top_k=TOP_K, allowed_document_ids=allowed)
        got = [_hit_key(h) for h in hits]
        exp = [_flat_key(h) for h in next(
            r for r in stored["bm25"]["per_question"] if r["question_id"] == q["question_id"]
        )["hit_summary"]]
        compat["checked"] += 1
        if got == exp:
            compat["matched"] += 1
        else:
            compat["mismatches"].append({"question_id": q["question_id"], "stored": exp, "rerun": got})

    # ---- candidate runs (shared encoding once for dense+hybrid) ----
    t_enc = time.time()
    dense_index = None
    embed = None
    encode_note = ""
    try:
        from campus_assistant.retrieval.dense import DenseIndex
        from campus_assistant.retrieval.embedding import EmbeddingService

        if model_dir.exists():
            embed = EmbeddingService(args.model_path)
            texts = [c.get("text", "") for c in cand_chunks]
            emb = embed.encode_documents(texts)
            dense_index = DenseIndex(cand_chunks, emb)
        else:
            encode_note = "模型目录不存在——dense/hybrid 候选未运行（BM25 候选已运行）"
    except Exception as e:  # noqa: BLE001
        encode_note = f"候选编码失败：{type(e).__name__}: {e}"
    encode_seconds = time.time() - t_enc

    cand_bm25 = BM25Index(cand_chunks, k1=1.5, b=0.75)

    def run_candidate(mode, q):
        allowed = allowed_for(q)
        if mode == "bm25":
            return cand_bm25.search(q["query"], top_k=TOP_K, allowed_document_ids=allowed)
        if embed is None or dense_index is None:
            return None
        if mode == "dense":
            return dense_index.search(embed.encode_query(q["query"]), top_k=TOP_K,
                                     allowed_document_ids=allowed)
        from campus_assistant.retrieval.hybrid import rrf_fusion
        bm = cand_bm25.search(q["query"], top_k=20, allowed_document_ids=allowed)
        de = dense_index.search(embed.encode_query(q["query"]), top_k=20, allowed_document_ids=allowed)
        return rrf_fusion(bm, de, top_k=TOP_K)

    rows = []
    for q in questions:
        row = {
            "question_id": q["question_id"], "answerable": q["answerable"],
            "question_type": q.get("question_type"), "group_id": q.get("group_id"),
            "conditions": filters_by_q[q["question_id"]],
            "fact_availability": {
                "baseline": _fact_available(base_by_block, q),
                "candidate": _fact_available(cand_by_block, q),
            },
            "modes": {},
        }
        for mode in ("bm25", "dense", "hybrid"):
            s_rec = next(r for r in stored[mode]["per_question"] if r["question_id"] == q["question_id"])
            entry = {
                "baseline_stored": {
                    "recall": s_rec["recall"], "hit": s_rec["hit"], "mrr": s_rec["mrr"],
                    "covered_evidence_ids": s_rec.get("covered_evidence_ids"),
                    "hit_keys": [_flat_key(h) for h in s_rec.get("hit_summary") or []],
                },
            }
            cand_hits = run_candidate(mode, q)
            if cand_hits is None:
                entry["candidate"] = None
            else:
                v = evaluate_question(q, cand_hits, top_k=TOP_K)
                entry["candidate"] = {
                    "recall": v["recall"], "hit": v["hit"], "mrr": v["mrr"],
                    "covered_evidence_ids": v["covered_evidence_ids"],
                    "hit_keys": [_hit_key(h) for h in cand_hits],
                    "dup_stats": _dup_stats(cand_hits),
                }
            row["modes"][mode] = entry
        rows.append(row)

    # ---- aggregates (answerable 20 / unanswerable 4 kept separate) ----
    aggregates = {}
    for mode in ("bm25", "dense", "hybrid"):
        for branch in ("baseline_stored", "candidate"):
            per_q = []
            for row in rows:
                e = row["modes"][mode][branch]
                if e is None:
                    continue
                per_q.append({
                    "question_id": row["question_id"], "answerable": row["answerable"],
                    "recall": e["recall"], "hit": e["hit"], "mrr": e["mrr"],
                    "returned_count": len(e["hit_keys"]),
                })
            if per_q:
                aggregates[f"{mode}/{branch}"] = compute_summary(per_q)

    grouping = {}
    for row in rows:
        for mode in ("bm25", "dense", "hybrid"):
            for branch in ("baseline_stored", "candidate"):
                e = row["modes"][mode][branch]
                if e is None or e["recall"] is None:
                    continue  # 不足题单独分母，不进可答分组均值
                key = f"{row['question_type'] or 'untyped'}|{mode}|{branch}"
                grouping.setdefault(key, []).append(e["recall"])
    group_summary = {k: {"n": len(v), "recall_mean": sum(v) / len(v)} for k, v in grouping.items()}

    dup_totals = {}
    for mode in ("bm25", "dense", "hybrid"):
        pairs = same = 0
        q_with_dup = 0
        for row in rows:
            e = row["modes"][mode].get("candidate")
            if not e:
                continue
            pairs += 1
            if e["dup_stats"]["same_block_pairs"] or e["dup_stats"]["overlapping_interval_pairs"]:
                q_with_dup += 1
            same += e["dup_stats"]["overlapping_interval_pairs"]
        dup_totals[mode] = {
            "questions_with_same_block_or_overlap_hits": q_with_dup,
            "questions_compared": pairs,
            "overlapping_interval_pairs_total": same,
        }

    # ---- boundary-fact case + regression / non-improvement cases ----
    boundary_cases = []
    for row in rows:
        q = next(x for x in questions if x["question_id"] == row["question_id"])
        for ev in q.get("evidence", []):
            span = (ev["char_start"], ev["char_end"])
            base_ok = any(c["char_start"] <= span[0] and span[1] <= c["char_end"]
                          for c in base_by_block.get((ev["document_id"], ev["block_id"]), []))
            cand_ok = any(c["char_start"] <= span[0] and span[1] <= c["char_end"]
                          for c in cand_by_block.get((ev["document_id"], ev["block_id"]), []))
            if not base_ok and cand_ok:
                boundary_cases.append({
                    "question_id": row["question_id"], "evidence_id": ev["evidence_id"],
                    "document_id": ev["document_id"], "block_id": ev["block_id"],
                    "span": list(span),
                    "note": "gold 源跨度被 baseline 硬边界切开；candidate 存在完整覆盖该跨度的块",
                })
    regressions = []
    non_improvements = []
    for row in rows:
        for mode in ("bm25", "dense", "hybrid"):
            b = row["modes"][mode]["baseline_stored"]
            c = row["modes"][mode]["candidate"]
            if c is None:
                continue
            b_r = b["recall"] if b["recall"] is not None else -1
            c_r = c["recall"] if c["recall"] is not None else -1
            b_m = b["mrr"] if b["mrr"] is not None else -1
            c_m = c["mrr"] if c["mrr"] is not None else -1
            if c_r < b_r or (c_r == b_r and c_m < b_m):
                regressions.append({
                    "question_id": row["question_id"], "mode": mode,
                    "baseline": {"recall": b["recall"], "mrr": b["mrr"]},
                    "candidate": {"recall": c["recall"], "mrr": c["mrr"]},
                    "candidate_dup": c["dup_stats"],
                })
            elif c_r == b_r and c_m == b_m:
                non_improvements.append({"question_id": row["question_id"], "mode": mode})

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    out = {
        "note": "T034 overlap-100 vs overlap-0 离线对照（固定参数单次；开发集实验，非独立测试/校园准确率；只评检索指标：事实可覆盖/进入 top5，不产生答案质量结论）",
        "frozen_config_ref": "frozen-config.json",
        "counts": {
            "questions": len(rows),
            "answerable": len(answerable),
            "unanswerable": len(unanswerable),
            "baseline_chunks": len(base_chunks),
            "candidate_chunks": len(cand_chunks),
        },
        "compat_bm25_baseline_vs_t030": compat,
        "encode_note": encode_note,
        "timing_seconds": {
            "chunk_both": round(chunk_seconds, 2),
            "baseline_bm25_build": round(bm25_build_seconds, 2),
            "candidate_dense_encode_and_build": round(encode_seconds, 2),
            "total": round(time.time() - t0, 2),
        },
        "aggregates": aggregates,
        "group_summary": group_summary,
        "dup_stats_candidate": dup_totals,
        "boundary_cases": boundary_cases[:10],
        "regressions": regressions,
        "non_improvements_count": len(non_improvements),
        "non_improvements": non_improvements[:40],
        "rows": rows,
    }
    (EXP_DIR / "experiment.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("wrote", EXP_DIR / "experiment.json")
    print("chunks baseline/candidate:", len(base_chunks), "/", len(cand_chunks))
    print("compat BM25 vs T030 stored:", compat["matched"], "/", compat["checked"])
    print("encode:", encode_note or f"ok ({encode_seconds:.1f}s)")
    for k, s in sorted(aggregates.items()):
        print(f"{k}: R={s['evidence_recall']:.3f} H={s['hit']:.3f} M={s['mrr']:.3f}")
    print("boundary cases:", len(boundary_cases), "| regressions:", len(regressions),
          "| non-improvements:", len(non_improvements))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
