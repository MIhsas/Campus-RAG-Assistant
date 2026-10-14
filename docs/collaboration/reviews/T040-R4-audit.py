"""Astra offline audit of saved live output; no HTTP, provider, or credentials."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "step2_code/backend"
SUB = ROOT / "docs/collaboration/submissions/T040"
sys.path.insert(0, str(BACKEND / "src"))
from campus_assistant.corpus.parse import parse_manifest
from campus_assistant.retrieval.filters import compute_allowed_document_ids
from campus_assistant.qa.deepseek import build_messages

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
def check(kind, label, ok):
    checks.append({"kind": kind, "label": label, "pass": bool(ok)})
def same(kind, p, expected):
    check(kind, str(p.relative_to(ROOT)), sha(p) == expected)

change = load(SUB / "changed-files.json")
for section in ("live_outputs", "updated_docs"):
    for item in change[section]:
        if "sha256" in item:
            same("submission hash", ROOT / item["path"], item["sha256"])
for item in change["live_outputs"]:
    same("raw live copy", BACKEND / ".cache/real-qa-smoke/T040-B-resume-1" / Path(item["path"]).name, item["sha256"])
baseline = load(SUB / "rev2/changed-files.json")
for name, expected in baseline["a_materials_unchanged"].items():
    if name != "note":
        for folder in (SUB, SUB / "rev1", BACKEND / ".cache/real-qa-smoke/T040-A"):
            same("A preserved", folder / name, expected)
rev3 = load(SUB / "rev3/changed-files.json")
for section in ("fixed_code", "updated_docs"):
    for item in rev3[section]:
        if "sha256" in item:
            target = ROOT / item["path"] if section == "fixed_code" else SUB / "rev3" / Path(item["path"]).name
            same("revision3 preserved", target, item["sha256"])
for name, expected in rev3["preserved_revision2"].items():
    if name.endswith((".json", ".md")):
        same("old live archived", SUB / "rev3" / name, expected)
same("run1 cache", BACKEND / ".cache/real-qa-smoke/T040-B/live-results.json", baseline["b_results"][0]["sha256"])
for name, expected in load(SUB / "input-hashes.json")["files"].items():
    if name == "prepare-real-qa-smoke.py":
        p = BACKEND / "scripts" / name
    elif name in ("questions.json", "freeze.json"):
        p = ROOT / "data/evaluations/sicau-rag-pilot-eval-v2" / name
    elif name == "manifest.json":
        p = ROOT / "data/corpora/sicau-rag-pilot-v1.2/manifest.json"
    elif name == "review-supplement.md":
        p = ROOT / "docs/collaboration/submissions/T039" / name
    else:
        p = BACKEND / "src/campus_assistant" / name
    same("A input", p, expected)
same("current aggregate", ROOT / "data/evaluations/sicau-rag-pilot-eval-v2/aggregate.json", "fcecdc9c884a55cdcf80870131326991f56a30a7b0cf9b9969ad54d4ae7af747")

run = load(SUB / "live-results.json")
full = load(SUB / "live-answers-full.json")
a = load(SUB / "dry-run.json")
questions = {q["question_id"]: q for q in load(ROOT / "data/evaluations/sicau-rag-pilot-eval-v2/questions.json")["questions"]}
order = ["q08", "q10", "u03", "u04"]
endpoint = "https://api.deepseek.com/chat/completions"
cfg = run["run_identity"]
check("config", "official actual configuration", cfg["endpoint"] == endpoint and cfg["model"] == "deepseek-flash" and cfg["max_tokens"] == 1500 and cfg["timeout_seconds"] == 30)
check("run", "four fixed questions complete", list(run["questions"]) == order and list(full["questions"]) == order and run["exit_ok"] is True and run["stop"]["reason"] == "completed_all" and run["stop"]["not_attempted"] == [])
counts = run["attempt_accounting"]
check("counts", "4 send /4 provider/8 local", counts["external_http_attempts"] == 4 and counts["provider_calls"] == 4 and counts["ask_calls"] == 8 and counts["ask_calls_generated_only"] == 4)
check("counts", "send log actual response", len(counts["send_log"]) == 4 and all(s["index"] == i and s["endpoint"] == endpoint and s["outcome"] == "response" and s["response_status"] == 200 for i, s in enumerate(counts["send_log"], 1)))
pack = ROOT / "data/corpora/sicau-rag-pilot-v1.2"
parsed = parse_manifest(pack / "manifest.json", pack)
check("corpus", "20 documents parsed without errors", len(parsed["documents"]) == 20 and not parsed["errors"])
docs = {d["document_id"]: d for d in parsed["documents"]}
blocks = {(d["document_id"], b["block_id"]): b for d in parsed["documents"] for b in d["blocks"]}
coverage = {}
metas = []
for qid in order:
    q = full["questions"][qid]
    r = run["questions"][qid]
    old = a["questions"][qid]
    check("snapshot", qid, q["query"] == questions[qid]["query"] == old["frozen_query"] and q["conditions"] == questions[qid]["conditions"] == old["frozen_conditions"] and r["request_body"] == {"query": q["query"], "filters": q["conditions"], "mode": "bm25", "top_k": 5, "answer_mode": "generated"})
    check("result", qid, q["outcome"] == r["outcome"] and q["answer_paragraphs_full"] == r["paragraphs"] and q["generation_meta"] == r["generation_meta"] and r["attempts"] == 1 and r["provider_calls"] == 1 and r["local_http_status"] == 200 and r["supplier_http_status"] == 200)
    ev = q["evidence_full"]
    sent = {e["evidence_id"]: e for e in ev}
    ae = {e["evidence_id"]: e for e in old["api_result"]["evidence"]}
    allowed = compute_allowed_document_ids(parsed["documents"], q["conditions"])["allowed_document_ids"]
    check("evidence", qid + " A equivalence", len(ev) == 5 and set(sent) == set(ae) and all(all(e[k] == ae[e["evidence_id"]][k] for k in e) for e in ev))
    for e in ev:
        block = blocks[(e["document_id"], e["block_id"])]
        check("span", qid + "/" + e["evidence_id"], 0 <= e["char_start"] < e["char_end"] <= len(block["text"]) and block["text"][e["char_start"]:e["char_end"]] == e["text"] and (allowed is None or e["document_id"] in allowed) and e["locator"] == block["locator"])
    rebuilt = build_messages(query=q["query"], evidence=old["api_result"]["evidence"], filters=q["conditions"])
    msgsha = hashlib.sha256(json.dumps(q["messages_full"], ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    check("messages", qid, q["messages_full"] == old["future_messages"] == rebuilt and msgsha == q["messages_sha256"])
    for p in q["answer_paragraphs_full"] or []:
        check("citation", qid, bool(p["evidence_ids"]) and len(p["citations"]) == len(p["evidence_ids"]) and all(c["evidence_id"] in p["evidence_ids"] and c["document_id"] == sent[c["evidence_id"]]["document_id"] and c["block_id"] == sent[c["evidence_id"]]["block_id"] and c["preview_url"] == sent[c["evidence_id"]]["preview_url"] for c in p["citations"]))
    m = q["generation_meta"]
    check("audit", qid, m == counts["attempt_log"][order.index(qid)]["generation_meta"] and m["model"] == "deepseek-flash" and m["finish_reason"] == "stop" and m["max_tokens"] == 1500 and m["request_id"] and m["usage"]["total_tokens"] == m["usage"]["prompt_tokens"] + m["usage"]["completion_tokens"] and m["latency_ms"] >= 0)
    metas.append(m)
    facts = {}
    for gold in questions[qid]["evidence"]:
        fid = gold.get("fact_id") or gold["evidence_id"]
        covered = any(e["document_id"] == gold["document_id"] and e["block_id"] == gold["block_id"] and e["char_start"] <= gold["char_start"] and gold["char_end"] <= e["char_end"] for e in ev)
        facts[fid] = facts.get(fid, False) or covered
    coverage[qid] = facts
    check("candidate isolation", qid, not any(e["document_id"].startswith("db05e0") for e in ev) if qid == "u03" else not any(e["document_id"].startswith("83eb") for e in ev) if qid == "u04" else True)
check("coverage", "q08 missing; q10 complete; u03 complete; u04 no gold", coverage == {"q08": {"f1": False}, "q10": {"f1": True, "f2": True}, "u03": {"f1": True}, "u04": {}})
check("audit", "4 distinct observed request IDs", len({m["request_id"] for m in metas}) == 4)
check("outcomes", "two answers and two model insufficiencies", [full["questions"][qid]["outcome"] for qid in order] == ["business_insufficient", "answered", "answered", "business_insufficient"])
check("limited secret scan", "no DeepSeek-shaped key in the two output JSON files", all(not re.search(r"sk-[a-fA-F0-9]{32}", (SUB / name).read_text(encoding="utf-8")) for name in ("live-results.json", "live-answers-full.json")))
result = {"checks": checks, "check_count": len(checks), "pass": all(c["pass"] for c in checks), "gold_fact_coverage": coverage,
          "observed_token_usage": {key: sum(m["usage"][key] for m in metas) for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
          "boundary": "Saved live audit and offline structural verification; no independent server-side accounting, no network replay, no automatic semantic certification or human signature."}
Path(__file__).with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"checks": len(checks), "pass": result["pass"], "failed": [c for c in checks if not c["pass"]], "coverage": coverage, "usage": result["observed_token_usage"]}))
raise SystemExit(0 if result["pass"] else 1)
