"""Independent document-only audit. No credentials, network or product imports."""
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / "docs/collaboration/submissions/T041"
DEL = ROOT / "docs/delivery"
def load(p):
    return json.loads(p.read_text(encoding="utf-8"))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
checks = []
def check(kind, label, ok):
    checks.append({"kind": kind, "label": label, "pass": bool(ok)})
change = load(SUB / "changed-files.json")
for section in ("delivery_updated", "delivery_new", "submissions"):
    for item in change[section]:
        if "sha256" in item:
            check("submitted hash", item["path"], sha(ROOT / item["path"]) == item["sha256"])
docs = {Path(item["path"]).name: (ROOT / item["path"]).read_text(encoding="utf-8") for section in ("delivery_updated", "delivery_new") for item in change[section]}
links = []
for name, text in docs.items():
    for target in re.findall(r'\]\(([^\n)]+)\)', text):
        if re.match(r'^[a-zA-Z]+:', target) or target.startswith('#'):
            continue
        dest = unquote(target.split('#')[0].strip('<>'))
        ok = (DEL / dest).exists()
        links.append({"file": name, "target": target, "pass": ok})
check("links", "all relative Markdown links exist", all(link["pass"] for link in links))
raw = load(ROOT / "docs/collaboration/submissions/T040/live-answers-full.json")
case = docs["generation-casebook.md"]
for qid, q in raw["questions"].items():
    check("case text", qid + " query", q["query"] in case)
    for i, paragraph in enumerate(q["answer_paragraphs_full"] or []):
        check("case text", qid + " paragraph " + str(i + 1), paragraph["text"] in case)
    if q.get("insufficient_reason"):
        check("case text", qid + " insufficiency", q["insufficient_reason"] in case)
agg = load(ROOT / "data/evaluations/sicau-rag-pilot-eval-v2/aggregate.json")
verify = load(SUB / "t041-verify.json")
for mode, vals in agg["aggregates_n21"].items():
    numbers = [vals[k] for k in ("evidence_recall", "hit", "mrr")]
    check("metrics", mode + " recorded verify", verify["n21"][mode] == numbers)
    for name in ("experiment-index.md", "thesis-outline.md", "evidence-matrix.md"):
        check("metrics", mode + " " + name, all(str(number) in docs[name] for number in numbers))
for mode, vals in agg["aggregates_common_n20"].items() if "aggregates_common_n20" in agg else agg["common_subset_n20"].items():
    check("metrics", mode + " common subset", verify["n20"][mode] == [vals[k] for k in ("evidence_recall", "hit", "mrr")])
metas = [q["generation_meta"]["usage"] for q in raw["questions"].values()]
tokens = {"prompt": sum(m["prompt_tokens"] for m in metas), "completion": sum(m["completion_tokens"] for m in metas), "total": sum(m["total_tokens"] for m in metas)}
check("usage", "sum and copied token values", tokens == verify["tokens"] == {"prompt": 6080, "completion": 388, "total": 6468})
times = [int(v) for v in re.findall(r'^\| [0-7] \|[^\n]*\| (\d+) \|$', docs["defense-script.md"], re.M)]
check("time", "8 segments total560", len(times) == 8 and sum(times) == 560 and 480 <= sum(times) <= 600)
prefixes = {"README.md": "a31a9033", "system-design.md": "dab469a6", "thesis-outline.md": "07f92376", "evidence-matrix.md": "4c84fa3d", "defense-script.md": "e96bce13", "windows-runbook.md": "d55a0db0", "experiment-index.md": "9762be38", "human-review-pending.md": "852a9517"}
archive = []
for name, prefix in prefixes.items():
    p = DEL / "archive-pre-t041-20261011" / name
    digest = sha(p)
    archive.append({"file": name, "sha256": digest, "expected_prior_prefix": prefix, "prefix_match": digest.startswith(prefix)})
check("archive", "8 prior reported digest prefixes", len(archive) == 8 and all(a["prefix_match"] for a in archive))
prior = load(ROOT / "docs/collaboration/reviews/T040-R4-audit.json")
protected = [c for c in prior["checks"] if c["kind"] in ("submission hash", "raw live copy", "A input", "run1 cache", "current aggregate")]
# T040 prior audit labels contain repository-relative paths, each expected hash is
# anchored by prior submission or input records; current T040 list remains fixed.
t040 = load(ROOT / "docs/collaboration/submissions/T040/changed-files.json")
for section in ("live_outputs", "updated_docs"):
    for item in t040[section]:
        if "sha256" in item:
            check("T040 preserved", item["path"], sha(ROOT / item["path"]) == item["sha256"])
for name, expected in {"data/evaluations/sicau-rag-pilot-eval-v2/questions.json": "4e39229eb3b31dc9ccd5dc157e2d63203514ce70069450adca6b78c24b65c103", "data/evaluations/sicau-rag-pilot-eval-v2/freeze.json": "8c289b2ae7f00b39be80f02f850cf2820d8cc6de90f6f7245c634ddd2a9b5a26", "data/evaluations/sicau-rag-pilot-eval-v2/aggregate.json": "fcecdc9c884a55cdcf80870131326991f56a30a7b0cf9b9969ad54d4ae7af747", "data/corpora/sicau-rag-pilot-v1.2/manifest.json": "b05c37557675f02c045e01e9fd776c539954c43172d5e0b07d0704da4e352b4a"}.items():
    check("frozen", name, sha(ROOT / name) == expected)
findings = []
if "gold 为**模型辅助标注、人工未复核**" in docs["experiment-index.md"].split('## E4')[0]:
    findings.append({"id": "human-state", "file": "experiment-index.md", "detail": "Current shared limitation wrongly blanket-labels human review absent; received109/3/2 and remaining current items must be distinguished."})
if "T038—T041 均无浏览器实操" in docs["evidence-matrix.md"]:
    browser_review = (ROOT / "docs/collaboration/reviews/T038-R1.md").read_text(encoding="utf-8")
    check("source for prose finding", "T038 actually records browser path", "真实浏览器主路径已补齐" in browser_review)
    findings.append({"id": "browser-history", "file": "evidence-matrix.md", "detail": "Claims T038 had no browser work although T038-R1 documents real browser paths; distinguish T041/no new generated-answer browser evidence."})
result = {"structural_checks": checks, "structural_pass": all(c["pass"] for c in checks), "links": links, "archive": archive, "archive_boundary": "Prior eight digest prefixes checked and current full digests recorded; no independent complete pre-change snapshot for all eight.", "prose_findings": findings, "pass": all(c["pass"] for c in checks) and not findings}
Path(__file__).with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({"structural_checks": len(checks), "structural_pass": result["structural_pass"], "link_count": len(links), "failed_checks": [c for c in checks if not c['pass']], "findings": findings}))
raise SystemExit(0 if result['pass'] else 1)
