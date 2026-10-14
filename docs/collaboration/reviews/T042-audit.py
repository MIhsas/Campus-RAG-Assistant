"""Offline verification of the delivered review tool; no models or credentials."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "docs/collaboration/submissions/T042"
PACKDIR = ROOT / "step2_code/backend/.cache/human-review/T042-v1"
REBUILT = ROOT / "step2_code/backend/.cache/human-review/T042-Astra-20261014"
def load(p):
    return json.loads(p.read_text(encoding="utf-8"))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
def check(kind, label, ok):
    checks.append({"kind": kind, "label": label, "pass": bool(ok)})
c = load(SUB / "changed-files.json")
for section in ("new_scripts", "submissions", "delivery_touched"):
    for item in c[section]:
        if "sha256" in item:
            check("submission hash", item["path"], sha(ROOT / item["path"]) == item["sha256"])
for name, key in (("review.html", "review_html"), ("pack.json", "pack_json"), ("README.md", "readme")):
    check("pack hash", name, sha(PACKDIR / name) == c["pack_outputs"][key])
    check("independent rebuild", name, sha(PACKDIR / name) == sha(REBUILT / name))
p = load(PACKDIR / "pack.json")
q = {item["question_id"]: item for item in load(ROOT / "data/evaluations/sicau-rag-pilot-eval-v2/questions.json")["questions"]}
live = load(ROOT / "docs/collaboration/submissions/T040/live-answers-full.json")["questions"]
expected = [f"{domain}:{qid}" for domain in ("revision", "answer") for qid in ("q08", "q10", "u03", "u04")]
check("scope", "8 separated IDs", [card["card_id"] for card in p["cards"]] == expected)
check("scope", "unreviewed pack and counts", p["pack_meta"]["human_review_status"] == "unreviewed" and p["pack_meta"]["counts"] == {"cards": 8, "revision_cards": 4, "answer_cards": 4, "verified_refs": 40})
for name, item in p["pack_meta"]["inputs"].items():
    check("input identity", name, sha(Path(item["path"])) == item["sha256"])
reference_counts = {"gold": 0, "candidate": 0, "sent": 0}
for card in p["cards"]:
    qid = card["question_id"]
    check("snapshot", card["card_id"], card["query"] == q[qid]["query"] and card["conditions"] == q[qid]["conditions"])
    if card["object_type"] == "revision":
        source = q[qid]["evidence"]
        check("gold exact", card["card_id"], len(source) == len(card["gold_evidence"]) and all(all(src[k] == ev[k] for k in ("document_id", "document_sha256", "block_id", "char_start", "char_end", "quote", "evidence_id", "fact_id")) for src, ev in zip(source, card["gold_evidence"])))
        groups = (("gold", card["gold_evidence"]), ("candidate", card["candidates"]))
        check("candidate label", card["card_id"], all("非本次模型依据" in ev["candidate_label"] for ev in card["candidates"]))
    else:
        source = live[qid]
        check("original answers", card["card_id"], card["answer_paragraphs"] == source["answer_paragraphs_full"] and card["insufficient_reason"] == source["insufficient_reason"] and card["outcome"] == source["outcome"])
        check("sent exact", card["card_id"], len(card["sent_evidence"]) == len(source["evidence_full"]) and all(src['text'] == ev['quote'] and all(src[k] == ev[k] for k in ("document_id", "block_id", "char_start", "char_end", "evidence_id", "preview_url")) for src, ev in zip(source["evidence_full"], card["sent_evidence"])))
        groups = (("sent", card["sent_evidence"]),)
    for kind, refs in groups:
        for ev in refs:
            reference_counts[kind] += 1
            check("embedded span", card["card_id"] + "/" + kind, ev["block_text"][ev["char_start"]:ev["char_end"]] == ev["quote"] and ev["block_len"] == len(ev["block_text"]))
check("reference counts", "17 gold /3 candidate/20 sent", reference_counts == {"gold": 17, "candidate": 3, "sent": 20})
check("html contains correct data", "embedded PACK equals pack.json", load(PACKDIR / "pack.json") == json.loads(re.search(r'const PACK = (.*?);\s*\n\s*function esc', (PACKDIR / "review.html").read_text(encoding="utf-8"), re.S).group(1)))
old = load(ROOT / "docs/collaboration/submissions/T041/changed-files.json")
for section in ("delivery_modified", "delivery_unchanged"):
    for item in old[section]:
        if item["path"] != "docs/delivery/human-review-pending.md":
            check("delivery preserved", item["path"], sha(ROOT / item["path"]) == item["sha256"])
old_pending = (ROOT / "docs/delivery/archive-t041-rev1/human-review-pending.md").read_bytes()
check("append only", "human-review-pending original prefix preserved", (ROOT / "docs/delivery/human-review-pending.md").read_bytes().startswith(old_pending))
for name, expected_sha in {"data/evaluations/sicau-rag-pilot-eval-v2/freeze.json": "8c289b2ae7f00b39be80f02f850cf2820d8cc6de90f6f7245c634ddd2a9b5a26", "data/evaluations/sicau-rag-pilot-eval-v2/aggregate.json": "fcecdc9c884a55cdcf80870131326991f56a30a7b0cf9b9969ad54d4ae7af747"}.items():
    check("frozen", name, sha(ROOT / name) == expected_sha)
sample = load(SUB / "simulated-export-sample.json")
changed = [it for it in sample["items"] if it["opinion"] != "未复核"]
check("mock sample only", "one answer:q10 change labelled simulated", "模拟操作测试" in sample["record_title"] and len(sample["items"]) == 8 and len(changed) == 1 and changed[0]["id"] == "answer:q10" and changed[0]["opinion"] == "需修订" and sample["reviewer"] in ("", "（模拟测试，非真人复核）") and sample["review_date"] == "")
result = {"checks": checks, "count": len(checks), "reference_counts": reference_counts, "pass": all(it['pass'] for it in checks), "boundary": "Independent rebuild validated40 citations against fresh real parser; this audit compares the outputs and identities. Page behavior is VM stub, not browser. Browser file URL was rejected by policy; no workaround attempted. No human opinions certified."}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({"checks": len(checks), "pass": result['pass'], "failed": [it for it in checks if not it['pass']], "references": reference_counts}))
raise SystemExit(0 if result['pass'] else 1)
