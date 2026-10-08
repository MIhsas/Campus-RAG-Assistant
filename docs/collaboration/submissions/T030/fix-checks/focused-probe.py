# T030-R1/R2 focused regression probe (MiMo). Read-only on real inputs;
# all altered freeze copies live in an isolated cache dir.
# T030-R2 updates: every scenario now carries an expected value and the script
# exits non-zero when any expectation fails; new section 5 = q10 half-fact
# assertions (a hit covering only 导师50% must NOT satisfy full f1).
# Usage: python focused-probe.py [--skip-matrix]
#   --skip-matrix  skips sections 2-3 (missing-section / hash-drift matrix);
#                  their results remain valid in focused-probe-output.txt (R2).
# No product edits, no network, no model calls.
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
BACKEND = ROOT / "step2_code/backend"
DATA = ROOT / "data/evaluations/sicau-rag-pilot-eval-v1"
CACHE = BACKEND / ".cache/t030-r2/focus-freeze"
CACHE.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(BACKEND / "src"))
sys.stdout.reconfigure(encoding="utf-8")

SKIP_MATRIX = "--skip-matrix" in sys.argv
FAILURES: list[str] = []
CHECKS = 0


def check(label: str, expected, actual) -> None:
    global CHECKS
    CHECKS += 1
    if isinstance(expected, float) or isinstance(actual, float):
        expected, actual = round(float(expected), 4), round(float(actual), 4)
    ok = expected == actual
    print(f"  [{label}] expected={expected} actual={actual} -> {'OK' if ok else 'FAIL'}")
    if not ok:
        FAILURES.append(label)


fz = json.loads((DATA / "freeze.json").read_text(encoding="utf-8"))
pack = Path(fz["corpus_pack"]["path"])
cli = [str(BACKEND / ".venv/Scripts/python.exe"), str(BACKEND / "scripts/check-real-eval.py"),
       "--pack", str(pack), "--questions", str(DATA / "questions.json"), "--freeze"]
env = dict(os.environ, PYTHONIOENCODING="utf-8")


def run_checker(freeze_path: Path, label: str) -> tuple[int, str]:
    proc = subprocess.run(cli + [str(freeze_path)], cwd=BACKEND, capture_output=True,
                          text=True, encoding="utf-8", env=env)
    tail = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()][-1:]
    print(f"[{label}] exit={proc.returncode} | " + " / ".join(tail))
    return proc.returncode, proc.stdout


print("== 1. real schema (positive, expected exit 0) ==")
code, _ = run_checker(DATA / "freeze.json", "real-freeze")
check("real-freeze-exit", 0, code)

if not SKIP_MATRIX:
    print("== 2. missing required sections (each expected exit 1) ==")
    for section in ("dataset", "corpus_pack", "implementation_sha256", "embedding_model", "annotation_files"):
        bad = copy.deepcopy(fz)
        bad.pop(section, None)
        p = CACHE / f"missing-{section}.json"
        p.write_text(json.dumps(bad, ensure_ascii=False, indent=2), encoding="utf-8")
        code, _ = run_checker(p, f"missing-{section}")
        check(f"missing-{section}-exit", 1, code)

    bad = copy.deepcopy(fz)
    bad["corpus_pack"]["files"] = {}
    p = CACHE / "empty-corpus-files.json"
    p.write_text(json.dumps(bad, ensure_ascii=False, indent=2), encoding="utf-8")
    code, _ = run_checker(p, "empty-corpus-files")
    check("empty-corpus-files-exit", 1, code)

    print("== 3. parametrized single-item hash drift (each expected exit 1) ==")
    drifts = []
    first_corpus = next(iter(fz["corpus_pack"]["files"]))
    drifts.append(("corpus-file", lambda b: b["corpus_pack"]["files"].__setitem__(first_corpus, "0" * 64)))
    first_impl = next(iter(fz["implementation_sha256"]))
    drifts.append(("impl-file", lambda b: b["implementation_sha256"].__setitem__(first_impl, "0" * 64)))
    first_model = next(iter(fz["embedding_model"]["identity_files_sha256"]))
    drifts.append(("model-identity", lambda b: b["embedding_model"]["identity_files_sha256"].__setitem__(first_model, "0" * 64)))
    first_ann = next(iter(fz["annotation_files"]))
    drifts.append(("annotation-file", lambda b: b["annotation_files"].__setitem__(first_ann, "0" * 64)))
    drifts.append(("questions", lambda b: b["dataset"].__setitem__("questions_sha256", "0" * 64)))
    drifts.append(("manifest", lambda b: b["corpus_pack"].__setitem__("manifest_sha256", "0" * 64)))
    for label, mutate in drifts:
        bad = copy.deepcopy(fz)
        mutate(bad)
        p = CACHE / f"drift-{label}.json"
        p.write_text(json.dumps(bad, ensure_ascii=False, indent=2), encoding="utf-8")
        code, _ = run_checker(p, f"drift-{label}")
        check(f"drift-{label}-exit", 1, code)
