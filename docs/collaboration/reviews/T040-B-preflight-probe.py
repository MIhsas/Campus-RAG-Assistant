"""Astra: two isolated mock probes; no real network or credentials.

A identity is explicitly stubbed only for the output-directory probe.
This is not evidence of live generation or independent A-content validation.
"""
import importlib.util
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "step2_code/backend"
sys.path.insert(0, str(BACKEND / "src"))
spec = importlib.util.spec_from_file_location("t040_mock_helpers", BACKEND / "tests/test_live_smoke_real_qa.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
smoke = helpers.smoke
from campus_assistant.qa.deepseek import DeepSeekAnswerProvider

def main():
    evidence = {"level": "isolated mock; zero real network", "checks": {}}
    _, _, _, corpus = helpers._make_app([])
    with TemporaryDirectory(prefix="t040-output-", dir=Path(__file__).parent) as tmp:
        tmp = Path(tmp)
        qpath = tmp / "questions.json"
        qpath.write_text(json.dumps({"questions": list(helpers.QUESTIONS.values())}), encoding="utf-8")
        output = tmp / "existing"
        output.mkdir()
        sentinel = output / "previous.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        fake = helpers._FakeClient([helpers._deepseek_ok() for _ in range(4)])
        inner = DeepSeekAnswerProvider("mock-placeholder", client=fake)
        error = None
        with patch.object(smoke, "verify_a_identity", return_value={"ok": True, "problems": []}):
            try:
                smoke.run_b(live=True, a_dir=tmp / "a", out_dir=output,
                            questions_path=qpath, corpus_root=corpus,
                            provider_factory=lambda: inner, emit=lambda *_: None)
            except RuntimeError as exc:
                error = str(exc)
        evidence["checks"]["nonempty_output_before_send"] = {
            "identity_note": "A gate stubbed true to isolate output-check timing",
            "mock_post_calls": len(fake.calls), "error": error,
            "old_file_unchanged": sentinel.read_text(encoding="utf-8") == "preserve",
            "new_audit_written": (output / "live-results.json").exists(),
            "pass": len(fake.calls) == 0 and error is not None,
        }

    client, recording, fake, _ = helpers._make_app([])
    with patch("campus_assistant.qa.deepseek.build_messages", side_effect=RuntimeError("mock pre-send failure")):
        result = smoke.execute_live_loop(client=client, recording=recording, questions=helpers.QUESTIONS)
    evidence["checks"]["counter_matches_actual_send"] = {
        "mock_post_calls": len(fake.calls),
        "reported_external_http_attempts": recording.external_http_attempts,
        "first_outcome": result["questions"]["q08"]["outcome"],
        "pass": recording.external_http_attempts == len(fake.calls),
    }
    evidence["pass"] = all(c["pass"] for c in evidence["checks"].values())
    target = Path(__file__).with_suffix(".json")
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0 if evidence["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
