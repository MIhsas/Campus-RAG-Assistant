"""Read-only submitted hashes and preserved A identities; no credential access."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "step2_code/backend"
SUB = ROOT / "docs/collaboration/submissions/T040"
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

changed = json.loads((SUB / "changed-files.json").read_text(encoding="utf-8"))
checks = []
for section in ("new_code", "b_results", "updated_docs"):
    for item in changed[section]:
        if "sha256" in item:
            checks.append({"kind": "submission", "path": item["path"], "pass": sha(ROOT / item["path"]) == item["sha256"]})
for name, expected in changed["a_materials_unchanged"].items():
    if name == "note":
        continue
    for folder in (SUB, SUB / "rev1", BACKEND / ".cache/real-qa-smoke/T040-A"):
        checks.append({"kind": "A material", "path": str((folder / name).relative_to(ROOT)), "pass": sha(folder / name) == expected})
inputs = json.loads((SUB / "input-hashes.json").read_text(encoding="utf-8"))["files"]
for name, expected in inputs.items():
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
    checks.append({"kind": "A input", "path": str(p.relative_to(ROOT)), "pass": sha(p) == expected})
raw = json.loads((SUB / "live-results.json").read_text(encoding="utf-8"))
checks.append({"kind": "run-1 copy", "pass": sha(SUB / "live-results.json") == sha(BACKEND / ".cache/real-qa-smoke/T040-B/live-results.json")})
result = {"checks": checks, "count": len(checks), "pass": all(c["pass"] for c in checks),
          "raw_run_1": {"key_present": raw["preflight"]["key_present"], "external_http_attempts": raw["attempt_accounting"]["external_http_attempts"], "ask_calls": raw["attempt_accounting"]["ask_calls"], "question_keys": list(raw["questions"])},
          "boundary": "Hashes and stored preflight only; no live request, no current key-presence check"}
Path(__file__).with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"count": result["count"], "pass": result["pass"], "raw_run_1": result["raw_run_1"]}))
raise SystemExit(0 if result["pass"] else 1)
