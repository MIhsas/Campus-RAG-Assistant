"""Astra read-only source and filter audit. Run from the workspace root."""
import hashlib
import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "step2_code/backend/src"))
from campus_assistant.corpus.parse import parse_manifest
from campus_assistant.retrieval.filters import compute_allowed_document_ids

load = lambda p: json.loads((ROOT / p).read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
corpus = Path("data/corpora/sicau-rag-pilot-v1.1")
checks = load("docs/collaboration/submissions/T037/source-check.json")
manifest = load(corpus / "manifest.json")
questions = load("data/evaluations/sicau-rag-pilot-eval-v1/questions.json")
record = load("data/reviews/T036-user-review-20261008/human-review-record.json")
for key, rel in (
    ("questions", "data/evaluations/sicau-rag-pilot-eval-v1/questions.json"),
    ("manifest", str(corpus / "manifest.json")),
    ("procedures", "data/procedures/sicau-transfer-2026-v1/procedures.json"),
    ("user_record", "data/reviews/T036-user-review-20261008/human-review-record.json"),
):
    assert sha(rel) == checks["inputs"][key]["sha256"], key

historical_hashes = {
    "data/evaluations/sicau-rag-source-selection-v1/experiment.json": "57b22f93bd1420faf276915c6425b3f8e8f9c978058935f8a1c69de39bd5c618",
    "data/evaluations/sicau-rag-overlap-v1/experiment.json": "cef9f162f1eb164adbb65b1c9acc1634ee24e985edcc197fae09a6ac07dd2d95",
}
for rel, expected in historical_hashes.items():
    assert sha(rel) == expected, rel

parsed = parse_manifest(ROOT / corpus / "manifest.json", ROOT / corpus)
assert parsed["valid"] and not parsed["errors"] and len(parsed["documents"]) == 20
docs = {d["document_id"]: d for d in parsed["documents"]}
meta = {d["document_id"]: d for d in manifest["documents"]}
blocks = {
    (d["document_id"], b["block_id"]): b
    for d in parsed["documents"] for b in d["blocks"]
}
def verify(c):
    assert sha(corpus / meta[c["document_id"]]["local_path"]) == c["document_sha256"]
    b = blocks[c["document_id"], c["block_id"]]
    assert 0 <= c["char_start"] < c["char_end"] <= len(b["text"])
    assert b["text"][c["char_start"]:c["char_end"]] == c["quote"]
    if "locator" in c:
        assert c["locator"] == b.get("locator")

refs = [c for item in checks["items"] for field in ("citations", "repeal_check") for c in item.get(field, [])]
for c in refs:
    verify(c)
gold = {q["question_id"]: q for q in questions["questions"]}
for c in gold["q10"]["evidence"]:
    verify(c)

bed = next(k for k in docs if k.startswith("bed3ac"))
db = next(k for k in docs if k.startswith("db05e0"))
guide = next(k for k in docs if k.startswith("83eb"))
u03 = compute_allowed_document_ids(list(docs.values()), gold["u03"]["conditions"])
u04 = compute_allowed_document_ids(list(docs.values()), gold["u04"]["conditions"])
control = compute_allowed_document_ids(list(docs.values()), None)
assert u03["allowed_count"] == 4 and u03["excluded_counts"]["date_unknown_from"] == 16
assert bed not in u03["allowed_document_ids"] and db not in u03["allowed_document_ids"]
assert u04["allowed_count"] == 18 and u04["excluded_counts"]["scope_unknown"] == 2
assert guide not in u04["allowed_document_ids"]
assert control["allowed_document_ids"] is None and control["allowed_count"] == 20

print("SOURCE AUDIT OK:", len(refs), "submitted refs; 14 q10 gold refs; 4 input hashes; 20 fresh documents")
print("FILTER AUDIT OK: u03 4/20, u04 18/20, unrestricted 20/20")
print("BED3 DATE BLOCKS:")
for b in docs[bed]["blocks"]:
    if "2019年11月7日" in b["text"] or "自发文之日起执行" in b["text"]:
        print(json.dumps({"block_id": b["block_id"], "locator": b.get("locator"), "text": b["text"]}, ensure_ascii=False))
print("GUIDE SCOPE AND OFFICE BLOCKS:")
for b in docs[guide]["blocks"]:
    if "所有在校生" in b["text"] or "基本信息" in b["text"]:
        print(json.dumps({"block_id": b["block_id"], "locator": b.get("locator"), "text": b["text"]}, ensure_ascii=False))

out = {
    "fresh_parse_documents": 20, "source_refs_verified": len(refs),
    "q10_gold_refs_verified": 14, "input_hash_checks": 4,
    "historical_experiment_hash_checks": historical_hashes,
    "u03_allowed": 4, "u04_allowed": 18, "unrestricted": 20,
    "human_record_tally": record["tally"],
    "source_check_sha256": sha("docs/collaboration/submissions/T037/source-check.json"),
    "not_verified": ["policy current validity or revocation", "human withdrawal of open opinions", "browser behavior", "candidate implementation"],
}
(ROOT / "docs/collaboration/reviews/T037-audit.json").write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
