"""Astra T029: isolated input/output verification regression, no real-data writes.

Run with the backend Python. Exit 0 only if an unchanged pack verifies and
changes to source bytes or selection evidence are detected without overwriting.
Temporary fixtures stay under backend/.cache/astra-t029-* for inspection.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "step2_code/backend"
sys.stdout.reconfigure(encoding="utf-8")
spec = importlib.util.spec_from_file_location(
    "prepare_real_corpus", BACKEND / "scripts/prepare-real-corpus.py"
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    cache = BACKEND / ".cache"
    cache.mkdir(exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix="astra-t029-", dir=cache))
    dataset = fixture / "dataset"
    dataset.mkdir()
    original = b"Original public policy text.\n"
    src = dataset / "document.txt"
    src.write_bytes(original)
    doc_id = digest(src)
    row = {
        "doc_id": doc_id, "sha256": doc_id, "relative_path": "document.txt",
        "title": "Isolated review fixture",
        "sources": [{"url": "https://jiaowu.sicau.edu.cn/example.txt",
                     "site": "jiaowu.sicau.edu.cn"}],
    }
    (dataset / "manifest.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    selection = {"docs": [{"doc_id": doc_id, "decision": "include",
                           "reason": "Reviewed original", "notes": "Evidence revision 1"}]}
    selection_path = fixture / "selection.json"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    out = fixture / "pack"
    records = []

    def run_case(name: str, should_succeed: bool) -> None:
        before = {p.name: digest(p) for p in out.glob("*") if p.is_file()}
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            try:
                code = module.build(dataset, selection_path, out)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                print(str(exc))
        after = {p.name: digest(p) for p in out.glob("*") if p.is_file()}
        unchanged = not before or before == after
        passed = ((code == 0) == should_succeed) and unchanged
        records.append({"case": name, "expected_success": should_succeed,
                        "actual_exit_code": code, "output_unchanged": unchanged,
                        "passed": passed, "stdout": stdout.getvalue().strip()})

    run_case("initial_build", True)
    run_case("unchanged_verify", True)
    src.write_bytes(b"Changed public policy text.\n")
    run_case("source_bytes_changed_manifest_unchanged", False)
    src.write_bytes(original)
    selection["docs"][0]["notes"] = "Evidence revision 2"
    selection_path.write_text(json.dumps(selection), encoding="utf-8")
    run_case("selection_evidence_changed", False)
    result = {"fixture": str(fixture), "external_model_calls": 0, "cases": records}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(r["passed"] for r in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
