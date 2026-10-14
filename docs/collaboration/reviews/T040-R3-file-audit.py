"""Astra revision-3 file audit, no network or credential access."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "step2_code/backend"
SUB = ROOT / "docs/collaboration/submissions/T040"
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    return json.loads(p.read_text(encoding="utf-8"))
checks = []
def check(kind, p, expected):
    checks.append({"kind": kind, "path": str(p.relative_to(ROOT)), "expected_sha256": expected, "pass": digest(p) == expected})

current = read(SUB / "changed-files.json")
previous = read(SUB / "rev2/changed-files.json")
for section in ("fixed_code", "updated_docs"):
    for item in current[section]:
        if "sha256" in item:
            check("current submission", ROOT / item["path"], item["sha256"])
for name, expected in previous["a_materials_unchanged"].items():
    if name != "note":
        for folder in (SUB, SUB / "rev1", BACKEND / ".cache/real-qa-smoke/T040-A"):
            check("A original", folder / name, expected)
for section in ("b_results", "updated_docs"):
    for item in previous[section]:
        if "sha256" in item:
            check("revision-2 archive", SUB / "rev2" / Path(item["path"]).name, item["sha256"])
for name, expected in current["preserved_revision2"].items():
    if name.endswith(".json") or name.endswith(".md"):
        check("run-1 preserved", SUB / name, expected)
check("run-1 raw cache", BACKEND / ".cache/real-qa-smoke/T040-B/live-results.json", previous["b_results"][0]["sha256"])
old_probe = SUB / "rev2/T040-B-preflight-probe-failed-preserved.json"
old_data = read(old_probe)
checks.append({"kind": "failed probe retained", "path": str(old_probe.relative_to(ROOT)),
               "actual_sha256": digest(old_probe), "expected_sha256_prefix": "94e3944f",
               "boundary": "Known prior digest prefix and failed probe content, not a full independent prior digest",
               "pass": digest(old_probe).startswith("94e3944f") and old_data["pass"] is False
               and old_data["checks"]["nonempty_output_before_send"]["mock_post_calls"] == 4
               and old_data["checks"]["counter_matches_actual_send"]["reported_external_http_attempts"] == 1})
for name, expected in read(SUB / "input-hashes.json")["files"].items():
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
    check("A input", p, expected)
result = {"checks": checks, "count": len(checks), "pass": all(c["pass"] for c in checks), "boundary": "File hashes only; no live request or current secret-presence check. Probe output hash excluded because temp-directory text changes on rerun."}
Path(__file__).with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"count": len(checks), "pass": result["pass"], "failed": [c for c in checks if not c["pass"]]}, ensure_ascii=False))
raise SystemExit(0 if result["pass"] else 1)