else:
    print("== 2-3. matrix skipped (--skip-matrix; prior results remain valid) ==")

print("== 4. q05 alternative-source scoring regression (same saved rankings) ==")
from campus_assistant.evaluation.metrics import evaluate_question  # noqa: E402

qs = {q["question_id"]: q for q in json.loads((DATA / "questions.json").read_text(encoding="utf-8"))["questions"]}
rev1_qs = {q["question_id"]: q for q in json.loads((DATA / "rev1/questions.json").read_text(encoding="utf-8"))["questions"]}
q05_v = qs["q05"]
q05_rev1 = rev1_qs["q05"]
print(f"q05 gold: rev1 {len(q05_rev1['evidence'])} 源 -> 当前 {len(q05_v['evidence'])} 源")


def hits_from(rec):
    return [{"chunk": h, "score": h.get("score", 0)} for h in rec["hit_summary"]]


for mode, exp_old, exp_new in (("bm25", 1.0, 1.0), ("dense", 0.2, 0.5), ("hybrid", 1 / 3, 1.0)):
    run = json.loads((DATA / "rev1/results" / f"{mode}.json").read_text(encoding="utf-8"))
    rec = next(r for r in run["per_question"] if r["question_id"] == "q05")
    v_old = evaluate_question(q05_rev1, hits_from(rec), top_k=5)
    v_new = evaluate_question(q05_v, hits_from(rec), top_k=5)
    print(f"q05 [{mode}] 同一排名 | rev1 gold mrr={v_old['mrr']} || 当前 gold mrr={v_new['mrr']}")
    check(f"q05-{mode}-mrr-rev1gold", exp_old, round(v_old["mrr"], 4))
    check(f"q05-{mode}-mrr-currgold", exp_new, round(v_new["mrr"], 4))

print("== 5. q10 half-fact assertions (导师50% alone must NOT cover full f1) ==")
q10 = qs["q10"]
f1_spans = {}
for ev in q10["evidence"]:
    if ev["fact_id"] == "f1" and ev["evidence_id"] in ("f1-s6", "f1-s7"):
        f1_spans[ev["evidence_id"]] = ev
for eid, ev in f1_spans.items():
    bid, doc = ev["block_id"], ev["document_id"]
    s_full, e_full = ev["char_start"], ev["char_end"]
    half_end = ev["quote"].index("和答辩成绩")  # boundary after 导师50%
    e_half = s_full + half_end

    def synth(s, e):
        return [{"score": 1.0, "chunk": {"document_id": doc, "block_id": bid,
                                          "chunk_id": "synthetic", "char_start": s, "char_end": e}}]

    v_half = evaluate_question(q10, synth(s_full, e_half), top_k=5)
    v_full = evaluate_question(q10, synth(s_full, e_full), top_k=5)
    print(f"q10 {eid}: half span ({s_full},{e_half}) full span ({s_full},{e_full})")
    check(f"q10-{eid}-half-recall", 0.0, v_half["recall"])          # 半事实不满足 f1，两事实均未覆盖
    check(f"q10-{eid}-half-f1-covered", False,
          next(f for f in v_half["facts"] if f["fact_id"] == "f1")["covered"])
    check(f"q10-{eid}-full-recall", 0.5, v_full["recall"])          # 完整 f1 覆盖=1/2 事实
    check(f"q10-{eid}-full-f1-covered", True,
          next(f for f in v_full["facts"] if f["fact_id"] == "f1")["covered"])

print(f"\n== SUMMARY: {CHECKS} checks, {len(FAILURES)} failures ==")
if FAILURES:
    for f in FAILURES:
        print("FAIL:", f)
    print("PROBE FAILED")
    raise SystemExit(1)
print("PROBE OK")
